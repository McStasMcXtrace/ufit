#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Metadata view window."""

from PyQt4.QtCore import SIGNAL, QByteArray, Qt
from PyQt4.QtGui import QMainWindow, QTableWidgetItem, QMessageBox

from ufit.gui.common import loadUi, SettingGroup
from ufit.gui.session import session
from ufit.pycompat import srepr


class InspectorWindow(QMainWindow):
    def __init__(self, parent):
        self._updating = False
        self._data = None
        QMainWindow.__init__(self, parent)
        loadUi(self, 'inspector.ui')
        # layout = QVBoxLayout()
        # layout.setContentsMargins(0, 0, 0, 0)
        # layout.addWidget(self.canvas)
        self.sgroup = SettingGroup('inspector')
        self.tbl.verticalHeader().setDefaultSectionSize(
            self.tbl.verticalHeader().minimumSectionSize() + 2)

        with self.sgroup as settings:
            geometry = settings.value('geometry', QByteArray())
            self.restoreGeometry(geometry)
            windowstate = settings.value('windowstate', QByteArray())
            self.restoreState(windowstate)

    def setDataset(self, data):
        self.data = data
        self.dataName.setText('%s - %s' % (data.name, data.title))
        self._updating = True
        self.tbl.setRowCount(len(data.meta))
        for i, key in enumerate(sorted(data.meta, key=lambda n: n.lower())):
            key_item = QTableWidgetItem(key)
            key_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)
            self.tbl.setItem(i, 0, key_item)
            if key.startswith('col_'):
                value_item = QTableWidgetItem(str(data.meta[key]))
                value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
            else:
                value_item = QTableWidgetItem(srepr(data.meta[key]))
            self.tbl.setItem(i, 1, value_item)
        self._updating = False

    def closeEvent(self, event):
        with self.sgroup as settings:
            settings.setValue('geometry', self.saveGeometry())
            settings.setValue('windowstate', self.saveState())
        self.emit(SIGNAL('closed'))
        return QMainWindow.closeEvent(self, event)

    def on_tbl_itemChanged(self, item):
        if self._updating:
            return
        try:
            new_value = eval(str(item.text()))
        except Exception:
            QMessageBox.error(self, 'Error',
                              'The new value is not a valid expression.')
            return
        else:
            key = str(self.tbl.item(item.row(), 0).text())
            self.data.meta[key] = new_value
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty()
