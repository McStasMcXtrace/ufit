#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data browsing window for the standalone GUI."""

import os
from os import path

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL, QVariant
from PyQt4.QtGui import QMainWindow, QListWidgetItem, QVBoxLayout

from ufit.data import Loader
from ufit.utils import extract_template
from ufit.gui.common import loadUi, MPLCanvas, MPLToolbar, SettingGroup


class BrowseWindow(QMainWindow):
    def __init__(self, parent):
        QMainWindow.__init__(self, parent)
        loadUi(self, 'browse.ui')
        self.dirBtn.hide()
        self.loader = Loader()
        self._data = {}
        self.canvas = MPLCanvas(self)
        self.canvas.plotter.lines = True
        self.toolbar = MPLToolbar(self.canvas, self)
        self.toolbar.setObjectName('browsetoolbar')
        self.addToolBar(self.toolbar)
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.plotframe.setLayout(layout)
        self.sgroup = SettingGroup('browse')

        with self.sgroup as settings:
            geometry = settings.value('geometry').toByteArray()
            self.restoreGeometry(geometry)
            windowstate = settings.value('windowstate').toByteArray()
            self.restoreState(windowstate)
            splitstate = settings.value('splitstate').toByteArray()
            self.splitter.restoreState(splitstate)
            #vsplitstate = settings.value('vsplitstate').toByteArray()
            #self.vsplitter.restoreState(vsplitstate)

    @qtsig('')
    def on_loadBtn_clicked(self):
        datas = [self._data[item.type()] for item in self.datalist.selectedItems()]
        if not datas:
            return
        loadwin = self.parent()
        for data in datas[:-1]:
            loadwin.emit(SIGNAL('newData'), data, False)
        loadwin.emit(SIGNAL('newData'), datas[-1])

    def set_template(self, template):
        self.setWindowTitle('ufit browser - %s' % template)
        root = path.dirname(template)
        files = os.listdir(root)
        for fn in sorted(files):
            fn = path.join(root, fn)
            try:
                t, n = extract_template(fn)
                self.loader.template = t
                res = self.loader.load(n, 'auto', 'auto', 'auto', 'auto', -1)
            except Exception, e:
                print e
            else:
                self._data[n] = res
                QListWidgetItem('%s (%s) - %s' % (n, res.xcol,
                                                  res.meta.get('title', '?')),
                                self.datalist, n)

    def on_datalist_itemSelectionChanged(self):
        numors = [item.type() for item in self.datalist.selectedItems()]
        if not numors:
            return
        plotter = self.canvas.plotter
        plotter.reset(False)
        if len(numors) > 1:
            for numor in numors:
                plotter.plot_data(self._data[numor], multi=True)
            plotter.plot_finish()
        else:
            plotter.plot_data(self._data[numors[0]])
        plotter.draw()

    def closeEvent(self, event):
        event.accept()
        with self.sgroup as settings:
            settings.setValue('geometry', QVariant(self.saveGeometry()))
            settings.setValue('windowstate', QVariant(self.saveState()))
            settings.setValue('splitstate', QVariant(self.splitter.saveState()))
            #settings.setValue('vsplitstate',
            #                  QVariant(self.vsplitter.saveState()))
