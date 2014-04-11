#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2014, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data operations panel."""

from numpy import sqrt, ones

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL
from PyQt4.QtGui import QWidget, QDialog, QListWidgetItem, QMessageBox

from ufit.data.merge import rebin, floatmerge
from ufit.gui.common import loadUi
from ufit.gui.session import session


class DataOps(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.item = None
        self.data = None
        self.picking = None
        self.picked_points = []

        loadUi(self, 'dataops.ui')
        self.pickedLbl.hide()

    def initialize(self, item):
        self.data = item.data
        self.model = item.model
        self.item = item
        if self.data.fitmin is not None:
            self.limitminEdit.setText('%.5g' % self.data.fitmin)
        if self.data.fitmax is not None:
            self.limitmaxEdit.setText('%.5g' % self.data.fitmax)
        self.monscaleEdit.setText(str(self.data.nscale))
        self.titleEdit.setText(self.data.title)
        self.nameEdit.setText(self.data.name)

    def on_canvas_pick(self, event):
        if not hasattr(event, 'artist'):
            return
        if self.picking:
            xdata = event.artist.get_xdata()[event.ind]
            ydata = event.artist.get_ydata()[event.ind]
            self.picked_points.append(xdata)
            self.pickedLbl.setText('%d picked' % len(self.picked_points))
            event.canvas.figure.gca().plot([xdata], [ydata], 'ow', ms=8,
                                           mec='blue')
            event.canvas.draw()

    @qtsig('')
    def on_badResetBtn_clicked(self):
        self.data.reset_mask()
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty()

    @qtsig('')
    def on_badPointsBtn_clicked(self):
        if self.picking == 'bad':
            self.badPointsBtn.setText('Start')
            self.pickedLbl.hide()
            self.picking = None
            self.removeBadPoints(self.picked_points)
        elif not self.picking:
            self.badPointsBtn.setText('Click points on plot, then '
                                      'here to finish')
            self.emit(SIGNAL('pickRequest'), self)
            self.picking = 'bad'
            self.picked_points = []
            self.pickedLbl.setText('0 picked')
            self.pickedLbl.show()

    @qtsig('')
    def on_limitsBtn_clicked(self):
        try:
            limitmin = float(self.limitminEdit.text())
        except ValueError:
            limitmin = None
        try:
            limitmax = float(self.limitmaxEdit.text())
        except ValueError:
            limitmax = None
        self.data.fitmin, self.data.fitmax = limitmin, limitmax
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty()

    def removeBadPoints(self, points):
        """'Remove' bad data points (just mask them out)."""
        for point in points:
            self.data.mask[self.data.x == point] = False
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty()

    @qtsig('')
    def on_rebinBtn_clicked(self):
        try:
            binsize = float(self.precisionEdit.text())
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Enter a valid precision.')
            return
        new_array = rebin(self.data._data, binsize)
        self.data.__init__(self.data.meta, new_array,
                           self.data.xcol, self.data.ycol, self.data.ncol,
                           self.data.nscale, name=self.data.name,
                           sources=self.data.sources)
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty()

    @qtsig('')
    def on_floatmergeBtn_clicked(self):
        try:
            binsize = float(self.precisionEdit.text())
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Enter a valid precision.')
            return
        new_array = floatmerge(self.data._data, binsize)
        self.data.__init__(self.data.meta, new_array,
                           self.data.xcol, self.data.ycol, self.data.ncol,
                           self.data.nscale, name=self.data.name,
                           sources=self.data.sources)
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty()

    @qtsig('')
    def on_cloneBtn_clicked(self):
        new_data = self.data.copy()
        new_model = self.model.copy()
        from ufit.gui.datasetitem import DatasetItem
        session.add_item(DatasetItem(new_data, new_model), self.item.group)

    @qtsig('')
    def on_mulBtn_clicked(self):
        try:
            const = float(self.scaleConstEdit.text())
        except ValueError:
            return
        self.data.y *= const
        self.data.y_raw *= const
        self.data.dy *= const
        self.data.dy_raw *= const
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty()

    @qtsig('')
    def on_addBtn_clicked(self):
        try:
            const = float(self.addConstEdit.text())
        except ValueError:
            return
        self.data.y += const
        self.data.y_raw += const * self.data.norm
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty()

    @qtsig('')
    def on_shiftBtn_clicked(self):
        try:
            const = float(self.shiftConstEdit.text())
        except ValueError:
            return
        self.data.x += const
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty()

    @qtsig('')
    def on_monscaleBtn_clicked(self):
        try:
            const = int(self.monscaleEdit.text())
        except ValueError:
            return
        self.data.nscale = const
        self.data.norm = self.data.norm_raw / const
        self.data.y = self.data.y_raw/self.data.norm
        self.data.dy = sqrt(self.data.y_raw)/self.data.norm
        self.data.yaxis = self.data.ycol + ' / %s %s' % (const, self.data.ncol)
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty()

    @qtsig('')
    def on_titleBtn_clicked(self):
        self.data.meta.title = str(self.titleEdit.text())
        self.emit(SIGNAL('titleChanged'))
        session.set_dirty()
        self.emit(SIGNAL('replotRequest'), None)

    @qtsig('')
    def on_nameBtn_clicked(self):
        self.data.name = str(self.nameEdit.text())
        session.set_dirty()
        self.emit(SIGNAL('replotRequest'), None)

    @qtsig('')
    def on_subtractBtn_clicked(self):
        dlg = QDialog(self)
        loadUi(dlg, 'subtract.ui')
        # XXX
        for i, p in enumerate(session.items):
            QListWidgetItem('%d' % p.index, dlg.setList, i)
        if dlg.exec_() != QDialog.Accepted:
            return
        items = dlg.setList.selectedItems()
        if not items:
            return
        try:
            prec = float(dlg.precisionEdit.text())
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Please enter a valid precision.')
            return
        # XXX
        bkgd_data = session.items[items[0].type()].data
        if not dlg.destructBox.isChecked():
            new_data = self.data.copy()
        else:
            new_data = self.data
        new_data.name = new_data.name + '-' + bkgd_data.name
        new_data.sources.extend(bkgd_data.sources)

        # Subtraction algorithm works as follows: for each point in the
        # background, the points in the original data with an X value within
        # the selected precision are looked up, and the Y value is subtracted.
        # An array of indices is kept so that from every original data point
        # background is subtracted at most once.

        # indices of data points not corrected
        ind_unused = ones(len(new_data.x), dtype=bool)
        for xb, yb, dyb, nb in bkgd_data._data:
            ind = ind_unused & (new_data.x >= xb - prec) & (new_data.x <= xb + prec)
            scale = new_data.norm_raw[ind]/nb
            new_data.y_raw[ind] -= scale * yb
            new_data.dy_raw[ind] = sqrt(new_data.dy_raw[ind]**2 + (scale * dyb)**2)
            ind_unused &= ~ind
        new_data.y = new_data.y_raw / new_data.norm
        new_data.dy = new_data.dy_raw / new_data.norm
        # mask out points from which no background has been subtracted
        new_data.mask &= ~ind_unused

        if not dlg.destructBox.isChecked():
            new_model = self.model.copy()
            from ufit.gui.datasetitem import DatasetItem
            session.add_item(DatasetItem(new_data, new_model), self.item.group)
        else:
            self.emit(SIGNAL('replotRequest'), None)
            session.set_dirty()
