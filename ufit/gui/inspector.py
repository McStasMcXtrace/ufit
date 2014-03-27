#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2014, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Metadata view window."""

from PyQt4.QtCore import SIGNAL, QByteArray
from PyQt4.QtGui import QMainWindow, QTableWidgetItem

from ufit.gui.common import loadUi, SettingGroup


class InspectorWindow(QMainWindow):
    def __init__(self, parent):
        QMainWindow.__init__(self, parent)
        loadUi(self, 'inspector.ui')
        #layout = QVBoxLayout()
        #layout.setContentsMargins(0, 0, 0, 0)
        #layout.addWidget(self.canvas)
        self.sgroup = SettingGroup('inspector')
        self.tbl.verticalHeader().setDefaultSectionSize(
            self.tbl.verticalHeader().minimumSectionSize() + 2)

        with self.sgroup as settings:
            geometry = settings.value('geometry', QByteArray())
            self.restoreGeometry(geometry)
            windowstate = settings.value('windowstate', QByteArray())
            self.restoreState(windowstate)

    def newData(self, data):
        self.dataName.setText(data.meta.title or data.name)
        self.tbl.setRowCount(len(data.meta))
        for i, entry in enumerate(sorted(data.meta, key=lambda n: n.lower())):
            self.tbl.setItem(i, 0, QTableWidgetItem(entry))
            self.tbl.setItem(i, 1, QTableWidgetItem(str(data.meta[entry])))

    def closeEvent(self, event):
        self.emit(SIGNAL('closed'))
        return QMainWindow.closeEvent(self, event)

#    def on_
