#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data loader panel."""

from os import path

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL, Qt
from PyQt4.QtGui import QWidget, QFileDialog, QDialogButtonBox, QMessageBox, \
     QMainWindow, QSplitter, QApplication

from ufit.data import data_formats, Loader
from ufit.utils import extract_template
from ufit.gui.common import loadUi, MPLCanvas, MPLToolbar
from ufit.gui.browse import BrowseWindow


class DataLoader(QWidget):

    def __init__(self, parent, plotter, standalone=False):
        QWidget.__init__(self, parent)
        self.plotter = plotter
        self.last_data = []
        self.loader = Loader()
        self.createUI(standalone)

    def createUI(self, standalone):
        loadUi(self, 'dataloader.ui')
        self.dataformatBox.addItem('auto')
        for fmt in data_formats:
            self.dataformatBox.addItem(fmt)

        self.buttonBox.addButton(QDialogButtonBox.Open)
        self.buttonBox.addButton('Preview', QDialogButtonBox.NoRole)

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

    @qtsig('')
    def on_browseBtn_clicked(self):
        bwin = BrowseWindow(self)
        bwin.set_template(str(self.templateEdit.text()))
        bwin.show()

    @qtsig('')
    def on_settemplateBtn_clicked(self):
        previous = str(self.templateEdit.text())
        if previous:
            startdir = path.dirname(previous)
        else:
            startdir = '.'
        fn = str(QFileDialog.getOpenFileName(self, 'Choose a file', startdir,
                                             'All files (*)'))
        if not fn:
            return
        self.set_template(fn)

    def set_template(self, fn):
        dtempl, numor = extract_template(fn)
        self.templateEdit.setText(dtempl)
        self.loader.template = dtempl
        try:
            cols, xguess, yguess, dyguess, mguess, nmon = \
                self.loader.guess_cols(numor)
        except Exception, e:
            #raise
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
            QMessageBox.information(self, 'Error', 'Monitor scale must be integer.')
            return
        dtempl = self.templateEdit.text()
        self.loader.template = str(dtempl)
        numors = str(self.numorsEdit.text())
        try:
            datas = self.loader.load_numors(numors, prec,
                                            xcol, ycol, dycol, mcol, mscale)
        except Exception, e:
            QMessageBox.information(self, 'Error', 'Could not read data: %s' % e)
            return
        if final:
            self.last_data = datas
            for data in datas[:-1]:
                self.emit(SIGNAL('newData'), data, False)
            self.emit(SIGNAL('newData'), datas[-1])
            self.emit(SIGNAL('closeRequest'))
        else:
            self.plotter.reset()
            for data in datas:
                self.plotter.plot_data(data, multi=True)
            self.plotter.plot_finish()
            self.plotter.draw()

    def initialize(self):
        pass


class DataLoaderMain(QMainWindow):
    def __init__(self, data):
        QMainWindow.__init__(self)
        layout = QSplitter(Qt.Vertical, self)
        self.canvas = MPLCanvas(self)
        self.toolbar = MPLToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.dloader = DataLoader(self, self.canvas.plotter, standalone=True)
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
