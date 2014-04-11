#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2014, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Multiple dataset operations panel."""

from numpy import sqrt, mean

from os import path

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL
from PyQt4.QtGui import QWidget, QDialog, QMessageBox

from ufit.gui.common import loadUi
from ufit.gui.session import session
from ufit.gui.mappingitem import MappingItem
from ufit.gui.datasetitem import DatasetItem
from ufit.gui.dialogs import ParamSetDialog
from ufit.data.merge import rebin


class MultiDataOps(QWidget):

    def __init__(self, parent, canvas):
        QWidget.__init__(self, parent)
        self.data = None
        self.canvas = canvas

        loadUi(self, 'multiops.ui')

    def initialize(self, items):
        self.items = [i for i in items if isinstance(i, DatasetItem)]
        self.datas = [i.data for i in self.items]
        self.monscaleEdit.setText(str(int(mean([d.nscale for d in self.datas]))))
        self.onemodelBox.clear()
        self.onemodelBox.addItems(['%d' % i.index for i in self.items])

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
        session.set_dirty()

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
        session.set_dirty(True)

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
        session.set_dirty(True)

    @qtsig('')
    def on_shiftBtn_clicked(self):
        try:
            const = float(self.shiftConstEdit.text())
        except ValueError:
            return
        for data in self.datas:
            data.x += const
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty(True)

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
        session.set_dirty(True)

    @qtsig('')
    def on_mergeBtn_clicked(self):
        try:
            precision = float(self.mergeEdit.text())
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Enter a valid precision.')
            return
        new_data = self.datas[0].merge(precision, *self.datas[1:])
        session.add_item(DatasetItem(new_data), self.items[-1].group)

    @qtsig('')
    def on_floatMergeBtn_clicked(self):
        try:
            precision = float(self.mergeEdit.text())
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Enter a valid precision.')
            return
        new_data = self.datas[0].merge(precision, floatmerge=True, *self.datas[1:])
        session.add_item(DatasetItem(new_data), self.items[-1].group)

    @qtsig('')
    def on_onemodelBtn_clicked(self):
        which = self.onemodelBox.currentIndex()
        if which < 0:
            return
        model = self.items[which].model
        for i, item in enumerate(self.items):
            if i == which:
                continue
            item.change_model(model.copy())
        self.emit(SIGNAL('replotRequest'), None)

    @qtsig('')
    def on_paramsetBtn_clicked(self):
        dlg = ParamSetDialog(self, self.items)
        if dlg.exec_() != QDialog.Accepted:
            return
        session.add_item(DatasetItem(dlg.new_data), self.items[-1].group)

    @qtsig('')
    def on_mappingBtn_clicked(self):
        item = MappingItem([item.data for item in self.items], None)
        session.add_item(item, self.items[-1].group)

    @qtsig('')
    def on_globalfitBtn_clicked(self):
        QMessageBox.warning(self, 'Sorry', 'Not implemented yet.')

    def export_ascii(self, filename):
        base, ext = path.splitext(filename)
        for i, item in enumerate(self.items):
            item.export_ascii(base + '.%d' % i + ext)

    def export_fits(self, filename):
        base, ext = path.splitext(filename)
        for i, item in enumerate(self.items):
            item.export_fits(base + '.%d' % i + ext)

    def export_python(self, filename):
        base, ext = path.splitext(filename)
        for i, item in enumerate(self.items):
            item.export_python(base + '.%d' % i + ext)
