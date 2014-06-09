from Crypto.Cipher import AES
import base64
import os

class aescrypt():

    BLOCK_SIZE = 32
    PADDING = '{'
    pad = 0
    EncodeAES = 0
    DecodeAES = 0
    secret = ""
    cipher = ""

    def __init__(self, _secret):
        """

        :param name:
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

        self.secret = self.pad(_secret)

        # create a cipher object using the secret
        self.cipher = AES.new(self.secret)

    def encode(self, input):
        # encode a string
        encoded = self.EncodeAES(self.cipher, input)
        return encoded

    def decode(self, input):
        # decode the encoded string
        decoded = self.DecodeAES(self.cipher, input)
        return decoded