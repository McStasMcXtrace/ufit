#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Session annotation window."""

from PyQt4.QtCore import SIGNAL, QByteArray
from PyQt4.QtGui import QMainWindow

from ufit.gui.common import SettingGroup, loadUi
from ufit.gui.session import session


class AnnotationWindow(QMainWindow):
    def __init__(self, parent):
        self._updating = False
        self._data = None
        QMainWindow.__init__(self, parent)
        loadUi(self, 'annotations.ui')
        self.sgroup = SettingGroup('annotations')

        self.connect(session, SIGNAL('propsRequested'),
                     self.on_session_propsRequested)
        self.connect(session, SIGNAL('propsUpdated'),
                     self.on_session_propsUpdated)

        with self.sgroup as settings:
            geometry = settings.value('geometry', QByteArray())
            self.restoreGeometry(geometry)
            windowstate = settings.value('windowstate', QByteArray())
            self.restoreState(windowstate)

        self._editing = True
        self.on_session_propsUpdated()

    def on_textBox_textChanged(self):
        if self._editing:
            session.set_dirty()

    def on_session_propsRequested(self):
        session.props.annotations = self.textBox.toPlainText()

    def on_session_propsUpdated(self):
        if 'annotations' in session.props:
            self._editing = False
            self.textBox.setText(session.props.annotations)
            self._editing = True

    def closeEvent(self, event):
        self.on_session_propsRequested()
        with self.sgroup as settings:
            settings.setValue('geometry', self.saveGeometry())
            settings.setValue('windowstate', self.saveState())
        self.emit(SIGNAL('closed'))
        return QMainWindow.closeEvent(self, event)
