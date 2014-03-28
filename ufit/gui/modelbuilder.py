#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2014, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Model builder panel."""

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL
from PyQt4.QtGui import QWidget, QListWidgetItem, QDialogButtonBox, \
     QMessageBox, QInputDialog, QTextCursor

from ufit.models import concrete_models, eval_model
from ufit.models.corr import Background
from ufit.models.peaks import Gauss
from ufit.gui.common import loadUi


class ModelBuilder(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.gauss_picking = 0
        self.gauss_peak_pos = 0, 0
        self.pick_model = None
        self.data = None
        self.last_model = None
        self.createUI()

    def createUI(self):
        loadUi(self, 'modelbuilder.ui')
        self.modeldefStacker.setCurrentIndex(0)
        self.model_dict = {}
        for model in concrete_models:
            QListWidgetItem(model.__name__, self.premodelsList)
            self.model_dict[model.__name__] = model
        self.buttonBox.addButton('Check', QDialogButtonBox.NoRole)
        self.buttonBox.addButton(QDialogButtonBox.Apply)

    def on_buttonBox_clicked(self, button):
        role = self.buttonBox.buttonRole(button)
        if role == QDialogButtonBox.ResetRole:
            self.modeldefEdit.setText('')
        elif role == QDialogButtonBox.NoRole:
            self.eval_model()
        else:  # "apply"
            self.eval_model(final=True)

    @qtsig('')
    def on_gaussOnlyBtn_clicked(self):
        if self.gauss_picking:
            self._finish_picking()
            return
        self.gaussOnlyBtn.setText('Back to full modeling mode')
        self.emit(SIGNAL('pickRequest'), self)
        self.gauss_picking = 1
        self.gauss_picked_points = []
        self.modeldefStacker.setCurrentIndex(1)
        self.pick_model = Background(bkgd=self.data.y.min())
        self.modeldefEdit.setText(self.pick_model.get_description())
        self.emit(SIGNAL('newModel'), self.pick_model, False)

    def on_canvas_pick(self, event):
        if not self.gauss_picking:
            return
        if hasattr(event, 'artist'):
            return
        if self.gauss_picking % 2 == 1:
            # first click, picked position
            self.gauss_peak_pos = event.xdata, event.ydata
        else:
            # second click, picked width
            pos = self.gauss_peak_pos[0]
            ampl = self.gauss_peak_pos[1] - self.data.y.min()
            fwhm = abs(pos - event.xdata) * 2
            self.pick_model += Gauss('p%02d' % self.gauss_picking,
                                     pos=pos, ampl=ampl, fwhm=fwhm)
            self.emit(SIGNAL('newModel'), self.pick_model, False)
            self.modeldefEdit.setText(self.pick_model.get_description())
        self.gauss_picking += 1

    def _finish_picking(self):
        if not self.gauss_picking:
            return
        self.gauss_picking = None
        self.gaussOnlyBtn.setText('Gauss peaks only mode')
        self.modeldefStacker.setCurrentIndex(0)

    def on_premodelsList_currentItemChanged(self, current, previous):
        model = self.model_dict[str(current.text())]
        self.modelinfoLbl.setText(model.__doc__)

    def on_premodelsList_itemDoubleClicked(self, item):
        self.on_addmodelBtn_clicked()

    @qtsig('')
    def on_addmodelBtn_clicked(self):
        modelitem = self.premodelsList.currentItem()
        if not modelitem:
            return
        model = self.model_dict[str(modelitem.text())]
        modelname = QInputDialog.getText(self, 'ufit', 'Please enter a name '
                                         'for the model part:')[0]
        if not modelname:
            return
        currentmodel = str(self.modeldefEdit.toPlainText())
        prefix = ''
        if currentmodel:
            prefix = ' + '
        tc = self.modeldefEdit.textCursor()
        tc.movePosition(QTextCursor.End)
        tc.insertText('%s%s(%r)' % (prefix, model.__name__, str(modelname)))

    def default_model(self, data):
        ymin = data.y.min()
        ymaxidx = data.y.argmax()
        ymax = data.y[ymaxidx]
        xmax = data.x[ymaxidx]
        overhalf = data.x[data.y > (ymax + ymin)/2.]
        if len(overhalf) >= 2:
            xwidth = abs(overhalf[0] - overhalf[-1]) or 0.1
        else:
            xwidth = 0.1
        new_model = eval_model('Background() + Gauss(\'peak\')')
        new_model.params[0].value = ymin
        new_model.params[1].value = xmax
        new_model.params[2].value = ymax-ymin
        new_model.params[3].value = xwidth
        return new_model

    def initialize(self, data, model):
        self.model = model
        self.data = data
        self.modeldefEdit.setText(model.get_description())

    def eval_model(self, final=False):
        modeldef = str(self.modeldefEdit.toPlainText()).replace('\n', ' ')
        if not modeldef:
            QMessageBox.information(self, 'Error', 'No model defined.')
            return
        try:
            model = eval_model(modeldef)
        except Exception, e:
            QMessageBox.information(self, 'Error',
                                    'Could not evaluate model: %s' % e)
            return
        if final:
            self._finish_picking()
            self.last_model = model
            self.emit(SIGNAL('newModel'), model)
            self.emit(SIGNAL('closeRequest'))
        else:
            self.statusLbl.setText('Model definition is good.')
