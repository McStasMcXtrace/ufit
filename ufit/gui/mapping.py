#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data mapping window."""

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL
from PyQt4.QtGui import QWidget, QDialog, QMainWindow, QVBoxLayout, \
     QDialogButtonBox, QMessageBox

from ufit.gui.common import loadUi, MPLCanvas, MPLToolbar
from ufit.plotting import mapping as plot_mapping


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
        plot_mapping(xaxis, yaxis, self.datas,
                     minmax=(zmin, zmax),
                     yscale=yscale,
                     usemask=self.usemaskBox.isChecked(),
                     interpolate=self.stepBox.value(),
                     mat=not self.contourBox.isChecked(),
                     log=self.logBox.isChecked(),
                     dots=self.dotsBox.isChecked(),
                     figure=self.canvas.figure)
        self.canvas.draw()
