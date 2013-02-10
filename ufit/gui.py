# -*- coding: utf-8 -*-
# ufit interactive fitting gui

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from matplotlib.backends.backend_qt4agg import \
     FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT

from matplotlib.figure import Figure



class Canvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
    def __init__(self, parent=None, width=7, height=6, dpi=72):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()


class SmallLineEdit(QLineEdit):
    def sizeHint(self):
        sz = QLineEdit.sizeHint(self)
        return QSize(sz.width()/1.5, sz.height())


class FitMainWindow(QMainWindow):

    def __init__(self):
        QMainWindow.__init__(self)
        self.last_result = None

        central = QFrame(self)
        layout = QVBoxLayout()
        self.canvas = Canvas(self)

        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        self.param_frame = QFrame(self)
        layout.addWidget(self.param_frame)

        self.statusLabel = QLabel(self)
        fnt = self.statusLabel.font()
        fnt.setBold(True)
        self.statusLabel.setFont(fnt)
        layout.addWidget(self.statusLabel)

        self.buttonBox = QDialogButtonBox(self,)
        self.buttonBox.addButton(QDialogButtonBox.RestoreDefaults)
        self.buttonBox.addButton(QDialogButtonBox.Close)
        self.buttonBox.addButton('Replot', QDialogButtonBox.ActionRole)
        self.buttonBox.addButton('Fit', QDialogButtonBox.ApplyRole)
        layout.addWidget(self.buttonBox)
        self.connect(self.buttonBox, SIGNAL('clicked(QAbstractButton*)'),
                     self.on_buttonBox_clicked)

        central.setLayout(layout)
        self.setCentralWidget(central)

    def on_buttonBox_clicked(self, button):
        role = self.buttonBox.buttonRole(button)
        if role == QDialogButtonBox.RejectRole:
            self.close()
        elif role == QDialogButtonBox.ApplyRole:
            self.do_fit()
        elif role == QDialogButtonBox.ActionRole:
            self.do_plot()
        else:
            self.restore_original()

    def initialize(self, model, data, fit=True):
        self.setWindowTitle('Fitting: %s' % data.name)
        self.model = model
        self.data = data
        self.param_controls = {}
        layout = QGridLayout()
        for j, text in enumerate(('Param', 'Value', 'Error', 'Fix', 'Expr',
                                  'Data', 'Min', 'Max')):
            ctl = QLabel(text, self)
            ctl.setFont(self.statusLabel.font())
            layout.addWidget(ctl, 0, j)
        i = 1
        self.original_params = []
        for p in model.params:
            e0 = QLabel(p.name, self)
            e1 = SmallLineEdit('%.4g' % p.value, self)
            e2 = QLabel('', self)
            e3 = QCheckBox(self)
            e4 = SmallLineEdit(p.expr or '', self)
            e5 = SmallLineEdit(p.datapar or '', self)
            e6 = SmallLineEdit(p.pmin is not None and '%.4g' % p.pmin or '', self)
            e7 = SmallLineEdit(p.pmax is not None and '%.4g' % p.pmax or '', self)
            ctls = self.param_controls[p] = (e0, e1, e2, e3, e4, e5, e6, e7)
            for j, ctl in enumerate(ctls):
                layout.addWidget(ctl, i, j)
            i += 1
            self.original_params.append(p.copy(p.name))
            #self.connect(e1, SIGNAL('textEdited(const QString&)'),
            #             self.do_plot)
            self.connect(e3, SIGNAL('clicked(bool)'), self.update_enables)
            self.connect(e4, SIGNAL('textEdited(const QString&)'),
                         self.update_enables)
            self.connect(e5, SIGNAL('textEdited(const QString&)'),
                         self.update_enables)
        self.update_enables()
        self.param_frame.setLayout(layout)
        if fit:
            self.do_fit()
        else:
            model.plot(data, _axes=self.canvas.axes)
            model.plot_components(data, _axes=self.canvas.axes)

    def update_enables(self, *ignored):
        for p, ctls in self.param_controls.iteritems():
            # if there is an expr or datapar...
            if ctls[4].text() or ctls[5].text():
                # disable value and minmax, check "fixed" and disable "fixed"
                ctls[1].setEnabled(False)
                ctls[3].setCheckState(Qt.PartiallyChecked)  # implicitly fixed
                ctls[3].setEnabled(False)
                ctls[6].setEnabled(False)
                ctls[7].setEnabled(False)
            # else, if "fixed" is checked...
            elif ctls[3].checkState() == Qt.Checked:
                # enable value, but disable expr and datapar plus minmax
                ctls[1].setEnabled(True)
                ctls[4].setEnabled(False)
                ctls[5].setEnabled(False)
                ctls[6].setEnabled(False)
                ctls[7].setEnabled(False)
            # else: not fixed, no expr or datapar
            else:
                # enable everything
                ctls[1].setEnabled(True)
                ctls[3].setEnabled(True)
                ctls[3].setCheckState(Qt.Unchecked)
                ctls[3].setTristate(False)
                ctls[4].setEnabled(True)
                ctls[5].setEnabled(True)
                ctls[6].setEnabled(True)
                ctls[7].setEnabled(True)

    def update_from_controls(self):
        for p, ctls in self.param_controls.iteritems():
            _, val, _, fx, expr, datap, pmin, pmax = ctls
            p.value = float(val.text()) if val.text() else 0
            if fx.checkState() == Qt.Checked:
                p.expr = str(val.text())
            else:
                p.expr = str(expr.text())
            p.datapar = str(datap.text())
            p.pmin = float(pmin.text()) if pmin.text() else None
            p.pmax = float(pmax.text()) if pmax.text() else None

    def restore_original(self):
        for p, p0 in zip(self.model.params, self.original_params):
            ctls = self.param_controls[p]
            ctls[1].setText('%.4g' % p0.value)
            ctls[3].setChecked(False)
            ctls[4].setText(p0.expr or '')
            ctls[5].setText(p0.datapar or '')
            ctls[6].setText(p0.pmin is not None and '%.4g' % p0.pmin or '')
            ctls[7].setText(p0.pmax is not None and '%.4g' % p0.pmax or '')
        self.do_plot()

    def do_plot(self, *ignored):
        self.update_from_controls()
        xlims = self.canvas.axes.get_xlim()
        ylims = self.canvas.axes.get_ylim()
        self.canvas.axes.clear()
        self.model.plot(self.data, _axes=self.canvas.axes)
        self.model.plot_components(self.data, _axes=self.canvas.axes)
        if xlims != (0, 1):
            self.canvas.axes.set_xlim(*xlims)
            self.canvas.axes.set_ylim(*ylims)
        self.canvas.draw()

    def do_fit(self):
        self.update_from_controls()
        res = self.model.fit(self.data)
        self.statusLabel.setText((res.success and 'Converged. ' or 'Failed. ')
                                 + res.message +
                                 ' Reduced chi^2 = %.3g.' % res.chisqr)
        #res.printout()
        xlims = self.canvas.axes.get_xlim()
        ylims = self.canvas.axes.get_ylim()
        self.canvas.axes.clear()
        res.plot(_axes=self.canvas.axes)
        res.plot_components(_axes=self.canvas.axes)
        if xlims != (0, 1):
            self.canvas.axes.set_xlim(*xlims)
            self.canvas.axes.set_ylim(*ylims)
        self.canvas.draw()

        for p in res.params:
            self.param_controls[p][1].setText('%.4g' % p.value)
            self.param_controls[p][2].setText(u'± %.4g' % p.error)

        self.last_result = res


def start(model, data, fit=True):
    app = QApplication([])
    win = FitMainWindow()
    win.initialize(model, data, fit)
    win.show()
    app.exec_()
    return win.last_result
