#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Common GUI elements."""

import sys
from os import path

from PyQt4 import uic
from PyQt4.QtCore import SIGNAL, QSize, QSettings, Qt, QRectF, QByteArray
from PyQt4.QtGui import QLineEdit, QSizePolicy, QWidget, QIcon, QFileDialog, \
    QMessageBox, QPrinter, QPrintDialog, QPrintPreviewWidget, QPainter, QDialog
from PyQt4.QtSvg import QSvgRenderer

import matplotlib.backends.qt_editor.figureoptions
from matplotlib.backends.backend_qt4agg import \
    FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT, FigureManagerQT
from matplotlib._pylab_helpers import Gcf
from matplotlib.colors import LogNorm
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

from ufit.gui import logger
from ufit.gui.session import session
from ufit.plotting import DataPlotter
from ufit.pycompat import BytesIO, text_type, PY2
from ufit.gui.ploteditor import figure_edit

# override figure editor with our extended version
matplotlib.backends.qt_editor.figureoptions.figure_edit = figure_edit

uipath = path.dirname(__file__)


def loadUi(widget, uiname, subdir='ui'):
    uic.loadUi(path.join(uipath, subdir, uiname), widget)


def path_to_str(qstring):
    if PY2:
        return qstring.encode(sys.getfilesystemencoding())
    return qstring


def str_to_path(string):
    if not isinstance(string, text_type):
        return string.decode(sys.getfilesystemencoding())
    return string


class MPLCanvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
    def __init__(self, parent, width=10, height=6, dpi=72, maincanvas=False):
        fig = Figure(figsize=(width, height), dpi=dpi)
        fig.set_facecolor('white')
        self.print_width = 0
        self.main = parent
        self.logz = False
        self.axes = fig.add_subplot(111)
        self.plotter = DataPlotter(self, self.axes)
        # make tight_layout do the right thing
        self.axes.set_xlabel('x')
        self.axes.set_ylabel('y')
        self.axes.set_title('(data title)\n(info)')
        FigureCanvas.__init__(self, fig)

        # create a figure manager so that we can use pylab commands on the
        # main viewport
        def make_active(event):
            Gcf.set_active(self.manager)
        self.manager = FigureManagerQT(self, 1)
        self.manager._cidgcf = self.mpl_connect('button_press_event', make_active)
        Gcf.set_active(self.manager)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()
        # actually get key events
        self.setFocusPolicy(Qt.StrongFocus)
        self.mpl_connect('key_press_event', self.key_press)
        # These will not do anything in standalone mode, but do not hurt.
        if maincanvas:
            self.connect(session, SIGNAL('propsRequested'),
                         self.on_session_propsRequested)
            self.connect(session, SIGNAL('propsUpdated'),
                         self.on_session_propsUpdated)

    def on_session_propsRequested(self):
        session.props.canvas_logz = self.logz

    def on_session_propsUpdated(self):
        if 'canvas_logz' in session.props:
            self.logz = session.props.canvas_logz
            self.emit(SIGNAL('logzChanged'))

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
        self.plotter.save_layout()
        self.draw()
        self.update()
        QWidget.resizeEvent(self, event)

    def print_(self):
        sio = BytesIO()
        self.print_figure(sio, format='svg')
        svg = QSvgRenderer(QByteArray(sio.getvalue()))
        sz = svg.defaultSize()
        aspect = sz.width()/float(sz.height())

        printer = QPrinter(QPrinter.HighResolution)
        printer.setOrientation(QPrinter.Landscape)

        dlg = QDialog(self)
        loadUi(dlg, 'printpreview.ui')
        dlg.width.setValue(self.print_width or 500)
        ppw = QPrintPreviewWidget(printer, dlg)
        dlg.layout().insertWidget(1, ppw)

        def render(printer):
            height = printer.height() * (dlg.width.value()/1000.)
            width = aspect * height
            painter = QPainter(printer)
            svg.render(painter, QRectF(0, 0, width, height))

        def sliderchanged(newval):
            ppw.updatePreview()

        self.connect(ppw, SIGNAL('paintRequested(QPrinter *)'), render)
        self.connect(dlg.width, SIGNAL('valueChanged(int)'), sliderchanged)
        if dlg.exec_() != QDialog.Accepted:
            return
        self.print_width = dlg.width.value()
        pdlg = QPrintDialog(printer, self)
        if pdlg.exec_() != QDialog.Accepted:
            return
        render(printer)

    def ufit_replot(self):
        self.emit(SIGNAL('replotRequest'))


