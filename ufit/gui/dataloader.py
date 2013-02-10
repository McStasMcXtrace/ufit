# -*- coding: utf-8 -*-
# ufit interactive fitting gui

import re
from os import path

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL, Qt
from PyQt4.QtGui import QWidget, QFileDialog, QDialogButtonBox, QMessageBox, \
     QMainWindow, QSplitter, QApplication

from ufit.data import data_formats, Loader
from ufit.gui.common import loadUi, MPLCanvas, MPLToolbar

numor_re = re.compile(r'\d+')

class DataLoader(QWidget):

    def __init__(self, parent, canvas, standalone=False):
        QWidget.__init__(self, parent)
        self.canvas = canvas
        self.last_data = None
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
        elif role == QDialogButtonBox.NoRole:
            self.open_data()
        else:  # "open"
            self.open_data(final=True)

    def on_dataformat_currentIndexChanged(self, i):
        self.loader.format = str(self.dataformat.currentText())

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
        bn = path.basename(fn)
        dn = path.dirname(fn)
        m = list(numor_re.finditer(bn))
        if not m:
            QMessageBox.information(self, 'Error', 'No number in file name?!')
            return
        b, e = m[-1].span()
        dtempl = path.join(dn, bn[:b] + '%%0%dd' % (e-b) + bn[e:])
        numor = int(m[-1].group())
        self.datatemplate.setText(dtempl)
        self.loader.template = dtempl
        try:
            cols, xguess, yguess, mguess = self.loader.guess_cols(numor)
        except Exception, e:
            QMessageBox.information(self, 'Error',
                                    'Could not read column names: %s' % e)
            return
        self.xcol.clear()
        self.ycol.clear()
        self.moncol.clear()
        for i, name in enumerate(cols):
            self.xcol.addItem(name)
            self.ycol.addItem(name)
            self.moncol.addItem(name)
            if name == xguess:
                self.xcol.setCurrentIndex(i)
            if name == yguess:
                self.ycol.setCurrentIndex(i)
            if name == mguess:
                self.moncol.setCurrentIndex(i)
        self.numors.setText(str(numor))
        self.open_data()

    def open_data(self, final=False):
        prec = self.precision.value()
        xcol = str(self.xcol.currentText())
        ycol = str(self.ycol.currentText())
        mcol = str(self.moncol.currentText())
        try:
            mscale = int(self.monscale.text())
        except Exception:
            QMessageBox.information(self, 'Error', 'Monitor scale must be integer.')
            return
        try:
            numors = map(int, str(self.numors.text()).split(','))
        except Exception:
            QMessageBox.information(self, 'Error',
                                    'Numor list must be n1,n2,n3 etc.')
            return
        try:
            datas = [self.loader.load(numor, xcol, ycol, mcol, mscale)
                     for numor in numors]
        except Exception, e:
            QMessageBox.information(self, 'Error', 'Could not read data: %s' % e)
            return
        if len(datas) == 1:
            data = datas[0]
        else:
            data = datas[0].merge(prec, *datas[1:])
        if final:
            self.last_data = data
            self.emit(SIGNAL('newData'), data)
            self.emit(SIGNAL('closeRequest'))
        else:
            self.canvas.axes.clear()
            data.plot(_axes=self.canvas.axes)
            self.canvas.draw()

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
        self.dloader = DataLoader(self, self.canvas, standalone=True)
        self.dloader.initialize()
        self.connect(self.dloader, SIGNAL('closeRequest'), self.close)
        layout.addWidget(self.fitter)
        self.setCentralWidget(layout)
        self.setWindowTitle(self.fitter.windowTitle())


def start():
    app = QApplication([])
    win = DataLoaderMain()
    win.show()
    app.exec_()
    return win.dloader.last_data