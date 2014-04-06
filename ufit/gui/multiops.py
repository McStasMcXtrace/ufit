#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2014, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Multiple dataset operations panel."""

from os import path

from numpy import sqrt, mean, array

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL
from PyQt4.QtGui import QWidget, QDialog, QMessageBox

from ufit.gui.common import loadUi
from ufit.gui.mapping import MappingWindow
from ufit.data.merge import rebin
from ufit.data.dataset import Dataset


class MultiDataOps(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.data = None

        loadUi(self, 'multiops.ui')

    def initialize(self, panels):
        self.panels = panels
        self.datas = [p.data for p in panels]
        self.monscaleEdit.setText(str(int(mean([d.nscale for d in self.datas]))))
        self.onemodelBox.clear()
        self.onemodelBox.addItems(['%d' % p.index for p in panels])

    @qtsig('')
    def on_rebinBtn_clicked(self):
        try:
            binsize = float(self.precisionEdit.text())
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Enter a valid precision.')
            return
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
            const = float(self.scaleConstEdit.text())
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
            const = float(self.addConstEdit.text())
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
            const = float(self.shiftConstEdit.text())
        except ValueError:
            return
        for data in self.datas:
            data.x += const
        self.emit(SIGNAL('replotRequest'), None)
        self.emit(SIGNAL('dirty'))

    @qtsig('')
    def on_monscaleBtn_clicked(self):
        try:
            const = int(self.monscaleEdit.text())
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
        try:
            precision = float(self.mergeEdit.text())
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Enter a valid precision.')
            return
        new_data = self.datas[0].merge(precision, *self.datas[1:])
        self.emit(SIGNAL('newData'), new_data)

    @qtsig('')
    def on_floatMergeBtn_clicked(self):
        try:
            precision = float(self.mergeEdit.text())
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Enter a valid precision.')
            return
        new_data = self.datas[0].merge(precision, floatmerge=True, *self.datas[1:])
        self.emit(SIGNAL('newData'), new_data)

    @qtsig('')
    def on_onemodelBtn_clicked(self):
        which = self.onemodelBox.currentIndex()
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
    def on_paramsetBtn_clicked(self):
        dlg = ParamSetDialog(self, self.panels)
        if dlg.exec_() != QDialog.Accepted:
            return
        self.emit(SIGNAL('newData'), dlg.new_data)

    @qtsig('')
    def on_mappingBtn_clicked(self):
        wnd = MappingWindow(self)
        wnd.set_datas([panel.data for panel in self.panels])
        wnd.show()

    @qtsig('')
    def on_globalfitBtn_clicked(self):
        QMessageBox.warning(self, 'Sorry', 'Not implemented yet.')

    def export_ascii(self, filename):
        base, ext = path.splitext(filename)
        for i, panel in enumerate(self.panels):
            panel.export_ascii(base + '.%d' % i + ext)


class ParamSetDialog(QDialog):
    def __init__(self, parent, panels):
        QDialog.__init__(self, parent)
        loadUi(self, 'paramset.ui')
        self.new_data = None
        self.panels = panels

        allvalues = set()
        for panel in panels:
            if not panel.model or not panel.data:
                return
            values = set([p.name + ' (parameter)' for p in panel.model.params] +
                         [mname + ' (from data)' for mname in panel.data.meta if
                          not mname.startswith('col_')])
            if not allvalues:
                allvalues = values
            else:
                allvalues &= values

        allvalues = sorted(allvalues)
        self.xvalueBox.addItems(allvalues)
        self.yvalueBox.addItems(allvalues)

    def exec_(self):
        res = QDialog.exec_(self)
        if res != QDialog.Accepted:
            return res
        xx, yy, dy = [], [], []
        xp = yp = False
        xv = str(self.xvalueBox.currentText())
        if xv.endswith(' (parameter)'):
            xp = True
        xv = xv[:-12]
        yv = str(self.yvalueBox.currentText())
        if yv.endswith(' (parameter)'):
            yp = True
        yv = yv[:-12]

        for panel in self.panels:
            if xp:
                xx.append(panel.model.paramdict[xv].value)
            else:
                xx.append(panel.data.meta[xv])
            if yp:
                yy.append(panel.model.paramdict[yv].value)
                dy.append(panel.model.paramdict[yv].error)
            else:
                yy.append(panel.data.meta[yv])
                dy.append(1)
        xx, yy, dy = map(array, [xx, yy, dy])

        self.new_data = Dataset.from_arrays(str(self.nameBox.text()),
                                            xx, yy, dy, xcol=xv, ycol=yv)
        return res
