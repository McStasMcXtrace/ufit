# ufit common GUI elements

from PyQt4.QtCore import QSize
from PyQt4.QtGui import QLineEdit, QSizePolicy

from matplotlib.backends.backend_qt4agg import \
     FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT

from matplotlib.figure import Figure

class MPLCanvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
    def __init__(self, parent=None, width=7, height=6, dpi=72):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()

MPLToolbar = NavigationToolbar2QT


class SmallLineEdit(QLineEdit):
    def sizeHint(self):
        sz = QLineEdit.sizeHint(self)
        return QSize(sz.width()/1.5, sz.height())
