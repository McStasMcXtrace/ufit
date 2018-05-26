#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data loader panel."""

from os import path

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL, Qt
from PyQt4.QtGui import QWidget, QFileDialog, QDialogButtonBox, QMessageBox, \
    QMainWindow, QSplitter, QApplication

from ufit.data import data_formats, Loader, ImageData
from ufit.utils import extract_template
from ufit.gui import logger
from ufit.gui.common import loadUi, path_to_str, str_to_path, \
    MPLCanvas, MPLToolbar
from ufit.gui.browse import BrowseWindow
from ufit.gui.common import SettingGroup
from ufit.gui.session import session


class DataLoader(QWidget):

    def __init__(self, parent, plotter, standalone=False):
        QWidget.__init__(self, parent)
        self.logger = logger.getChild('loader')
        self.plotter = plotter
        self.last_data = []
        self.loader = Loader()
        self.createUI(standalone)

        self.sgroup = SettingGroup('main')

        # These will not do anything in standalone mode, but do not hurt.
        self.connect(session, SIGNAL('propsRequested'),
                     self.on_session_propsRequested)
        self.connect(session, SIGNAL('propsUpdated'),
                     self.on_session_propsUpdated)
        self.connect(session, SIGNAL('itemsUpdated'),
                     self.on_session_itemsUpdated)
        self.connect(session, SIGNAL('groupAdded'),
                     self.on_session_itemsUpdated)

        with self.sgroup as settings:
            data_template_path = settings.value('last_data_template', '')
            if data_template_path:
                self.templateEdit.setText(data_template_path)
                self.set_template(data_template_path, 0, silent=True)

    def createUI(self, standalone):
        loadUi(self, 'dataloader.ui')
        self.dataformatBox.addItem('auto')
        for fmt in sorted(data_formats):
            self.dataformatBox.addItem(fmt)

        self.buttonBox.addButton(QDialogButtonBox.Open)
        self.buttonBox.addButton('Preview', QDialogButtonBox.NoRole)

    def on_session_propsRequested(self):
        session.props.template = self.templateEdit.text()

    def on_session_propsUpdated(self):
        if 'template' in session.props:
            self.templateEdit.setText(session.props.template)

    def on_session_itemsUpdated(self):
        # list of groups may have changed
        self.groupBox.clear()
        for group in session.groups:
            self.groupBox.addItem(group.name)

    def on_buttonBox_clicked(self, button):
        role = self.buttonBox.buttonRole(button)
        if role == QDialogButtonBox.RejectRole:
            self.emit(SIGNAL('closeRequest'))
        elif role == QDialogButtonBox.NoRole:  # "preview"
            self.open_data()
        else:  # "open"
            self.open_data(final=True)

    def on_dataformatBox_currentIndexChanged(self, i):
        self.loader.format = str(self.dataformatBox.currentText())

    @qtsig('')
    def on_numorHelpBtn_clicked(self):
        QMessageBox.information(self, 'Numor Help', '''\
The numor string contains file numbers, with the following operators:

, loads multiple files
- loads multiple sequential files
+ merges multiple files
> merges multiple sequential files

For example:

* 10-15,23  loads files 10 through 15 and 23 in 7 separate datasets.
* 10+11,23+24 loads two datasets consisting of files 10 and 11 merged \
into one set, as well as files 23 and 24.
* 10>15+23 merges files 10 through 15 and 23 into one single dataset.
* 10,11,12+13,14 loads four sets.
''')

    def open_browser(self, directory):
        bwin = BrowseWindow(self)
        bwin.show()
        QApplication.processEvents()
        try:
            bwin.set_directory(directory)
        except OSError:
            pass
        bwin.activateWindow()

    @qtsig('')
    def on_browseBtn_clicked(self):
        templ = path_to_str(self.templateEdit.text())
        self.open_browser(path.dirname(templ))

    @qtsig('')
    def on_settemplateBtn_clicked(self):
        previous = self.templateEdit.text()
        if previous:
            startdir = path.dirname(previous)
        else:
            startdir = '.'
        fn = path_to_str(QFileDialog.getOpenFileName(
            self, 'Choose a file', startdir, 'All files (*)'))
        if not fn:
            return
        dtempl, numor = extract_template(fn)
        self.set_template(dtempl, numor)

    def set_template(self, dtempl, numor, silent=True):
        self.templateEdit.setText(str_to_path(dtempl))
        with self.sgroup as settings:
            settings.setValue('last_data_template', dtempl)
        self.loader.template = dtempl
        try:
            cols, xguess, yguess, dyguess, mguess, nmon = \
                self.loader.guess_cols(numor)
        except Exception as e:
            if not silent:
                self.logger.exception('Could not read column names')
                QMessageBox.information(self, 'Error',
                                        'Could not read column names: %s' % e)
            return
        self.xcolBox.clear()
        self.xcolBox.addItem('auto')
        self.xcolBox.setCurrentIndex(0)
        self.ycolBox.clear()
        self.ycolBox.addItem('auto')
        self.ycolBox.setCurrentIndex(0)
        self.dycolBox.clear()
        self.dycolBox.addItem('auto')
        self.dycolBox.addItem('sqrt(Y)')
        self.dycolBox.setCurrentIndex(0)
        self.moncolBox.clear()
        self.moncolBox.addItem('auto')
        self.moncolBox.addItem('none')
        self.moncolBox.setCurrentIndex(0)
        for i, name in enumerate(cols):
            self.xcolBox.addItem(name)
            self.ycolBox.addItem(name)
            self.dycolBox.addItem(name)
            self.moncolBox.addItem(name)
        self.monscaleEdit.setText(str(nmon or 1))
        self.numorsEdit.setText(str(numor))
        self.open_data()

    def open_data(self, final=False):
        try:
            prec = float(self.precisionEdit.text())
        except ValueError:
            QMessageBox.information(self, 'Error', 'Enter a valid precision.')
            return
        floatmerge = self.rbFloatMerge.isChecked()
        xcol = str(self.xcolBox.currentText())
        ycol = str(self.ycolBox.currentText())
        dycol = str(self.dycolBox.currentText())
        mcol = str(self.moncolBox.currentText())
        if mcol == 'none':
            mcol = None
        if dycol == 'sqrt(Y)':
            dycol = None
        try:
            mscale = int(self.monscaleEdit.text())
        except Exception:
            QMessageBox.information(
                self, 'Error', 'Monitor scale must be integer.')
            return
        dtempl = path_to_str(self.templateEdit.text())
        self.loader.template = dtempl
        numors = str(self.numorsEdit.text())
        try:
            datas = self.loader.load_numors(
                numors, prec, xcol, ycol, dycol, mcol, mscale, floatmerge)
        except Exception as e:
            self.logger.exception('Error while loading data file')
            QMessageBox.information(self, 'Error', str(e))
            return
        self.last_data = datas
        if final:
            self.emit(SIGNAL('newDatas'), datas, self.groupBox.currentText())
            self.emit(SIGNAL('closeRequest'))
        else:
            self.plot()

    def initialize(self):
        pass

    def plot(self, limits=True, canvas=None):
        self.plotter.reset()
        xlabels = set()
        ylabels = set()
        titles = set()
        for data in self.last_data:
            xlabels.add(data.xaxis)
            ylabels.add(data.yaxis)
            titles.add(data.title)
            if isinstance(data, ImageData):  # XXX this plots only one
                self.plotter.plot_image(data, multi=True)
                break
            else:
                self.plotter.plot_data(data, multi=True)
        self.plotter.plot_finish(', '.join(xlabels), ', '.join(ylabels),
                                 ', '.join(titles))
        self.plotter.draw()


class DataLoaderMain(QMainWindow):
    def __init__(self, data):
        QMainWindow.__init__(self)
        layout = QSplitter(Qt.Vertical, self)
        self.canvas = MPLCanvas(self)
        self.toolbar = MPLToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.dloader = DataLoader(self, self.canvas.plotter, standalone=True)
        self.dloader.groupBox.hide()
        self.dloader.groupBoxLbl.hide()
        self.dloader.groupBoxDesc.hide()
        self.dloader.initialize()
        self.connect(self.dloader, SIGNAL('closeRequest'), self.close)
        layout.addWidget(self.dloader)
        self.setCentralWidget(layout)
        self.setWindowTitle('Data loading')


def start():
    app = QApplication([])
    win = DataLoaderMain()
    win.show()
    app.exec_()
    return win.dloader.last_data
