#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data operations panel."""

from numpy import ones, sqrt

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL
from PyQt4.QtGui import QWidget

from ufit.gui.common import loadUi
from ufit.data.merge import rebin


class DataOps(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.data = None
        self.picking = None
        self.picked_points = []

        loadUi(self, 'dataops.ui')
        self.pickedlabel.hide()

    def initialize(self, data):
        self.data = data
        if self.data.fitmin is not None:
            self.limitmin.setText('%.5g' % self.data.fitmin)
        if self.data.fitmax is not None:
            self.limitmax.setText('%.5g' % self.data.fitmax)
        self.monscale.setText(str(self.data.nscale))

    def on_canvas_pick(self, event):
        if not hasattr(event, 'artist'):
            return
        if self.picking:
            xdata = event.artist.get_xdata()[event.ind]
            self.picked_points.append(xdata)
            self.pickedlabel.setText('%d picked' % len(self.picked_points))

    @qtsig('')
    def on_badResetBtn_clicked(self):
        self.data.mask = ones(len(self.data.x), bool)
        self.emit(SIGNAL('replotRequest'))

    @qtsig('')
    def on_badPointsBtn_clicked(self):
        if self.picking == 'bad':
            self.badPointsBtn.setText('Start')
            self.pickedlabel.hide()
            self.picking = None
            self.removeBadPoints(self.picked_points)
        elif not self.picking:
            self.badPointsBtn.setText('Click points on plot, then '
                                      'here to finish')
            self.emit(SIGNAL('pickRequest'), self)
            self.picking = 'bad'
            self.picked_points = []
            self.pickedlabel.setText('0 picked')
            self.pickedlabel.show()

    @qtsig('')
    def on_limitsBtn_clicked(self):
        try:
            limitmin = float(self.limitmin.text())
        except ValueError:
            limitmin = None
        try:
            limitmax = float(self.limitmax.text())
        except ValueError:
            limitmax = None
        self.data.fitmin, self.data.fitmax = limitmin, limitmax
        self.emit(SIGNAL('replotRequest'))

    def removeBadPoints(self, points):
        """'Remove' bad data points (just mask them out)."""
        for point in points:
            self.data.mask[self.data.x == point] = False
        self.emit(SIGNAL('replotRequest'))

    @qtsig('')
    def on_rebinBtn_clicked(self):
        binsize = self.precision.value()
        new_array = rebin(self.data.x, self.data.y_raw, self.data.norm_raw,
                          binsize)
        self.data.__init__([self.data.xcol, self.data.ycol, self.data.ncol],
                           new_array, self.data.meta,
                           self.data.xcol, self.data.ycol, self.data.ncol,
                           self.data.nscale, name=self.data.name,
                           sources=self.data.sources)
        self.emit(SIGNAL('replotRequest'))

    @qtsig('')
    def on_mulBtn_clicked(self):
        try:
            const = float(self.mul_constant.text())
        except ValueError:
            return
        self.data.y *= const
        self.data.y_raw *= const
        self.data.dy *= const
        self.emit(SIGNAL('replotRequest'), None)

    @qtsig('')
    def on_addBtn_clicked(self):
        try:
            const = float(self.add_constant.text())
        except ValueError:
            return
        self.data.y += const
        self.data.y_raw += const * self.data.norm
        # XXX how to treat dy?
        self.emit(SIGNAL('replotRequest'), None)

    @qtsig('')
    def on_shiftBtn_clicked(self):
        try:
            const = float(self.shift_constant.text())
        except ValueError:
            return
        self.data.x += const
        self.emit(SIGNAL('replotRequest'), None)

    @qtsig('')
    def on_monscaleBtn_clicked(self):
        try:
            const = int(self.monscale.text())
        except ValueError:
            return
        self.data.nscale = const
        self.data.norm = self.data.norm_raw / const
        self.data.y = self.data.y_raw/self.data.norm
        self.data.dy = sqrt(self.data.y_raw)/self.data.norm
        self.emit(SIGNAL('replotRequest'), None)
