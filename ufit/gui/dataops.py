#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data operations panel."""

from numpy import sqrt, ones, zeros, arange, linspace
from scipy.interpolate import interp1d
from scipy.fftpack import fft

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL
from PyQt4.QtGui import QWidget, QDialog, QMessageBox

from ufit.data.merge import rebin, floatmerge
from ufit.data.dataset import ScanData
from ufit.gui.common import loadUi, SettingGroup
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
        self.fftNpointsEdit.setText(str(len(self.data.x) * 4))

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
        new_array, new_meta = rebin(self.data._data, binsize, self.data.meta)
        self.data.__init__(new_meta, new_array,
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
        new_array, new_meta = floatmerge(self.data._data, binsize,
                                         self.data.meta)
        self.data.__init__(new_meta, new_array,
                           self.data.xcol, self.data.ycol, self.data.ncol,
                           self.data.nscale, name=self.data.name,
                           sources=self.data.sources)
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty()

    @qtsig('')
    def on_cloneBtn_clicked(self):
        new_data = self.data.copy()
        new_model = self.model.copy()
        from ufit.gui.scanitem import ScanDataItem
        session.add_item(ScanDataItem(new_data, new_model), self.item.group)

    @qtsig('')
    def on_arbBtn_clicked(self):
        dlg = QDialog(self)
        loadUi(dlg, 'change.ui')
        with SettingGroup('main') as settings:
            dlg.xEdit.setText(settings.value('changex', 'x'))
            dlg.yEdit.setText(settings.value('changey', 'y'))
            dlg.dyEdit.setText(settings.value('changedy', 'dy'))
            if dlg.exec_() != QDialog.Accepted:
                return
            settings.setValue('changex', dlg.xEdit.text())
            settings.setValue('changey', dlg.yEdit.text())
            settings.setValue('changedy', dlg.dyEdit.text())
        xfml = dlg.xEdit.text()
        yfml = dlg.yEdit.text()
        dyfml = dlg.dyEdit.text()
        new_x = []
        new_y = []
        new_dy = []
        ns = {}
        for dpoint in zip(self.data.x, self.data.y_raw, self.data.dy_raw):
            ns.update(x=dpoint[0], y=dpoint[1], dy=dpoint[2])
            new_x.append(eval(xfml, ns))
            new_y.append(eval(yfml, ns))
            new_dy.append(eval(dyfml, ns))
        self.data.x[:] = new_x
        self.data.y_raw[:] = new_y
        self.data.dy_raw[:] = new_dy
        self.data.y = self.data.y_raw / self.data.norm
        self.data.dy = self.data.dy_raw / self.data.norm
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty()

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
    def on_scaleXBtn_clicked(self):
        try:
            const = float(self.scaleXConstEdit.text())
        except ValueError:
            return
        self.data.x *= const
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
        self.data.rescale(const)
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
        from ufit.gui.scanitem import ScanDataItem
        dlg = QDialog(self)
        loadUi(dlg, 'subtract.ui')
        data2obj = dlg.setList.populate(ScanDataItem)
        if dlg.exec_() != QDialog.Accepted:
            return
        witems = dlg.setList.selectedItems()
        if not witems:
            return
        try:
            prec = float(dlg.precisionEdit.text())
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Please enter a valid precision.')
            return
        bkgd_data = data2obj[witems[0].type()].data
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
            from ufit.gui.scanitem import ScanDataItem
            session.add_item(ScanDataItem(new_data, new_model), self.item.group)
        else:
            self.emit(SIGNAL('replotRequest'), None)
            session.set_dirty()

    @qtsig('')
    def on_fftBtn_clicked(self):
        try:
            npoints = int(self.fftNpointsEdit.text())
        except ValueError:
            QMessageBox.warning(self, 'Error',
                                'Please enter a valid number of points.')
            return
        xmin = self.data.x.min()
        xmax = self.data.x.max()
        xinterp = linspace(xmin, xmax, npoints)
        yinterp = interp1d(self.data.x, self.data.y, kind='linear')
        yfft = fft(yinterp(xinterp))
        p2 = abs(yfft) / npoints
        p1 = p2[:npoints//2 + 2]
        p1[1:-1] *= 2
        dx = (xmax - xmin) / (npoints - 1)

        new_data = ScanData.from_arrays(
            name='FFT(' + self.data.name + ')',
            x=(1./dx) * arange(npoints//2 + 2) / npoints,
            y=p1,
            dy=0.01*ones(p1.shape),
            xcol='1/' + self.data.xaxis,
            ycol='|P1|')
        new_model = self.model.copy()
        from ufit.gui.scanitem import ScanDataItem
        session.add_item(ScanDataItem(new_data, new_model), self.item.group)
