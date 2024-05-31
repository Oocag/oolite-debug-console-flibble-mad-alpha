#
#  __init__.py
#  ooliteConsoleServer
#
#  Created by Jens Ayton on 2007-11-29.
#  Copyright (c) 2007 Jens Ayton. All rights reserved.
#


"""
Module to handle details of communicating with Oolite.
"""


try:
	pass
except ImportError:
	raise ImportError("ooliteConsoleServer requires Twisted (http://twistedmatrix.com/)")

from sys import version_info
if version_info.major  == 2:
	raise ImportError("Python2 no longer supported")
elif version_info.major  == 3: 		# Python 3.6 - (release date) December 23, 2016
	if version_info.minor < 6:
		raise ImportError("Python3 version must be at least 3.6")

from ooliteConsoleServer._protocol import defaultPort as defaultOoliteConsolePort
from ooliteConsoleServer.OoliteDebugConsoleProtocol import OoliteDebugConsoleProtocol


__author__	= "Jens Ayton <jens@ayton.se>"
__version__	= "1.0"


__all__ = ["PropertyListPacketProtocol", "OoliteDebugConsoleProtocol", "defaultOoliteConsolePort"]
