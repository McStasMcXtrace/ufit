#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

import sys
from os import path

import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

import numpy as np
from PyQt4 import QtCore, QtGui, uic

from ufit.gui.common import MPLCanvas, MPLToolbar, SettingGroup, path_to_str
from ufit.utils import extract_template

import ufit.qreader as qr
import ufit.bzplot as bp



# show the points
class ReciprocalViewer(QtGui.QMainWindow):

    def __init__(self, parent):
        """ Constructing a basic QApplication
        """
        QtGui.QMainWindow.__init__(self, parent)
        self.sgroup = SettingGroup('main')
        self.ui = uic.loadUi(path.join(path.dirname(__file__), 'ui', 'qexplorer.ui'), self)
        self.addWidgets()
        self.ui.show()
        self.dir = path.dirname(__file__)
        self.pts = []
        self.canvas = MPLCanvas(self)
        self.canvas.plotter.lines = True
        self.toolbar = MPLToolbar(self.canvas, self)
        self.toolbar.setObjectName('browsetoolbar')
        self.addToolBar(self.toolbar)
        self.v1 = [1, 0, 0]
        self.v2 = [0, 0, 1]
        layout = QtGui.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self.frmPlot.setLayout(layout)
        self.Reader = None

        # restore settings
        with self.sgroup as settings:
            data_template_path = settings.value('last_data_template', '')
            print(settings.value('test', ''))
            if data_template_path:
                dtempl, numor = extract_template(data_template_path)
                self.dir = dtempl
                self.ui.txtNumors.setText(str(numor))
                print("directory set to", self.dir)

    def closeEvent(self, event):
        with self.sgroup as settings:
            settings.setValue('test', 'abc')


    def addWidgets(self):
        """ Connecting signals
        """
        self.connect(self.ui.btnLoad, QtCore.SIGNAL("clicked()"), self.readData)
        self.connect(self.ui.btnSelectDir, QtCore.SIGNAL("clicked()"), self.changeDir)
        self.connect(self.ui.btnShow, QtCore.SIGNAL("clicked()"), self.readPoints)
        self.connect(self.ui.btnAddBZ, QtCore.SIGNAL("clicked()"), self.addBZ)
        self.connect(self.ui.fltEmax, QtCore.SIGNAL("valueChanged(double)"), self.showPoints)
        self.connect(self.ui.fltEmin, QtCore.SIGNAL("valueChanged(double)"), self.showPoints)
        self.connect(self.ui.chkBigFont, QtCore.SIGNAL("stateChanged(int)"), self.bigFont)

    def readData(self):
        """ This function will read data from files indicated by folder and Numors """

        numors = self.ui.txtNumors.text()
        self.canvas.axes.text(0.5, 0.5, 'Please wait, loading all data...',
                              horizontalalignment='center')
        self.canvas.draw()
        QtGui.QApplication.processEvents()
        self.reader = qr.QReader(self.dir, numors)
        self.canvas.axes.clear()
        self.canvas.draw()

    def readVectors(self):
        """ Reading orientation vectors from text fields """

        self.v1 = [float(xx) for xx in str(self.ui.txtV1.text()).split()]
        self.v2 = [float(xx) for xx in str(self.ui.txtV2.text()).split()]

    def readPoints(self):
        """ It will find points in read scan files which has hkle values
        These is then converted to orientation vector basis and calculated distance from it.
        Only inplane points are processed.
        """

        self.readVectors()
        self.canvas.axes.text(0.5, 0.5, 'Please wait, parsing read data...',
                              horizontalalignment='center')
        self.canvas.draw()
        QtGui.QApplication.processEvents()
        self.pts = self.reader.get_points(self.v1, self.v2)
        print("Datafiles read:", len(self.pts))
        self.canvas.axes.clear()
        self.canvas.draw()
        self.showPoints()

    def showPoints(self):
        """ Will show read points in selected E range to canvas  """
        plotter = self.canvas.plotter
        plotter.reset(False)
        x = []
        y = []
        emin = self.ui.fltEmin.value()
        emax = self.ui.fltEmax.value()

        for pt in self.pts:
            if pt[2] >= emin and pt[2] <= emax:  # ok, show point
                x.append(pt[0])
                y.append(pt[1])

        plotter.axes.plot(x, y, 'ro')
        plotter.axes.set_title('Measured points in reciprocal space', size='medium')
        plotter.axes.set_xlabel("x . (%.1f, %.1f, %.1f)" % tuple(self.v1))
        plotter.axes.set_ylabel("y . (%.1f, %.1f, %.1f)" % tuple(self.v2))
        plotter.draw()

    def changeDir(self):
        """ Change directory from which are the data read  """

        if self.dir:
            startdir = self.dir
        else:
            startdir = '.'
        fn = path_to_str(QtGui.QFileDialog.getOpenFileName(
            self, 'Choose a file', startdir, 'All files (*)'))
        if not fn:
            return
        dtempl, numor = extract_template(fn)
        self.dir = dtempl
        self.ui.txtNumors.setText(str(numor))
        print("directory changed to", self.dir)

    def bigFont(self, state):
        """ Increase font size  """
        # TODO: should be done more sofisticated with more configuration

        ax = self.canvas.plotter.axes
        sizes = {
            "normal": [12, 10, 10],
            "big": [24, 22, 18]
        }
        if state == 0:  # normal size
            toset = sizes["normal"]
        else:
            toset = sizes["big"]

        ax.title.set_fontsize(toset[0])
        ax.xaxis.label.set_fontsize(toset[1])
        ax.yaxis.label.set_fontsize(toset[1])
        for t in ax.xaxis.get_major_ticks():
            t.label.set_fontsize(toset[2])
        for t in ax.yaxis.get_major_ticks():
            t.label.set_fontsize(toset[2])
        if (ax.legend_):
            for t in ax.legend_.texts:
                t.set_fontsize(toset[1])
        self.canvas.plotter.draw()

    def addBZ(self):
        """ Experimental: add brilluin zone. Only Body centered tetragonal now supported. """

        # check by vectors
        self.readVectors()
        myplane = np.cross(self.v1, self.v2)
        # TODO: generate gamma point dynamically
        gpts = np.array([[0, 0], [0, 2], [1, 1], [2, 0], [2, 2]])

        # TODO: read lattice parameters from file
        bzc = bp.BZCreator(gpts, a = 4.33148, c = 10.83387, plane = myplane)
        bzc.doPlot(self.canvas.plotter.axes)
        self.canvas.plotter.draw()


# Run the gui if not imported
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    win = ReciprocalViewer()
    sys.exit(app.exec_())
