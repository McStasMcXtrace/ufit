#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data fitter panel."""

from PyQt4.QtCore import SIGNAL, Qt
from PyQt4.QtGui import QApplication, QWidget, QMainWindow, QGridLayout, \
    QFrame, QLabel, QDialogButtonBox, QCheckBox, QMessageBox, QSplitter, \
    QComboBox, QKeySequence, QIcon

from ufit.gui import logger
from ufit.gui.common import loadUi, MPLCanvas, MPLToolbar, SmallLineEdit
from ufit.gui.session import session
from ufit.pycompat import iteritems, number_types


def is_float(x):
    try:
        float(x)
        return True
    except ValueError:
        return False


class Fitter(QWidget):

    def __init__(self, parent, standalone=False, fit_kws={}):
        QWidget.__init__(self, parent)
        self.item = getattr(parent, 'item', None)
        self.logger = logger.getChild('fitter')
        self.picking = None
        self.last_result = None
        self.model = None
        self.data = None
        self.param_controls = {}
        self.fit_kws = fit_kws

        self.standalone = standalone
        self.createUI(standalone)

    def createUI(self, standalone):
        loadUi(self, 'fitter.ui')

        if standalone:
            self.buttonBox.addButton(QDialogButtonBox.Close)
        self.buttonBox.addButton('Initial guess', QDialogButtonBox.HelpRole)
        self.buttonBox.addButton('Save params', QDialogButtonBox.ResetRole)
        self.buttonBox.addButton('Restore saved', QDialogButtonBox.ResetRole)
        self.buttonBox.addButton('Replot', QDialogButtonBox.ActionRole)
        fitbtn = self.buttonBox.addButton('Fit', QDialogButtonBox.ApplyRole)
        fitbtn.setShortcut(QKeySequence('Ctrl+F'))
        fitbtn.setIcon(QIcon.fromTheme('dialog-ok'))

    def initialize(self, model, data, fit=True, keep_old=True):
        self.picking = None
        self.last_result = None

        old_model = self.model
        self.modelLabel.setText(model.get_description())
        self.data = data
        self.model = model

        self.param_controls = {}
        self.create_param_controls()

        # try to transfer values of old parameters to new
        if keep_old and old_model is not None:
            oldp_dict = dict((p.name, p) for p in old_model.params)
            self.restore_from_params(oldp_dict)

        self.connect(session, SIGNAL('modelFitted'), self.on_modelFitted)

        if self.standalone:
            if fit:
                self.do_fit()
            else:
                self.emit(SIGNAL('replotRequest'), None)

    def create_param_controls(self):
        self.param_controls = {}
        self.param_frame = QFrame(self)
        layout = QGridLayout()
        for j, text in enumerate(('Param', 'Value', 'Error', 'Fix', 'Expr',
                                  'Min', 'Max', 'Delta')):
            ctl = QLabel(text, self)
            ctl.setFont(self.statusLabel.font())
            layout.addWidget(ctl, 0, j)
        i = 1
        self.original_params = {}
        combo_items = [''] + [par.name for par in self.model.params] + \
            ['data.' + m for m in sorted(self.data.meta)
             if isinstance(self.data.meta[m], number_types)]
        for p in self.model.params:
            e0 = QLabel(p.name, self)
            e1 = SmallLineEdit('%.5g' % p.value, self)
            e2 = QLabel(u'± %.5g' % p.error, self)
            e3 = QCheckBox(self)
            e4 = QComboBox(self)
            e4.setEditable(True)
            e4.addItems(combo_items)
            if p.expr and is_float(p.expr):
                e1.setText(p.expr)
                e3.setChecked(True)
                e4.lineEdit().setText('')
            else:
                e4.lineEdit().setText(p.expr or '')
            e5 = SmallLineEdit(p.pmin is not None and '%.5g' % p.pmin or '', self)
            e6 = SmallLineEdit(p.pmax is not None and '%.5g' % p.pmax or '', self)
            e7 = SmallLineEdit(p.delta and '%.5g' % p.delta or '', self)
            ctls = self.param_controls[p] = (e0, e1, e2, e3, e4, e5, e6, e7)
            for j, ctl in enumerate(ctls):
                layout.addWidget(ctl, i, j)
            i += 1
            self.original_params[p.name] = p.copy()
            self.connect(e1, SIGNAL('returnPressed()'), self.do_plot)
            self.connect(e4.lineEdit(), SIGNAL('returnPressed()'), self.do_plot)
            self.connect(e5, SIGNAL('returnPressed()'), self.do_plot)
            self.connect(e6, SIGNAL('returnPressed()'), self.do_plot)
            self.connect(e3, SIGNAL('clicked(bool)'), self.update_enables)
            self.connect(e4, SIGNAL('editTextChanged(const QString&)'),
                         self.update_enables)
        layout.setRowStretch(i+1, 1)
        self.param_frame.setLayout(layout)
        self.param_scroll.setWidget(self.param_frame)
        self.update_enables()

    def update_enables(self, *ignored):
        for p, ctls in iteritems(self.param_controls):
            # if there is an expr...
            if ctls[4].currentText():
                # disable value and minmax, check "fixed" and disable "fixed"
                ctls[1].setEnabled(False)
                ctls[3].setCheckState(Qt.PartiallyChecked)  # implicitly fixed
                ctls[3].setEnabled(False)
                ctls[5].setEnabled(False)
                ctls[6].setEnabled(False)
                ctls[7].setEnabled(False)
            # else, if "fixed" is checked...
            elif ctls[3].checkState() == Qt.Checked:
                # enable value, but disable expr and minmax
                ctls[1].setEnabled(True)
                ctls[4].setEnabled(False)
                ctls[5].setEnabled(False)
                ctls[6].setEnabled(False)
                ctls[7].setEnabled(False)
            # else: not fixed, no expr
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
            if button.text() == 'Save params':
                self.save_original_params()
                self.statusLabel.setText('Current parameter values saved.')
            else:
                self.restore_from_params(self.original_params)
                self.statusLabel.setText('Saved parameter values restored.')

    def update_from_controls(self):
        for p, ctls in iteritems(self.param_controls):
            _, val, _, fx, expr, pmin, pmax, delta = ctls
            p.value = float(val.text()) if val.text() else 0
            if fx.checkState() == Qt.Checked:
                p.expr = str(val.text())
            else:
                p.expr = str(expr.currentText())
            p.pmin = float(pmin.text()) if pmin.text() else None
            p.pmax = float(pmax.text()) if pmax.text() else None
            p.delta = float(delta.text()) if delta.text() else 0
        self.update_enables()
        session.set_dirty()

    def restore_from_params(self, other_params):
        for p in self.model.params:
            if p.name not in other_params:
                continue
            p0 = other_params[p.name]
            ctls = self.param_controls[p]
            ctls[1].setText('%.5g' % p0.value)
            ctls[2].setText(u'± %.5g' % p0.error)
            ctls[3].setChecked(False)
            if p0.expr and is_float(p0.expr):
                ctls[1].setText(p0.expr)
                ctls[3].setChecked(True)
                ctls[4].lineEdit().setText('')
            else:
                ctls[4].lineEdit().setText(p0.expr or '')
            ctls[5].setText(p0.pmin is not None and '%.5g' % p0.pmin or '')
            ctls[6].setText(p0.pmax is not None and '%.5g' % p0.pmax or '')
            ctls[7].setText(p0.delta and '%.5g' % p0.delta or '')
        session.set_dirty()
        self.do_plot()

    def save_original_params(self):
        self.original_params = {}
        for p in self.model.params:
            self.original_params[p.name] = p.copy()

    def on_canvas_pick(self, event):
        if not self.picking:
            return
        if not hasattr(event, 'xdata') or event.xdata is None:
            return
        self._pick_values.append((event.xdata, event.ydata))
        if len(self._pick_values) == len(self._pick_points):
            self.picking = False
            self.statusLabel.setText('')
            self._pick_finished()
        else:
            self.statusLabel.setText('%s: click on %s' %
                                     (self.picking,
                                      self._pick_points[len(self._pick_values)]))

    def do_pick(self, *args):
        if self.picking:
            return
        self.emit(SIGNAL('pickRequest'), self)
        self._pick_points = self.model.get_pick_points()
        self._pick_values = []
        self.picking = 'Guess'
        self.statusLabel.setText('Guess: click on %s' % self._pick_points[0])

        def callback():
            self.model.apply_pick(self._pick_values)
            for p in self.model.params:
                ctls = self.param_controls[p]
                if not p.expr:
                    ctls[1].setText('%.5g' % p.value)
            session.set_dirty()
            self.do_plot()
        self._pick_finished = callback

    def do_plot(self, *ignored):
        self.update_from_controls()
        self.emit(SIGNAL('replotRequest'), None)

    def do_fit(self):
        if self.picking:
            QMessageBox.information(self, 'Fitting',
                                    'Please finish the picking operation first.')
            return
        self.update_from_controls()
        self.statusLabel.setText('Working...')
        self.statusLabel.repaint()
        QApplication.processEvents()
        try:
            res = self.model.fit(self.data, **self.fit_kws)
        except Exception as e:
            self.logger.exception('Error during fit')
            self.statusLabel.setText('Error during fit: %s' % e)
            return
        self.on_modelFitted(self.item, res)

        self.emit(SIGNAL('replotRequest'), True)
        session.set_dirty()

    def on_modelFitted(self, item, res):
        if item is not self.item:
            return

        self.statusLabel.setText(
            (res.success and 'Converged. ' or 'Failed. ') + res.message +
            ' Reduced chi^2 = %.3g.' % res.chisqr)

        for p in res.params:
            self.param_controls[p][1].setText('%.5g' % p.value)
            self.param_controls[p][2].setText(u'± %.5g' % p.error)

        self.last_result = res


