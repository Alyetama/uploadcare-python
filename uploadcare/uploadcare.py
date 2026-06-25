#!/usr/bin/env python
# coding: utf-8

import hashlib
import hmac
import io
import json
import mimetypes
import time
from pathlib import Path
from typing import Optional, Union

import dateparser
import requests
from requests.structures import CaseInsensitiveDict

from .exceptions import (InvalidDatetimeString, MissingExpireKwarg,
                        MissingSecretKey)


def _strip_image_metadata(path: str) -> Optional[bytes]:
    """Return the bytes of an image with embedded metadata removed.

    Re-encodes the image without its metadata (EXIF/GPS, PNG text chunks,
    ICC profile, etc.). JPEGs are saved with ``quality='keep'`` so the pixel
    data is preserved without re-quantization.

    Args:
        path (str): Path to the image file.

    Returns:
        Optional[bytes]: The stripped image bytes, or ``None`` if the file is
        not a readable image (in which case the caller should upload it as-is).

    Raises:
        ImportError: If Pillow is not installed.
    """
    try:
        from PIL import Image
    except ImportError:
        raise ImportError(
            'strip_metadata=True requires Pillow. Install it with '
            '`pip install Pillow`.')

    try:
        img = Image.open(path)
        img.load()
    except Exception:
        return None  # Not an image we can read; nothing to strip.

    save_kwargs = {}
    if img.format == 'JPEG':
        save_kwargs['quality'] = 'keep'

    buffer = io.BytesIO()
    # Not passing exif=/pnginfo=/icc_profile= means none of it is written back.
    img.save(buffer, format=img.format, **save_kwargs)
    return buffer.getvalue()


