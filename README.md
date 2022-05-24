# Uploadcare-Python

🚀 Python wrapper for UploadCare's Upload API.

[![GitHub Pages](https://github.com/Alyetama/uploadcare-python/actions/workflows/gh-pages.yml/badge.svg)](https://github.com/Alyetama/uploadcare-python/actions/workflows/gh-pages.yml) [![Supported Python versions](https://img.shields.io/badge/Python-%3E=3.6-blue.svg)](https://www.python.org/downloads/) [![PEP8](https://img.shields.io/badge/Code%20style-PEP%208-orange.svg)](https://www.python.org/dev/peps/pep-0008/) 


- 📖 [Documentation](https://alyetama.github.io/uploadcare-python/)

## Requirements
- 🐍 [python>=3.6](https://www.python.org/downloads/)


## ⬇️ Installation

```sh
pip install uploadcare
```

## ⌨️ Usage

```python
from uploadcare import UploadCare

uc = UploadCare(pub_key='my-public-key')
```

## 📕 Examples

```python
file = 'https://upload.wikimedia.org/wikipedia/en/a/a9/Example.jpg'  # or a local file

url = uc.upload(file)
print(url)
# 'https://ucarecdn.com/d30aff21-a441-4ae4-82e0-ead56bfabdc9/Example.jpg'

uc.info(url)
# {'size': 27661, 'total': 27661, 'done': 27661, 'uuid': 'd30aff21-a441-4ae4-82e0-ead56bfabdc9', 'file_id': 'd30aff21-a441-4ae4-82e0-ead56bfabdc9', 'original_filename': 'Example.jpg', 'is_image': True, 'is_stored': False, 'image_info': {'dpi': [72, 72], 'width': 275, 'format': 'JPEG', 'height': 297, 'sequence': False, 'color_mode': 'RGB', 'orientation': None, 'geo_location': None, 'datetime_original': None}, 'video_info': None, 'content_info': {'mime': {'mime': 'image/jpeg', 'type': 'image', 'subtype': 'jpeg'}, 'image': {'dpi': [72, 72], 'width': 275, 'format': 'JPEG', 'height': 297, 'sequence': False, 'color_mode': 'RGB', 'orientation': None, 'geo_location': None, 'datetime_original': None}}, 'is_ready': True, 'filename': 'Example.jpg', 'mime_type': 'image/jpeg', 'metadata': {}}

print(uc.info(url, pretty=True))
# Expand the output below:
```

<details>
  <summary>Expand</summary>
  
  ```json
  {
    "size": 27661,
    "total": 27661,
    "done": 27661,
    "uuid": "d30aff21-a441-4ae4-82e0-ead56bfabdc9",
    "file_id": "d30aff21-a441-4ae4-82e0-ead56bfabdc9",
    "original_filename": "Example.jpg",
    "is_image": true,
    "is_stored": false,
    "image_info": {
        "dpi": [
            72,
            72
        ],
        "width": 275,
        "format": "JPEG",
        "height": 297,
        "sequence": false,
        "color_mode": "RGB",
        "orientation": null,
        "geo_location": null,
        "datetime_original": null
    },
    "video_info": null,
    "content_info": {
        "mime": {
            "mime": "image/jpeg",
            "type": "image",
            "subtype": "jpeg"
        },
        "image": {
            "dpi": [
                72,
                72
            ],
            "width": 275,
            "format": "JPEG",
            "height": 297,
            "sequence": false,
            "color_mode": "RGB",
            "orientation": null,
            "geo_location": null,
            "datetime_original": null
        }
    },
    "is_ready": true,
    "filename": "Example.jpg",
    "mime_type": "image/jpeg",
    "metadata": {}
}
  ```

</details>


### 🔑 Supports *Secure Upload*

- A secure signature is generated automatically. But if you want to use a custom signature, you can pass it as a keyword argument.

```py
uc = UploadCare(pub_key='my-public-key', secret_key='my-secret-key')

# Set expiration as a unix timestamp
url = uc.upload(file, expire=1653429047) 

# Or, as a string
url = uc.upload(file, expire='in 30m')
url = uc.upload(file, expire='in 3 days')
url = uc.upload(file, expire='31-05-2022')
```

To view all supported methods, see: [uploadcare.UploadCare](https://alyetama.github.io/uploadcare-python/uploadcare.html#uploadcare.uploadcare.UploadCare)
