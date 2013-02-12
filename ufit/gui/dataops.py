#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data operations panel."""

from PyQt4.QtCore import pyqtSignature as qtsig
from PyQt4.QtGui import QWidget, QFileDialog, QDialogButtonBox, QMessageBox, \
     QMainWindow, QSplitter, QApplication

from ufit.gui.common import loadUi


class DataOps(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.data = None
        self.picking = None
        self.picked_points = []

        loadUi(self, 'dataops.ui')

    def initialize(self, data):
        self.data = data

    @qtsig('')
    def on_badPointsBtn_clicked(self):
        if self.picking == 'bad':
            self.on_badPointsBtn.setText('Remove bad datapoints')
            self.removeBadPoints(self.picked_points)
        elif not self.picking:
            self.on_badPointsBtn.setText('Click points on plot, then '
                                         'here to finish')

    def on_canvas_pick(self, event):
        if self.picking and event.xdata:
            self.picked_points.append((event.xdata, event.ydata))

    def removeBadPoints(self, points):
        pass
