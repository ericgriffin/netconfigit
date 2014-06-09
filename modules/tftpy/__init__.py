"""
This library implements the tftp protocol, based on rfc 1350.
http://www.faqs.org/rfcs/rfc1350.html
At the moment it implements only a client class, but will include a server,
with support for variable block sizes.

As a client of tftpy, this is the only module that you should need to import
directly. The TftpClient and TftpServer classes can be reached through it.
"""

import sys

# Make sure that this is at least Python 2.3
required_version = (2, 3)
if sys.version_info < required_version:
    raise ImportError, "Requires at least Python 2.3"

from modules.tftpy.TftpShared import *
from modules.tftpy.TftpPacketTypes import *
from modules.tftpy.TftpPacketFactory import *
from modules.tftpy.TftpClient import *
from modules.tftpy.TftpServer import *
from modules.tftpy.TftpContexts import *
from modules.tftpy.TftpStates import *