class UploadCare:
    """Python wrapper for UploadCare's Upload API

    Attributes:
        pub_key (str): Your public key.
        secret_key (Optional[str]): Your secret key.
        api_url (Optional[str]): API URL.
    """

    def __init__(self,
                 pub_key: str,
                 secret_key: Optional[str] = None,
                 api_url: Optional[str] = 'https://upload.uploadcare.com'):
        """Initializes the client.

        Args:
            pub_key (str): Your public key.
            secret_key (Optional[str]): Your secret key.
            api_url (Optional[str]): API URL. Defaults to
                'https://upload.uploadcare.com'.
        """
        self.pub_key = pub_key
        self.secret_key = secret_key
        self.api_url = api_url

    @staticmethod
    def generate_secure_signature(secret_key, expire):
        """Generates a signature to be sent alongside a secure upload request

        Note:
            Source: 
            https://uploadcare.com/docs/security/secure-uploads/#make-signature

        Args:
            secret_key (str): The secret key for your Uploadcare project.
                expire (int): A UNIX timestamp indicating the time when the
                signature will expire.

        Returns:
            str: A signature string.

        Raises:
            ValueError: If the secret key is not a string.
            TypeError: If the expire argument is not an integer.
        """
        k, m = secret_key, str(expire).encode('utf-8')
        if not isinstance(k, (bytes, bytearray)):
            k = k.encode('utf-8')
        return hmac.new(k, m, hashlib.sha256).hexdigest()

    def _secure_expire_signature(
            self, expire: Optional[Union[float, int, str]]) -> dict:
        if not isinstance(expire, (float, int, str)):
            raise ValueError(
                '`expire` value must be a float or a string representing date '
                'and/or time in a recognizably valid format.')

        if not self.secret_key:
            raise MissingSecretKey

        if isinstance(expire, str):
            expire = dateparser.parse(expire)
            if not expire:
                raise InvalidDatetimeString(expire)
            expire = time.mktime(expire.timetuple())
        if expire - time.time() < 0:
            raise ValueError('Expire timestamp cannot be in the past!')

        expire = int(expire)
        signature = self.generate_secure_signature(self.secret_key, expire)
        return {'expire': expire, 'signature': signature}

    def _check_response(self, resp):
        if resp.status_code != 200:
            if '`signature` is required' in resp.text and not self.secret_key:
                raise MissingSecretKey
            raise ConnectionError(resp.text)
        else:
            return resp.json()

    def _input_identity(self, _input) -> tuple:
        is_url = True
        endpoint = f'{self.api_url}/from_url/'
        try:
            input_exists = Path(_input).exists()
        except OSError:
            input_exists = False
        if input_exists:
            is_url = False
            endpoint = f'{self.api_url}/base/'
        elif not _input.startswith('http'):
            raise ValueError(
                'Input is neither an existing file nor a valid URL!')
        return is_url, endpoint

    def check_status(self,
                     token,
                     interval: float = 0.5,
                     timeout: Optional[float] = 60) -> tuple:
        """Check the status of a file upload, polling until it completes.

        Args:
            token (str): The token returned by the upload endpoint.
            interval (float): Seconds to wait between status checks.
            timeout (Optional[float]): Maximum seconds to wait before giving
                up. Pass ``None`` to poll indefinitely.

        Returns:
            tuple: A tuple containing the filename and uuid of the uploaded
            file.

        Raises:
            ConnectionError: If the status is 'error' or 'unknown'.
            TimeoutError: If the upload does not complete within ``timeout``.
        """
        status_endpoint = f'{self.api_url}/from_url/status/'
        deadline = None if timeout is None else time.time() + timeout

        while True:
            status_res = requests.post(status_endpoint, data={'token': token})
            wait_res = status_res.json()
            status = wait_res.get('status')
            if status == 'success':
                return wait_res['filename'], wait_res['uuid']
            if status in ('error', 'unknown'):
                raise ConnectionError(status_res.text)
            if deadline is not None and time.time() >= deadline:
                raise TimeoutError(
                    f'Upload did not complete within {timeout} seconds.')
            time.sleep(interval)

    def upload(self,
               _input: str,
               store: Union[int, str] = 'auto',
               metadata: Optional[dict] = None,
               expire: Optional[Union[float, int, str]] = None,
               strip_metadata: bool = False,
               **kwargs) -> str:
        """Uploads a file to Uploadcare.

        Args:
            _input (str): A path to a file or a URL.
            store (Union[int, str], optional): Whether to store the file.
                Defaults to 'auto'.
            metadata (Optional[dict], optional): Metadata to be attached to
                the file. Defaults to None.
            expire (Optional[Union[float, int, str]], optional): Expiration time
                for the upload. Defaults to None.
            strip_metadata (bool, optional): If True, strip embedded metadata
                (e.g. EXIF/GPS) from local image files before uploading so the
                stored original carries no metadata. Requires Pillow. Has no
                effect on non-image or URL uploads. Defaults to False.
            **kwargs: Additional arguments to be passed to the API.

        Returns:
            str: The URL of the uploaded file.

        Raises:
            MissingExpireKwarg: If the secret key is set but the expire kwarg
                is not.
            ImportError: If strip_metadata is True but Pillow is not installed.
        """
        if self.secret_key and not expire:
            raise MissingExpireKwarg

        fname = Path(_input).name

        is_url, endpoint = self._input_identity(_input)

        if not is_url:
            with open(_input, 'rb') as f:
                fdata = f.read()
            if strip_metadata:
                stripped = _strip_image_metadata(_input)
                if stripped is not None:
                    fdata = stripped

        pub_k = 'pub_key' if is_url else 'UPLOADCARE_PUB_KEY'

        data = {pub_k: self.pub_key, 'UPLOADCARE_STORE': str(store), **kwargs}

        if is_url:
            data.update({'source_url': _input})

        if metadata:
            for k, v in metadata.items():
                data.update({f'metadata[{k}]': v})

        if expire:
            data.update(self._secure_expire_signature(expire))

        content_type = mimetypes.guess_type(fname)[0]

        if is_url:
            res = requests.post(endpoint, data=data)
        else:
            res = requests.post(endpoint,
                                data=data,
                                files={'file': (fname, fdata, content_type)})

        res_json = self._check_response(res)

        if not is_url:
            _uuid = res_json['file']
        elif res_json.get('token'):
            token = res_json['token']
            fname, _uuid = self.check_status(token)
        else:
            fname, _uuid = res_json['filename'], res_json['uuid']

        return f'https://ucarecdn.com/{_uuid}/{fname}'

    def info(self, _input: str, pretty: bool = False):
        """Get information about a file.

        Args:
            _input (str): The file id or url of the file.
            pretty (bool): If True, returns a pretty printed json.

        Returns:
            dict: A dictionary containing information about the file.
        """
        endpoint = f'{self.api_url}/info/'

        if _input.startswith('http'):
            _uuid = Path(_input).parts[-2]
        else:
            _uuid = _input
        params = {'file_id': _uuid, 'pub_key': self.pub_key}

        res = requests.get(endpoint, params=params)
        res_json = self._check_response(res)

        if pretty:
            return json.dumps(res_json, indent=4)
        return res_json

    def start_multipart(self,
                        filename: str,
                        size: int,
                        expire: Optional[Union[float, int, str]] = None,
                        **kwargs):
        """Starts a multipart upload.

        Args:
            filename (str): The name of the file to be uploaded.
            size (int): The size of the file in bytes.
            expire (Optional[Union[float, int, str]]): The time when the upload
                will expire. If not provided, the upload will never expire.
                Can be a number of seconds since the epoch, a datetime object,
                or a string in a valid date/time format.
            **kwargs: Additional parameters to be passed to the server.

        Returns:
            dict: A dictionary containing the upload URL and the upload ID.

        Raises:
            MissingExpireKwarg: If the secret key is set and the expire argument
                is not provided.
            UploadcareException: If the response from the server is not
                successful.
        """
        if self.secret_key and not expire:
            raise MissingExpireKwarg

        endpoint = f'{self.api_url}/multipart/start/'
        data = {
            'UPLOADCARE_PUB_KEY': self.pub_key,
            'filename': filename,
            'size': size,
            **kwargs
        }

        if expire:
            data.update(self._secure_expire_signature(expire))

        res = requests.post(endpoint, data=data)
        return self._check_response(res)

    @staticmethod
    def upload_parts(presigned_url: str, data: bytes, content_type: str):
        """Uploads a single part's bytes to a presigned url.

        Args:
            presigned_url (str): The full presigned url returned by
                ``start_multipart`` to upload this part to.
            data (bytes): The raw bytes of the chunk to upload.
            content_type (str): The content type of the file.

        Returns:
            requests.Response: The response from the server.

        Raises:
            requests.HTTPError: If the upload request fails.
        """
        headers = CaseInsensitiveDict()
        headers['Content-Type'] = content_type
        res = requests.put(presigned_url, data=data, headers=headers)
        res.raise_for_status()
        return res

    def complete_multipart(self, uuid):
        """Complete multipart upload.
    
        Args:
            uuid (str): UUID of the file to complete.
            
        Returns:
            dict: A dictionary containing the response from the server.
        """
        endpoint = f'{self.api_url}/multipart/complete/'
        data = {'UPLOADCARE_PUB_KEY': self.pub_key, 'uuid': uuid}
        res = requests.post(endpoint, data=data)
        return self._check_response(res)

    def create_group(self,
                     files: list,
                     expire: Optional[Union[float, int, str]] = None,
                     **kwargs):
        """Creates a group of files.

        Args:
            files (list): A list of file objects.
            expire (Optional[Union[float, int, str]]): The time in seconds until
                the group expires.
            **kwargs: Additional keyword arguments to pass to the API.

        Returns:
            dict: The response from the API.

        Raises:
            MissingExpireKwarg: If the secret key is set and the expire kwarg is
                not.
        """

        if self.secret_key and not expire:
            raise MissingExpireKwarg

        endpoint = f'{self.api_url}/group/'
        data = {'pub_key': self.pub_key, **kwargs}
        for n, file in enumerate(files):
            data.update({f'files[{n}]': file})

        if expire:
            data.update(self._secure_expire_signature(expire))

        res = requests.post(endpoint, data=data)
        return self._check_response(res)

    def group_info(self, group_id: str):
        """Returns information about a files group.

        Args:
            group_id (str): The id of the group to get info for.
        Returns:
            dict: A dictionary containing the group's info.
        """
        endpoint = f'{self.api_url}/group/info/'
        params = {'pub_key': self.pub_key, 'group_id': group_id}
        res = requests.get(endpoint, params=params)
        return self._check_response(res)
