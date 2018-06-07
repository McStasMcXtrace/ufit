#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Qt 4/5 compatibility layer."""

import sys

try:
    import PyQt5

except (ImportError, RuntimeError):
    import sip
    sip.setapi('QString', 2)
    sip.setapi('QVariant', 2)

    from PyQt4.QtGui import *
    from PyQt4.QtCore import *
    from PyQt4.QtSvg import *
    from PyQt4 import uic

    import ufit.guires_qt4
    QTVER = 4

else:
    # Do not abort on exceptions in signal handlers.
    sys.excepthook = lambda *args: sys.__excepthook__(*args)

    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import *
    from PyQt5.QtSvg import *
    from PyQt5 import uic

    import ufit.guires_qt5
    QTVER = 5