class FitterMain(QMainWindow):
    def __init__(self, model, data, fit=True, fit_kws={}):
        QMainWindow.__init__(self)
        layout = QSplitter(Qt.Vertical, self)
        self.canvas = MPLCanvas(self)
        self.toolbar = MPLToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.fitter = Fitter(self, standalone=True, fit_kws=fit_kws)
        self.canvas.mpl_connect('button_press_event',
                                self.fitter.on_canvas_pick)
        self.connect(self.fitter, SIGNAL('closeRequest'), self.close)
        self.connect(self.fitter, SIGNAL('replotRequest'), self.replot)
        self.fitter.initialize(model, data, fit)
        layout.addWidget(self.fitter)
        self.setCentralWidget(layout)
        self.setWindowTitle('Fitting: data %s' % data.name)

    def replot(self, limits=True):
        plotter = self.canvas.plotter
        plotter.reset(limits=limits)
        try:
            plotter.plot_data(self.fitter.data)
            plotter.plot_model_full(self.fitter.model, self.fitter.data)
        except Exception:
            logger.exception('Error while plotting')
        else:
            plotter.draw()


def start(model, data, fit=True, **fit_kws):
    app = QApplication([])
    win = FitterMain(model, data, fit, fit_kws)
    win.show()
    app.exec_()
    return win.fitter.last_result
