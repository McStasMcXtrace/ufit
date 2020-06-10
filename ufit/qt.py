#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2020, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Qt compatibility layer."""

import sys

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtPrintSupport import *
from PyQt5.QtSvg import *
from PyQt5 import uic

import ufit.guires_qt5

# Do not abort on exceptions in signal handlers.
sys.excepthook = lambda *args: sys.__excepthook__(*args)
