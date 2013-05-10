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
        self.dataformat.addItem('auto')
        for fmt in data_formats:
            self.dataformat.addItem(fmt)

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

    def on_dataformat_currentIndexChanged(self, i):
        self.loader.format = str(self.dataformat.currentText())

    @qtsig('')
    def on_numorHelp_clicked(self):
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
        bwin.set_template(str(self.datatemplate.text()))
        bwin.show()

    @qtsig('')
    def on_settemplate_clicked(self):
        previous = str(self.datatemplate.text())
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
        self.datatemplate.setText(dtempl)
        self.loader.template = dtempl
        try:
            cols, xguess, yguess, dyguess, mguess, nmon = \
                self.loader.guess_cols(numor)
        except Exception, e:
            #raise
            QMessageBox.information(self, 'Error',
                                    'Could not read column names: %s' % e)
            return
        self.xcol.clear()
        self.xcol.addItem('auto')
        self.xcol.setCurrentIndex(0)
        self.ycol.clear()
        self.ycol.addItem('auto')
        self.ycol.setCurrentIndex(0)
        self.dycol.clear()
        self.dycol.addItem('auto')
        self.dycol.addItem('sqrt(Y)')
        self.dycol.setCurrentIndex(0)
        self.moncol.clear()
        self.moncol.addItem('auto')
        self.moncol.addItem('none')
        self.moncol.setCurrentIndex(0)
        for i, name in enumerate(cols):
            self.xcol.addItem(name)
            self.ycol.addItem(name)
            self.dycol.addItem(name)
            self.moncol.addItem(name)
        self.monscale.setText(str(nmon or 1))
        self.numors.setText(str(numor))
        self.open_data()

    def open_data(self, final=False):
        prec = self.precision.value()
        xcol = str(self.xcol.currentText())
        ycol = str(self.ycol.currentText())
        dycol = str(self.dycol.currentText())
        mcol = str(self.moncol.currentText())
        if mcol == 'none':
            mcol = None
        if dycol == 'sqrt(Y)':
            dycol = None
        try:
            mscale = int(self.monscale.text())
        except Exception:
            QMessageBox.information(self, 'Error', 'Monitor scale must be integer.')
            return
        dtempl = self.datatemplate.text()
        self.loader.template = str(dtempl)
        numors = str(self.numors.text())
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
