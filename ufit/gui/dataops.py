#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data operations panel."""

from numpy import sqrt, mean, array, ones

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL
from PyQt4.QtGui import QWidget, QDialog, QListWidgetItem, QMessageBox

from ufit.gui.common import loadUi
from ufit.gui.mapping import MappingWindow
from ufit.data.merge import rebin
from ufit.data.dataset import Dataset


class DataOps(QWidget):

    def __init__(self, parent, panellist):
        QWidget.__init__(self, parent)
        self.data = None
        self.picking = None
        self.picked_points = []
        self.panellist = panellist

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
        # XXX fix this mess (title, name, environment, sources, ...)
        self.datatitle.setText(self.data.meta.get('title', ''))
        self.nameEdit.setText(self.data.name or '')

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
        self.data.yaxis = self.data.ycol + ' / %s %s' % (const, self.data.ncol)
        self.emit(SIGNAL('replotRequest'), None)
        self.emit(SIGNAL('dirty'))

    @qtsig('')
    def on_titleBtn_clicked(self):
        self.data.meta.title = str(self.datatitle.text())
        self.emit(SIGNAL('titleChanged'))
        self.emit(SIGNAL('dirty'))
        self.emit(SIGNAL('replotRequest'), None)

    @qtsig('')
    def on_nameBtn_clicked(self):
        self.data.name = str(self.nameEdit.text())
        self.emit(SIGNAL('dirty'))
        self.emit(SIGNAL('replotRequest'), None)

    @qtsig('')
    def on_subtractBtn_clicked(self):
        dlg = QDialog(self)
        loadUi(dlg, 'subtract.ui')
        for i, p in enumerate(self.panellist):
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
        bkgd_data = self.panellist[items[0].type()].data
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
            self.emit(SIGNAL('newData'), new_data, True, new_model)
        else:
            self.emit(SIGNAL('replotRequest'), None)
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
