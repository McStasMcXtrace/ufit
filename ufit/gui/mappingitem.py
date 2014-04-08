#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2014, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Panel for mappings."""

from numpy import array, mgrid
from matplotlib.cbook import flatten

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QFrame, QMessageBox

from ufit.data.dataset import Dataset
from ufit.models.peaks import Gauss2D
from ufit.plotting import bin_mapping
from ufit.utils import attrdict
from ufit.gui import logger
from ufit.gui.common import loadUi


def maybe_float(text, default):
    try:
        return float(text)
    except ValueError:
        return default


default_settings = {
    'title': 'mapping',
    'usemask': True,
    'contour': True,
    'dots': True,
    'interp': 100,
    'xaxis': '',
    'yaxis': '',
    'yscale': 1,
    'zmin': -1e300,
    'zmax': 1e300,
    'logz': False,
    'gauss2d': True,
}

class MappingPanel(QFrame):

    def __init__(self, parent, canvas, datas=None, settings=None):
        QFrame.__init__(self, parent)
        loadUi(self, 'mapping.ui')
        self.logger = logger.getChild('mapping')
        self.canvas = canvas
        self.index = 0
        self.mapdata = None
        if datas is not None:
            self.set_datas(datas)
        self.set_settings(attrdict(settings or default_settings))

    def set_index(self, index):
        self.index = index
        self.gen_htmldesc()

    def set_datas(self, datas):
        self.datas = datas
        self.settings = {}
        axes = set([colname[4:] for colname in datas[0].meta
                    if colname.startswith('col_')])
        for data in datas[1:]:
            axes &= set([colname[4:] for colname in data.meta
                         if colname.startswith('col_')])
        axes = sorted(axes)
        self.xaxisBox.addItems(axes)
        self.yaxisBox.addItems(axes)

    def set_settings(self, settings):
        """Update controls from settings."""
        s = self.settings = settings
        self.titleBox.setText(s.title)
        self.xaxisBox.setCurrentIndex(self.xaxisBox.findText(s.xaxis))
        self.yaxisBox.setCurrentIndex(self.yaxisBox.findText(s.yaxis))
        self.stepBox.setValue(s.interp)
        self.zminEdit.setText(str(s.zmin))
        self.zmaxEdit.setText(str(s.zmax))
        self.scaleEdit.setText(str(s.yscale))
        self.usemaskBox.setChecked(s.usemask)
        self.dotsBox.setChecked(s.dots)
        self.contourBox.setChecked(s.contour)
        self.logBox.setChecked(s.logz)
        self.fitBox.setChecked(s.gauss2d)

    def _update_settings(self):
        """Update settings from controls."""
        s = self.settings
        old_title = s.title
        title = s.title = self.titleBox.text()
        if title != old_title:
            self.update_htmldesc()
        xaxis = s.xaxis = str(self.xaxisBox.currentText())
        yaxis = s.yaxis = str(self.yaxisBox.currentText())
        if xaxis == yaxis:
            QMessageBox.warning(self, 'Error', 'Please select distinct X '
                               'and Y axes.')
            return
        s.interp = self.stepBox.value()
        s.zmin = maybe_float(self.zminEdit.text(), -1e300)
        s.zmax = maybe_float(self.zmaxEdit.text(), 1e300)
        s.yscale = maybe_float(self.scaleEdit.text(), 1.0)
        s.usemask = self.usemaskBox.isChecked()
        s.dots = self.dotsBox.isChecked()
        s.contour = self.contourBox.isChecked()
        s.logz = self.logBox.isChecked()
        s.gauss2d = self.fitBox.isChecked()
        self.set_dirty()

    def gen_htmldesc(self):
        self.htmldesc = '<img src=":/map.png">&nbsp;&nbsp;<big><b>%d</b></big> ' \
                        '- %s<br>%s' % (
            self.index, self.settings.title,
            ', '.join(d.name for d in self.datas))

    def update_htmldesc(self):
        self.gen_htmldesc()
        self.emit(SIGNAL('updateList'))

    def as_html(self):
        return self.htmldesc

    def serialize(self):
        return ('mapping', self.datas, self.settings)

    def set_dirty(self):
        self.emit(SIGNAL('dirty'))

    def on_buttonBox_clicked(self, button):
        """Apply button clicked."""
        self._update_settings()
        self.rebuild_map(quiet=False)
        self.replot(quiet=False)

    def rebuild_map(self, quiet=True):
        s = self.settings
        try:
            self.mapdata = bin_mapping(s.xaxis, s.yaxis, self.datas,
                                       usemask=s.usemask, log=s.logz,
                                       yscale=s.yscale, interpolate=s.interp,
                                       minmax=(s.zmin, s.zmax))
        except Exception, err:
            self.logger.exception('While creating mapping')
            if not quiet:
                QMessageBox.warning(self, 'Mapping error',
                                    'Could not create mapping: %s (have you '
                                    'selected the right columns?)' % err)
            return

    def replot(self, limits=None, quiet=True):
        if not self.mapdata:
            self.rebuild_map(quiet=quiet)
        # XXX handle limits
        self.canvas.plotter.reset()
        s = self.settings
        self.canvas.plotter.plot_mapping(
            s.xaxis, s.yaxis, self.mapdata, title=s.title,
            mode=int(s.contour), dots=s.dots)
        if s.gauss2d:
            self.fit_2dgauss(s.xaxis, s.yaxis)
        self.canvas.draw()

    def save_limits(self):
        pass # XXX

    def get_saved_limits(self):
        pass # XXX

    def fit_2dgauss(self, x, y):
        runs = self.datas
        if self.settings.usemask:
            xss = array(list(flatten(run['col_'+x][run.mask] for run in runs)))
            yss = array(list(flatten(run['col_'+y][run.mask] for run in runs)))
            zss = array(list(flatten(run.y[run.mask] for run in runs)))
            dzss = array(list(flatten(run.dy[run.mask] for run in runs)))
        else:
            xss = array(list(flatten(run['col_'+x] for run in runs)))
            yss = array(list(flatten(run['col_'+y] for run in runs)))
            zss = array(list(flatten(run.y for run in runs)))
            dzss = array(list(flatten(run.dy for run in runs)))
        maxidx = zss.argmax()
        xdata = array((xss, yss)).T
        model = Gauss2D(pos_x=xss[maxidx], pos_y=yss[maxidx],
                        fwhm_x=0.5*(xss.max()-xss.min()),
                        fwhm_y=0.5*(yss.max()-yss.min()), ampl=zss[maxidx])
        data = Dataset.from_arrays('2dgauss', xdata, zss, dzss)
        res = model.fit(data)
        xx, yy = mgrid[xss.min():xss.max():100j,
                       yss.min():yss.max():100j]
        mesh = array((xx.ravel(), yy.ravel())).T
        zmesh = model.fcn(res.paramvalues, mesh).reshape((100, 100))
        ax = self.canvas.figure.gca()
        ax.contour(xx, yy, zmesh)
        self.fitParLbl.setText('pos_x: %(pos_x).5f  pos_y: %(pos_y).5f  '
                               'theta: %(theta).5f  '
                               'fwhm_x: %(fwhm_x).5f  fwhm_y: %(fwhm_y).5f  '
                               'ampl: %(ampl).5f' % res.paramvalues)
