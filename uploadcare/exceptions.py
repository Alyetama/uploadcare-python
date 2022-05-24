#!/usr/bin/env python
# coding: utf-8

class InvalidDatetimeString(Exception):
    """Raised when a datetime string is not in a recognizably valid format."""


class MissingExpireKwarg(Exception):
    """Raised when the user does not pass the `expire` keyword argument when
    using Secure Uploading."""

    def __init__(self):
        super().__init__(
            'When using Secure Uploading, you must pass keyword argument: '
            '`expire` (expire: Union[float, int, str]).')


class MissingSecretKey(Exception):
    """Raised when a secret key is required for Secure Uploads but not 
    provided."""

    def __init__(self):
        super().__init__('A secret key is required for Secure Uploads! Pass '
                         '`secret_key=...` to the class object.')
