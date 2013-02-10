# ufit full GUI window

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QMainWindow, QVBoxLayout, QHBoxLayout, \
     QFrame, QTabWidget, QApplication

from ufit.gui.common import MPLCanvas, MPLToolbar
from ufit.gui.dataloader import DataLoader
from ufit.gui.modelbuilder import ModelBuilder
from ufit.gui.fitter import Fitter


class UFitMain(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        mainframe = QFrame(self)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout2 = QVBoxLayout()
        layout2.setContentsMargins(0, 0, 0, 0)
        self.canvas = MPLCanvas(self)
        self.toolbar = MPLToolbar(self.canvas, self)
        layout2.addWidget(self.toolbar)
        layout2.addWidget(self.canvas)
        layout.addLayout(layout2)

        self.tabber = QTabWidget(self)
        self.tabber.setTabPosition(QTabWidget.South)
        layout.addWidget(self.tabber)

        self.dloader = DataLoader(self, self.canvas)
        self.connect(self.dloader, SIGNAL('newData'), self.handle_new_data)
        self.tabber.addTab(self.dloader, 'Data')

        self.mbuilder = ModelBuilder(self, self.canvas)
        self.connect(self.mbuilder, SIGNAL('newModel'), self.handle_new_model)
        self.tabber.addTab(self.mbuilder, 'Model')

        self.fitter = Fitter(self, self.canvas)
        self.canvas.mpl_connect('button_press_event', self.fitter.on_canvas_pick)
        self.tabber.addTab(self.fitter, 'Fit')

        mainframe.setLayout(layout)
        self.setCentralWidget(mainframe)
        self.setWindowTitle('ufit')

    def handle_new_data(self, data):
        self.mbuilder.initialize(data)
        self.tabber.setCurrentIndex(1)

    def handle_new_model(self, model):
        self.fitter.initialize(model, self.dloader.last_data, fit=False)
        self.tabber.setCurrentIndex(2)


def main(args):
    app = QApplication([])
    win = UFitMain()

    if args:
        datafile = args[0]
        win.dloader.set_template(datafile)

    win.show()
    app.exec_()
