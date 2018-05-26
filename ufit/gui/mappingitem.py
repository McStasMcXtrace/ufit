#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Panel for mappings."""

from numpy import array, mgrid
from matplotlib.cbook import flatten

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QFrame, QMessageBox

from ufit.data.dataset import Dataset
from ufit.data.mapping import bin_mapping
from ufit.models.peaks import Gauss2D
from ufit.utils import attrdict
from ufit.gui import logger
from ufit.gui.common import loadUi
from ufit.gui.session import session, SessionItem


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


class MappingItem(SessionItem):

    itemtype = 'mapping'

    def __init__(self, datas, settings):
        self.datas = datas
        self.settings = attrdict(settings or default_settings)
        SessionItem.__init__(self)

    def __reduce__(self):
        return (self.__class__, (self.datas, self.settings))

    def create_panel(self, mainwindow, canvas):
        return MappingPanel(mainwindow, canvas, self)

    def update_htmldesc(self):
        self.title = self.settings.title
        self.htmldesc = '<img src=":/map.png">&nbsp;&nbsp;<big><b>%d</b></big> ' \
                        '- %s<br>%s' % (
                            self.index, self.settings.title,
                            ', '.join(d.name for d in self.datas))
        session.emit(SIGNAL('itemUpdated'), self)


class MappingPanel(QFrame):

    def __init__(self, parent, canvas, item):
        QFrame.__init__(self, parent)
        loadUi(self, 'mapping.ui')
        self._limits = None
        self.item = item
        self.logger = logger.getChild('mapping')
        self.canvas = canvas
        self.mapdata = None
        self.set_datas(item.datas)
        self.set_settings(item.settings)

    @property
    def title(self):
        return self.settings.title

    def set_index(self, index):
        self.index = index
        self.gen_htmldesc()

    def set_datas(self, datas):
        axes = set(colname[4:] for colname in datas[0].meta
                   if colname.startswith('col_'))
        for data in datas[1:]:
            axes &= set(colname[4:] for colname in data.meta
                        if colname.startswith('col_'))
        axes = sorted(axes)
        self.xaxisBox.addItems(axes)
        self.yaxisBox.addItems(axes)

    def set_settings(self, s):
        """Update controls from settings."""
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
        s = self.item.settings
        old_title = s.title
        title = s.title = self.titleBox.text()
        if title != old_title:
            self.item.update_htmldesc()
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
        session.set_dirty()

    def on_buttonBox_clicked(self, button):
        """Apply button clicked."""
        self._update_settings()
        self.rebuild_map(quiet=False)
        self.plot()

    def rebuild_map(self, quiet=True):
        s = self.item.settings
        try:
            self.mapdata = bin_mapping(s.xaxis, s.yaxis, self.item.datas,
                                       usemask=s.usemask, log=s.logz,
                                       yscale=s.yscale, interpolate=s.interp,
                                       minmax=(s.zmin, s.zmax))
        except Exception as err:
            self.logger.exception('While creating mapping')
            if not quiet:
                QMessageBox.warning(self, 'Mapping error',
                                    'Could not create mapping: %s (have you '
                                    'selected the right columns?)' % err)
            return

    def plot(self, limits=True, canvas=None):
        s = self.item.settings
        canvas = canvas or self.canvas
        canvas.plotter.reset(limits)
        if not s.xaxis:
            canvas.draw()
            return
        if not self.mapdata:
            self.rebuild_map()
        canvas.plotter.plot_mapping(
            s.xaxis, s.yaxis, self.mapdata, title=s.title,
            mode=int(s.contour), dots=s.dots)
        if s.gauss2d:
            self.fit_2dgauss(s.xaxis, s.yaxis)
        canvas.draw()

    def save_limits(self):
        self._limits = self.canvas.axes.get_xlim(), self.canvas.axes.get_ylim()

    def get_saved_limits(self):
        return self._limits

    def fit_2dgauss(self, x, y):
        runs = self.item.datas
        if self.item.settings.usemask:
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
