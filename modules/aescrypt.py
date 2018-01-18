# -*- coding: utf-8 -*-
"""
AESCrypt class

Encrypts and decrypts data with AES encryption
"""

import os
import base64
from Crypto.Cipher import AES


class AESCrypt(object):
    """Encrypts and decrypts text data with AES encryption

    :param _secret: the encryption password
    """
    BLOCK_SIZE = 32
    PADDING = '{'
    pad = 0
    EncodeAES = 0
    DecodeAES = 0
    secret = ""
    cipher = ""

    def __init__(self, _secret):
        """Class constructor

        Pads the encryption password
        Creates an AES cipher object used for encryption/decryption
        :param _secret: the encryption password
        """
        # the block size for the cipher object - must be 16, 24, or 32 for AES
        self.BLOCK_SIZE = 16
        self.PADDING = '{'

        # sufficiently pad the text to be encrypted
        self.pad = lambda s: s + (self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE) * self.PADDING

        # encrypt/encode and decrypt/decode a string
        # encrypt with AES, encode with base64
        self.EncodeAES = lambda c, s: base64.b64encode(c.encrypt(self.pad(s)))
        self.DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(self.PADDING)

        # pad the encryption key to modulo 16
        self.secret = self.pad(_secret)

        # create a cipher object using the secret
        self.cipher = AES.new(self.secret)

    def encode(self, _input):
        """Encrypts data

        :param _input: plaintext input date
        :return encoded: encrypted data
        """
        # encode a string
        encoded = self.EncodeAES(self.cipher, _input)
        return encoded

    def decode(self, _input):
        """Decrypts data

        :param _input: ciphertext input data
        :return decoded: decrypted data
        """
        # decode the encoded string
        decoded = self.DecodeAES(self.cipher, _input)
        return decoded
