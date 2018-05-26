#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data browsing window for the standalone GUI."""

import os
from os import path

from PyQt4.QtCore import pyqtSignature as qtsig, QByteArray
from PyQt4.QtGui import QMainWindow, QApplication, QListWidgetItem, \
    QVBoxLayout, QFileDialog

from ufit.data import Loader
from ufit.utils import extract_template
from ufit.gui import logger
from ufit.gui.common import loadUi, MPLCanvas, MPLToolbar, SettingGroup, \
    path_to_str
from ufit.gui.session import session
from ufit.gui.scanitem import ScanDataItem


class Unavailable(object):
    def __format__(self, fmt):
        # Accepts all format strings (important for e.g. ".2f")
        return '???'


class FormatWrapper(object):
    """Wraps a dataset for the purposes of format() not raising exceptions."""

    def __init__(self, dataset):
        self.__dataset = dataset

    def __getattr__(self, attr, default=Unavailable()):
        val = getattr(self.__dataset, attr, default)
        if isinstance(val, list):
            return ', '.join(map(str, val))
        return val

    def __getitem__(self, attr):
        return getattr(self, attr)


class BrowseWindow(QMainWindow):
    def __init__(self, parent):
        QMainWindow.__init__(self, parent)
        loadUi(self, 'browse.ui')
        self.logger = logger.getChild('browse')

        self.rootdir = ''
        self.loader = Loader()
        self._data = {}
        self.canvas = MPLCanvas(self)
        self.canvas.plotter.lines = True
        self.toolbar = MPLToolbar(self.canvas, self)
        self.toolbar.setObjectName('browsetoolbar')
        self.addToolBar(self.toolbar)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self.plotframe.setLayout(layout)
        self.sgroup = SettingGroup('browse')

        with self.sgroup as settings:
            geometry = settings.value('geometry', QByteArray())
            self.restoreGeometry(geometry)
            windowstate = settings.value('windowstate', QByteArray())
            self.restoreState(windowstate)
            splitstate = settings.value('splitstate', QByteArray())
            self.splitter.restoreState(splitstate)
            self.monScaleEdit.setText(settings.value('fixedmonval'))

    @qtsig('')
    def on_loadBtn_clicked(self):
        datas = [self._data[item.type()] for item in self.dataList.selectedItems()]
        if not datas:
            return
        items = [ScanDataItem(data) for data in datas]
        # XXX which group
        session.add_items(items)

    @qtsig('')
    def on_dirBtn_clicked(self):
        newdir = QFileDialog.getExistingDirectory(self, 'New directory',
                                                  self.rootdir)
        self.set_directory(path_to_str(newdir))

    @qtsig('')
    def on_refreshBtn_clicked(self):
        self.set_directory(self.rootdir)

    @qtsig('')
    def on_monScaleBtn_clicked(self):
        self.set_directory(self.rootdir)

    def set_directory(self, root):
        self.setWindowTitle('ufit browser - %s' % root)
        self.canvas.axes.text(0.5, 0.5, 'Please wait, loading all data...',
                              horizontalalignment='center')
        self.canvas.draw()
        QApplication.processEvents()
        self.rootdir = root
        files = os.listdir(root)
        self.dataList.clear()
        for fn in sorted(files):
            fn = path.join(root, fn)
            if not path.isfile(fn):
                continue
            try:
                t, n = extract_template(fn)
                self.loader.template = t
                res = self.loader.load(n, 'auto', 'auto', 'auto', 'auto', -1)
            except Exception as e:
                self.logger.warning('While loading %r: %s' % (fn, e))
            else:
                if self.useMonScale.isChecked():
                    const = int(self.monScaleEdit.text())  # XXX check
                    res.rescale(const)
                if self.useFmtString.isChecked():
                    try:
                        scanLabel = self.fmtStringEdit.text().format(
                            n, FormatWrapper(res))
                    except Exception:
                        scanLabel = '%s (%s) - %s | %s' % (
                            n, res.xcol, res.title, ', '.join(res.environment))
                else:
                    scanLabel = '%s (%s) - %s | %s' % (
                        n, res.xcol, res.title, ', '.join(res.environment))
                self._data[n] = res
                QListWidgetItem(scanLabel, self.dataList, n)
        self.canvas.axes.clear()
        self.canvas.draw()

    def on_dataList_itemSelectionChanged(self):
        numors = [item.type() for item in self.dataList.selectedItems()]
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
            settings.setValue('geometry', self.saveGeometry())
            settings.setValue('windowstate', self.saveState())
            settings.setValue('splitstate', self.splitter.saveState())
            settings.setValue('fixedmonval', self.monScaleEdit.text())
