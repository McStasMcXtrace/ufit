#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2019, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Embedded IPython qt console."""

from ufit.qt import pyqtSignal, QMainWindow

from qtconsole.rich_ipython_widget import RichIPythonWidget
from qtconsole.inprocess import QtInProcessKernelManager


class QIPythonWidget(RichIPythonWidget):
    """Convenience class for a live IPython console widget."""

    closeme = pyqtSignal()
    redrawme = pyqtSignal()

    def __init__(self, customBanner=None, *args, **kwargs):
        if customBanner is not None:
            self.banner = customBanner
        super(QIPythonWidget, self).__init__(*args, **kwargs)
        self.kernel_manager = kernel_manager = QtInProcessKernelManager()
        kernel_manager.start_kernel()
        kernel_manager.kernel.gui = 'qt4'
        self.kernel_client = kernel_client = self._kernel_manager.client()
        kernel_client.start_channels()

        def stop():
            kernel_client.stop_channels()
            kernel_manager.shutdown_kernel()
            self.closeme.emit()
        self.exit_requested.connect(stop)

        def redraw():
            self.redrawme.emit()
        self.executed.connect(redraw)

    def pushVariables(self, variableDict):
        """Given a dictionary containing name / value pairs, push those
        variables to the IPython console widget.
        """
        self.kernel_manager.kernel.shell.push(variableDict)

    def clearTerminal(self):
        """Clears the terminal."""
        self._control.clear()

    def printText(self, text):
        """Prints some plain text to the console."""
        self._append_plain_text(text)

    def executeCommand(self, command):
        """Execute a command in the frame of the console widget."""
        self._execute(command, True)


class ConsoleWindow(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setWindowTitle('ufit Python console')
        self.ipython = QIPythonWidget(
            '''\
ufit interactive Python shell

Objects in the namespace:
* fig -- figure of the main viewport
* ax  -- current axes of the main viewport
* D   -- list of dataset items
            ''',
            self)
        self.setCentralWidget(self.ipython)

        self.ipython.closeme.connect(self.close)
        self.ipython.redrawme.connect(parent.canvas.draw)
