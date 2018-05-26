#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

import sys
from os import path

import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

from PyQt4 import QtGui

from ufit.gui.coverage import ReciprocalViewer

# Run the gui if not imported
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    win = ReciprocalViewer(None)
    sys.exit(app.exec_())
