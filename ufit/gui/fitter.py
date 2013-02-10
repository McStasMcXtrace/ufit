# -*- coding: utf-8 -*-
# ufit interactive fitting gui

from PyQt4.QtCore import SIGNAL, Qt
from PyQt4.QtGui import QApplication, QWidget, QMainWindow, QVBoxLayout, \
     QGridLayout, QFrame, QLabel, QDialogButtonBox, QCheckBox, QMessageBox, \
     QScrollArea

from ufit.gui.common import loadUi, MPLCanvas, MPLToolbar, SmallLineEdit


class Fitter(QWidget):

    def __init__(self, parent, canvas, standalone=False):
        QWidget.__init__(self, parent)
        self.canvas = canvas
        self._picking = False
        self.last_result = None
        self.model = None
        self.data = None
        self.param_controls = {}

        self.createUI(standalone)

    def createUI(self, standalone):
        loadUi(self, 'fitter.ui')

        if standalone:
            self.buttonBox.addButton(QDialogButtonBox.Close)
        self.buttonBox.addButton('Initial guess', QDialogButtonBox.HelpRole)
        self.buttonBox.addButton('Replot', QDialogButtonBox.ActionRole)
        self.buttonBox.addButton('Fit', QDialogButtonBox.ApplyRole)

    def initialize(self, model, data, fit=True):
        self.setWindowTitle('Fitting: data %s' % data.name)
        self._picking = False
        self.last_result = None
        self.model = model
        self.modelLabel.setText(model.get_description())
        self.data = data
        self.param_controls = {}
        self.create_param_controls()
        if fit:
            self.do_fit()
        else:
            model.plot(data, _axes=self.canvas.axes)
            model.plot_components(data, _axes=self.canvas.axes)

    def create_param_controls(self):
        self.param_frame.close()
        self.param_frame = QScrollArea(self)
        self.param_frame.setFrameShape(QFrame.NoFrame)
        self.param_frame.setFrameShadow(QFrame.Plain)
        self.layout().insertWidget(1, self.param_frame)
        layout = QGridLayout()
        for j, text in enumerate(('Param', 'Value', 'Error', 'Fix', 'Expr',
                                  'Data', 'Min', 'Max')):
            ctl = QLabel(text, self)
            ctl.setFont(self.statusLabel.font())
            layout.addWidget(ctl, 0, j)
        i = 1
        self.original_params = []
        for p in self.model.params:
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
            self.original_params.append(p.copy())
            #self.connect(e1, SIGNAL('textEdited(const QString&)'),
            #             self.do_plot)
            self.connect(e3, SIGNAL('clicked(bool)'), self.update_enables)
            self.connect(e4, SIGNAL('textEdited(const QString&)'),
                         self.update_enables)
            self.connect(e5, SIGNAL('textEdited(const QString&)'),
                         self.update_enables)
        layout.setRowStretch(i+1, 1)
        self.param_frame.setLayout(layout)
        self.update_enables()

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
                # disable "expr" as well when datapar is filled
                ctls[4].setEnabled(not bool(ctls[5].text()))
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

    def on_buttonBox_clicked(self, button):
        role = self.buttonBox.buttonRole(button)
        if role == QDialogButtonBox.RejectRole:
            self.emit(SIGNAL('closeRequest'))
        elif role == QDialogButtonBox.ApplyRole:
            self.do_fit()
        elif role == QDialogButtonBox.ActionRole:
            self.do_plot()
        elif role == QDialogButtonBox.HelpRole:
            self.do_pick()
        else:
            self.restore_original()

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
        self.update_enables()

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

    def on_canvas_pick(self, event):
        if not self._picking:
            return
        self.do_pick(event.xdata, event.ydata)

    def do_pick(self, *args):
        if not args:
            if not self._picking:
                self._pick_points = self.model.get_pick_points()
                self._pick_values = []
                self._picking = True
                self.statusLabel.setText('Guess: click on %s' % self._pick_points[0])
        else:
            self._pick_values.append((args[0], args[1]))
            if len(self._pick_values) == len(self._pick_points):
                self._picking = False
                self.statusLabel.setText('')
                self.model.apply_pick(self._pick_values)
                for p in self.model.params:
                    ctls = self.param_controls[p]
                    ctls[1].setText('%.4g' % p.value)
                self.do_plot()
            else:
                self.statusLabel.setText('Guess: click on %s' %
                                         self._pick_points[len(self._pick_values)])

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
        if self._picking:
            QMessageBox.information(self, 'Fitting',
                                    'Please finish the initial guess first.')
            return
        self.update_from_controls()
        self.statusLabel.setText('Working...')
        self.statusLabel.repaint()
        QApplication.processEvents()
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


class FitterMain(QMainWindow):
    def __init__(self, model, data, fit=True):
        QMainWindow.__init__(self)
        mainframe = QFrame(self)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.canvas = MPLCanvas(self)
        self.toolbar = MPLToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.fitter = Fitter(self, self.canvas, standalone=True)
        self.fitter.initialize(model, data, fit)
        self.canvas.mpl_connect('button_press_event', self.fitter.on_canvas_pick)
        self.connect(self.fitter, SIGNAL('closeRequest'), self.close)
        layout.addWidget(self.fitter)
        mainframe.setLayout(layout)
        self.setCentralWidget(mainframe)
        self.setWindowTitle(self.fitter.windowTitle())


def start(model, data, fit=True):
    app = QApplication([])
    win = FitterMain(model, data, fit)
    win.show()
    app.exec_()
    return win.fitter.last_result
