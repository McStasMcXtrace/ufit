#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data operations panel."""

from numpy import sqrt, mean

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL
from PyQt4.QtGui import QWidget, QDialog, QMainWindow

from ufit.gui.common import loadUi
from ufit.gui.mapping import MappingWindow
from ufit.data.merge import rebin


class DataOps(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.data = None
        self.picking = None
        self.picked_points = []

        loadUi(self, 'dataops.ui')
        self.pickedlabel.hide()

    def initialize(self, data, model):
        self.data = data
        self.model = model
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
            ydata = event.artist.get_ydata()[event.ind]
            self.picked_points.append(xdata)
            self.pickedlabel.setText('%d picked' % len(self.picked_points))
            event.canvas.figure.gca().plot([xdata], [ydata], 'ow', ms=8,
                                           mec='blue')
            event.canvas.draw()

    @qtsig('')
    def on_badResetBtn_clicked(self):
        self.data.reset_mask()
        self.emit(SIGNAL('replotRequest'))
        self.emit(SIGNAL('dirty'))

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
        self.emit(SIGNAL('dirty'))

    def removeBadPoints(self, points):
        """'Remove' bad data points (just mask them out)."""
        for point in points:
            self.data.mask[self.data.x == point] = False
        self.emit(SIGNAL('replotRequest'))
        self.emit(SIGNAL('dirty'))

    @qtsig('')
    def on_rebinBtn_clicked(self):
        binsize = self.precision.value()
        new_array = rebin(self.data._data, binsize)
        self.data.__init__(self.data.meta, new_array,
                           self.data.xcol, self.data.ycol, self.data.ncol,
                           self.data.nscale, name=self.data.name,
                           sources=self.data.sources)
        self.emit(SIGNAL('replotRequest'), None)
        self.emit(SIGNAL('dirty'))

    @qtsig('')
    def on_cloneBtn_clicked(self):
        new_data = self.data.copy()
        new_model = self.model.copy()
        self.emit(SIGNAL('newData'), new_data, True, new_model)
        self.emit(SIGNAL('dirty'))

    @qtsig('')
    def on_mulBtn_clicked(self):
        try:
            const = float(self.mul_constant.text())
        except ValueError:
            return
        self.data.y *= const
        self.data.y_raw *= const
        self.data.dy *= const
        self.data.dy_raw *= const
        self.emit(SIGNAL('replotRequest'), None)
        self.emit(SIGNAL('dirty'))

    @qtsig('')
    def on_addBtn_clicked(self):
        try:
            const = float(self.add_constant.text())
        except ValueError:
            return
        self.data.y += const
        self.data.y_raw += const * self.data.norm
        self.emit(SIGNAL('replotRequest'), None)
        self.emit(SIGNAL('dirty'))

    @qtsig('')
    def on_shiftBtn_clicked(self):
        try:
            const = float(self.shift_constant.text())
        except ValueError:
            return
        self.data.x += const
        self.emit(SIGNAL('replotRequest'), None)
        self.emit(SIGNAL('dirty'))

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
        self.emit(SIGNAL('dirty'))

    @qtsig('')
    def on_titleBtn_clicked(self):
        self.data.meta.title = str(self.datatitle.text())
        self.emit(SIGNAL('titleChanged'))
        self.emit(SIGNAL('dirty'))


class MultiDataOps(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.data = None

        loadUi(self, 'multiops.ui')

    def initialize(self, panels):
        self.panels = panels
        self.datas = [p.data for p in panels]
        self.monscale.setText(str(int(mean([d.nscale for d in self.datas]))))
        self.onemodel.clear()
        self.onemodel.addItems(['%d' % p.index for p in panels])

    @qtsig('')
    def on_rebinBtn_clicked(self):
        binsize = self.precision.value()
        for data in self.datas:
            new_array = rebin(data._data, binsize)
            data.__init__(data.meta, new_array,
                          data.xcol, data.ycol, data.ncol,
                          data.nscale, name=data.name,
                          sources=data.sources)
        self.emit(SIGNAL('replotRequest'), None)
        self.emit(SIGNAL('dirty'))

    @qtsig('')
    def on_mulBtn_clicked(self):
        try:
            const = float(self.mul_constant.text())
        except ValueError:
            return
        for data in self.datas:
            data.y *= const
            data.y_raw *= const
            data.dy *= const
            data.dy_raw *= const
        self.emit(SIGNAL('replotRequest'), None)
        self.emit(SIGNAL('dirty'))

    @qtsig('')
    def on_addBtn_clicked(self):
        try:
            const = float(self.add_constant.text())
        except ValueError:
            return
        for data in self.datas:
            data.y += const
            data.y_raw += const * data.norm
        self.emit(SIGNAL('replotRequest'), None)
        self.emit(SIGNAL('dirty'))

    @qtsig('')
    def on_shiftBtn_clicked(self):
        try:
            const = float(self.shift_constant.text())
        except ValueError:
            return
        for data in self.datas:
            data.x += const
        self.emit(SIGNAL('replotRequest'), None)
        self.emit(SIGNAL('dirty'))

    @qtsig('')
    def on_monscaleBtn_clicked(self):
        try:
            const = int(self.monscale.text())
        except ValueError:
            return
        for data in self.datas:
            data.nscale = const
            data.norm = data.norm_raw / const
            data.y = data.y_raw/data.norm
            data.dy = sqrt(data.y_raw)/data.norm
        self.emit(SIGNAL('replotRequest'), None)
        self.emit(SIGNAL('dirty'))

    @qtsig('')
    def on_mergeBtn_clicked(self):
        precision = self.mergeprecision.value()
        new_data = self.datas[0].merge(precision, *self.datas[1:])
        self.emit(SIGNAL('newData'), new_data)

    @qtsig('')
    def on_onemodelBtn_clicked(self):
        which = self.onemodel.currentIndex()
        if which < 0:
            return
        model = self.panels[which].model
        for i, panel in enumerate(self.panels):
            if i == which:
                continue
            panel.handle_new_model(model.copy(), keep_paramvalues=False)
        self.emit(SIGNAL('replotRequest'), None)
        self.emit(SIGNAL('dirty'))

    @qtsig('')
    def on_mappingBtn_clicked(self):
        wnd = MappingWindow(self)
        wnd.set_datas([panel.data for panel in self.panels])
        wnd.show()
