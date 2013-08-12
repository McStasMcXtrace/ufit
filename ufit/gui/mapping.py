#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data mapping window."""

from numpy import array, mgrid
from matplotlib.cbook import flatten

from PyQt4.QtGui import QMainWindow, QVBoxLayout, QDialogButtonBox, QMessageBox

from ufit.data.dataset import Dataset
from ufit.models.peaks import Gauss2D
from ufit.plotting import mapping as plot_mapping
from ufit.gui.common import loadUi, MPLCanvas, MPLToolbar


def maybe_float(text, default):
    try:
        return float(text)
    except ValueError:
        return default

class MappingWindow(QMainWindow):

    def __init__(self, parent):
        QMainWindow.__init__(self, parent)
        loadUi(self, 'mapping.ui')
        self.canvas = MPLCanvas(self)
        self.toolbar = MPLToolbar(self.canvas, self)
        self.addToolBar(self.toolbar)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self.plotFrame.setLayout(layout)

    def set_datas(self, datas):
        self.datas = datas
        axes = set([colname[4:] for colname in datas[0].meta
                    if colname.startswith('col_')])
        for data in datas[1:]:
            axes &= set([colname[4:] for colname in data.meta
                         if colname.startswith('col_')])
        axes = sorted(axes)
        self.xaxisBox.addItems(axes)
        self.yaxisBox.addItems(axes)

    def on_buttonBox_clicked(self, button):
        if self.buttonBox.buttonRole(button) == QDialogButtonBox.RejectRole:
            self.close()
            return
        xaxis = str(self.xaxisBox.currentText())
        yaxis = str(self.yaxisBox.currentText())
        if xaxis == yaxis:
            QMessageBox.warning(self, 'Error', 'Axes must be distinct.')
            return
        zmin = maybe_float(self.zminEdit.text(), -1e300)
        zmax = maybe_float(self.zmaxEdit.text(), 1e300)
        yscale = maybe_float(self.scaleEdit.text(), 1.0)
        try:
            plot_mapping(xaxis, yaxis, self.datas,
                         minmax=(zmin, zmax),
                         yscale=yscale,
                         usemask=self.usemaskBox.isChecked(),
                         interpolate=self.stepBox.value(),
                         mat=not self.contourBox.isChecked(),
                         log=self.logBox.isChecked(),
                         dots=self.dotsBox.isChecked(),
                         figure=self.canvas.figure)
        except Exception, err:
            QMessageBox.warning(self, 'Mapping error',
                                'Could not create mapping: %s (have you '
                                'selected the right columns?)' % err)
            return
        if self.fitBox.isChecked():
            self.fit_2dgauss(xaxis, yaxis)
        self.canvas.draw()

    def fit_2dgauss(self, x, y):
        runs = self.datas
        if self.usemaskBox.isChecked():
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
