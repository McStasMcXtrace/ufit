# ufit common GUI elements

from os import path

from PyQt4 import uic
from PyQt4.QtCore import QSize
from PyQt4.QtGui import QLineEdit, QSizePolicy, QWidget

from matplotlib.backends.backend_qt4agg import \
     FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT

from matplotlib.figure import Figure

uipath = path.dirname(__file__)

def loadUi(widget, uiname, subdir=''):
    uic.loadUi(path.join(uipath, subdir, uiname), widget)


class MPLCanvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
    def __init__(self, parent=None, width=7, height=6, dpi=72):
        fig = Figure(figsize=(width, height), dpi=dpi)
        fig.set_facecolor('white')
        self.axes = fig.add_subplot(111)
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()

    def resizeEvent(self, event):
        # reimplemented to add tight_layout()
        w = event.size().width()
        h = event.size().height()
        dpival = float(self.figure.dpi)
        winch = w/dpival
        hinch = h/dpival
        self.figure.set_size_inches(winch, hinch)
#        self.figure.tight_layout()
        self.draw()
        self.update()
        QWidget.resizeEvent(self, event)

MPLToolbar = NavigationToolbar2QT


class SmallLineEdit(QLineEdit):
    def sizeHint(self):
        sz = QLineEdit.sizeHint(self)
        return QSize(sz.width()/1.5, sz.height())