class MPLToolbar(NavigationToolbar2QT):

    icon_name_map = {
        'home.png':         'magnifier-zoom-fit.png',
        'back.png':         'arrow-180.png',
        'forward.png':      'arrow.png',
        'move.png':         'arrow-move.png',
        'zoom_to_rect.png': 'selection-resize.png',
        'filesave.png':     'document-pdf.png',
        'printer.png':      'printer.png',
        'pyconsole.png':    'terminal--arrow.png',
        'log-x.png':        'log-x.png',
        'log-y.png':        'log-y.png',
        'log-z.png':        'log-z.png',
        'exwindow.png':    'chart--arrow.png',
    }

    toolitems = list(NavigationToolbar2QT.toolitems)
    del toolitems[7]  # subplot adjust
    toolitems.insert(0, ('Log x', 'Logarithmic X scale', 'log-x', 'logx_callback'))
    toolitems.insert(1, ('Log y', 'Logarithmic Y scale', 'log-y', 'logy_callback'))
    toolitems.insert(2, ('Log z', 'Logarithmic Z scale for images', 'log-z',
                         'logz_callback'))
    toolitems.insert(3, (None, None, None, None))
    toolitems.append(('Print', 'Print the figure', 'printer',
                      'print_callback'))
    toolitems.append(('Pop out', 'Show the figure in a separate window',
                      'exwindow', 'popout_callback'))
    toolitems.append(('Execute', 'Show Python console', 'pyconsole',
                      'exec_callback'))

    def _init_toolbar(self):
        NavigationToolbar2QT._init_toolbar(self)
        self.locLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._actions['logx_callback'].setCheckable(True)
        self._actions['logy_callback'].setCheckable(True)
        self._actions['logz_callback'].setCheckable(True)
        self.connect(self.canvas, SIGNAL('logzChanged'),
                     self.on_canvas_logzChanged)

    def _icon(self, name):
        if name in self.icon_name_map:
            return QIcon(':/' + self.icon_name_map[name])
        return QIcon()

    def home(self):
        # always unzoom completely
        self._views.clear()
        self._positions.clear()
        self.canvas.figure.gca().autoscale()
        self.canvas.draw()
        return NavigationToolbar2QT.home(self)

    def logx_callback(self):
        ax = self.canvas.figure.gca()
        if ax.get_xscale() == 'linear':
            ax.set_xscale('symlog')
            self._actions['logx_callback'].setChecked(True)
        else:
            ax.set_xscale('linear')
            self._actions['logx_callback'].setChecked(False)
        self.canvas.draw()

    def logy_callback(self):
        ax = self.canvas.figure.gca()
        if ax.get_yscale() == 'linear':
            ax.set_yscale('symlog')
            self._actions['logy_callback'].setChecked(True)
        else:
            ax.set_yscale('linear')
            self._actions['logy_callback'].setChecked(False)
        self.canvas.draw()

    def logz_callback(self):
        ax = self.canvas.figure.gca()
        self.canvas.logz = not self.canvas.logz
        session.set_dirty()
        self._actions['logz_callback'].setChecked(self.canvas.logz)
        for im in ax.get_images():
            if self.canvas.logz:
                im.set_norm(LogNorm())
            else:
                im.set_norm(None)
        self.canvas.draw()

    def on_canvas_logzChanged(self):
        self._actions['logz_callback'].setChecked(self.canvas.logz)

    def print_callback(self):
        self.canvas.print_()

    def popout_callback(self):
        self.emit(SIGNAL('popoutRequested'))

    def exec_callback(self):
        try:
            from ufit.gui.console import ConsoleWindow
        except ImportError:
            logger.exception('Qt console window cannot be opened without '
                             'IPython; import error was:')
            QMessageBox.information(self, 'ufit',
                                    'Please install IPython with qtconsole to '
                                    'activate this function.')
            return
        w = ConsoleWindow(self)
        w.ipython.executeCommand('from ufit.lab import *')
        w.ipython.pushVariables({
            'fig': self.canvas.figure,
            'ax': self.canvas.figure.gca(),
            'D': [item for group in session.groups for item in group.items],
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
                self.canvas.print_figure(text_type(fname))
            except Exception as e:
                logger.exception('Error saving file')
                QMessageBox.critical(self, 'Error saving file', str(e))


class SmallLineEdit(QLineEdit):
    def sizeHint(self):
        sz = QLineEdit.sizeHint(self)
        return QSize(sz.width()/1.5, sz.height())


class SettingGroup(object):
    def __init__(self, name):
        self.name = name
        self.settings = QSettings('ufit', 'gui')

    def __enter__(self):
        self.settings.beginGroup(self.name)
        return self.settings

    def __exit__(self, *args):
        self.settings.endGroup()
        self.settings.sync()
