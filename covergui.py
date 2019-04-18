#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2019, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

import sys
from os import path

from ufit.qt import QApplication
from ufit.gui.coverage import ReciprocalViewer

# Run the gui if not imported
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ReciprocalViewer(None)
    sys.exit(app.exec_())
