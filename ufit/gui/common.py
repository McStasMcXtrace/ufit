#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2014, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Common GUI elements."""

import sys
from os import path

from PyQt4 import uic
from PyQt4.QtCore import SIGNAL, QSize, QSettings, Qt
from PyQt4.QtGui import QLineEdit, QSizePolicy, QWidget, QIcon, QFileDialog, \
    QMessageBox

from matplotlib.backends.backend_qt4agg import \
    FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib import pyplot
try:
    from matplotlib.backend_bases import key_press_handler
except ImportError:
    key_press_handler = None
from matplotlib.backends import backend_qt4
backend_qt4.figureoptions = None  # disable toolbar button that doesn't work
pyplot.rc('font', family='sans-serif')
pyplot.rc('font', **{'sans-serif': 'Sans Serif, Arial, Helvetica, '
                     'Lucida Grande, Bitstream Vera Sans'})

from ufit.plotting import DataPlotter

uipath = path.dirname(__file__)

def loadUi(widget, uiname, subdir=''):
    uic.loadUi(path.join(uipath, subdir, uiname), widget)

def path_to_str(qstring):
    return unicode(qstring).encode(sys.getfilesystemencoding())

def str_to_path(string):
    return string.decode(sys.getfilesystemencoding())


class MPLCanvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
    def __init__(self, parent, width=10, height=6, dpi=72):
        fig = Figure(figsize=(width, height), dpi=dpi)
        fig.set_facecolor('white')
        self.main = parent
        self.axes = fig.add_subplot(111)
        self.plotter = DataPlotter(self, self.axes)
        # make tight_layout do the right thing
        self.axes.set_xlabel('x')
        self.axes.set_ylabel('y')
        self.axes.set_title('(data title)\n(info)', size='medium')
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()
        # actually get key events
        self.setFocusPolicy(Qt.StrongFocus)
        self.mpl_connect('key_press_event', self.key_press)

    def key_press(self, event):
        if key_press_handler:
            key_press_handler(event, self)

    def resizeEvent(self, event):
        # reimplemented to add tight_layout()
        w = event.size().width()
        h = event.size().height()
        dpival = float(self.figure.dpi)
        winch = w/dpival
        hinch = h/dpival
        self.figure.set_size_inches(winch, hinch)
        try:
            self.figure.tight_layout(pad=2)
        except Exception:
            pass
        self.draw()
        self.update()
        QWidget.resizeEvent(self, event)


class MPLToolbar(NavigationToolbar2QT):

    icon_name_map = {
        'home.png':         'home.png',
        'back.png':         'arrow-180.png',
        'forward.png':      'arrow.png',
        'move.png':         'arrow-move.png',
        'zoom_to_rect.png': 'selection-resize.png',
        'filesave.png':     'document-pdf.png',
        'printer.png':      'printer.png',
        'pyconsole.png':    'terminal--arrow.png',
    }

    toolitems = list(NavigationToolbar2QT.toolitems)
    del toolitems[7]  # subplot adjust
    toolitems.append(('Print', 'Print the figure', 'printer',
                      'print_callback'))
    toolitems.append(('Execute', 'Show Python console', 'pyconsole',
                      'exec_callback'))

    def _init_toolbar(self):
        NavigationToolbar2QT._init_toolbar(self)
        self.locLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

    def _icon(self, name):
        if name in self.icon_name_map:
            return QIcon(':/' + self.icon_name_map[name])
        return QIcon()

    def print_callback(self):
        self.emit(SIGNAL('printRequested'))

    def exec_callback(self):
        try:
            from ufit.gui.console import ConsoleWindow
        except ImportError:
            QMessageBox.information(self, 'ufit',
                'Please install IPython with qtconsole to activate this function.')
            return
        w = ConsoleWindow(self)
        w.ipython.executeCommand('from ufit.lab import *')
        w.ipython.pushVariables({
            'fig': self.canvas.figure,
            'ax': self.canvas.figure.gca(),
            'D': self.canvas.main.panels,
        })
        w.show()

    def save_figure(self, *args):
        filetypes = self.canvas.get_supported_filetypes_grouped()
        sorted_filetypes = sorted(filetypes.items())

        start = self.canvas.get_default_filename()
        filters = []
        for name, exts in sorted_filetypes:
            if 'eps' in exts or 'emf' in exts or 'jpg' in exts or \
                'pgf' in exts or 'raw' in exts:
                continue
            exts_list = " ".join(['*.%s' % ext for ext in exts])
            filter = '%s (%s)' % (name, exts_list)
            filters.append(filter)
        filters = ';;'.join(filters)
        fname = QFileDialog.getSaveFileName(self, 'Choose a filename to save to',
                                            start, filters)
        if fname:
            try:
                self.canvas.print_figure(unicode(fname))
            except Exception as e:
                QMessageBox.critical(self, 'Error saving file', str(e))


class SmallLineEdit(QLineEdit):
    def sizeHint(self):
        sz = QLineEdit.sizeHint(self)
        return QSize(sz.width()/1.5, sz.height())


class SettingGroup(object):
    def __init__(self, name):
        self.name = name
        self.settings = QSettings()

    def __enter__(self):
        self.settings.beginGroup(self.name)
        return self.settings

    def __exit__(self, *args):
        self.settings.endGroup()
        self.settings.sync()
