#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Model builder panel."""

import re

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL
from PyQt4.QtGui import QWidget, QListWidgetItem, QDialogButtonBox, \
    QMessageBox, QInputDialog, QTextCursor, QDialog

from ufit.models import concrete_models, eval_model
from ufit.models.corr import Background
from ufit.models.peaks import GaussInt
from ufit.gui import logger
from ufit.gui.common import loadUi

ident_re = re.compile('[a-zA-Z][a-zA-Z0-9_]*$')


class ModelBuilder(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.logger = logger.getChild('model')
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
        self.emit(SIGNAL('newModel'), self.pick_model, True, False)

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
            self.pick_model += GaussInt('p%02d' % (self.gauss_picking/2),
                                        pos=pos, int=fwhm*ampl*2.5, fwhm=fwhm)
            self.emit(SIGNAL('newModel'), self.pick_model, True, False)
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
        modelcls = str(modelitem.text())
        modelname = QInputDialog.getText(self, 'ufit', 'Please enter a name '
                                         'for the model part:')[0]
        if not modelname:
            return
        self.insert_model_code('%s(%r)' % (modelcls, str(modelname)))

    @qtsig('')
    def on_addCustomBtn_clicked(self):
        dlg = QDialog(self)
        loadUi(dlg, 'custommodel.ui')
        while 1:
            if dlg.exec_() != QDialog.Accepted:
                return
            modelname = str(dlg.nameBox.text())
            params = str(dlg.paramBox.text())
            value = str(dlg.valueEdit.toPlainText()).strip()
            if not ident_re.match(modelname):
                QMessageBox.warning(self, 'Error', 'Please enter a valid model '
                                    'name (must be a Python identifier using '
                                    'only alphabetic characters and digits).')
                continue
            if not params:
                QMessageBox.warning(self, 'Error', 'Please enter some parameters.')
                continue
            for param in params.split():
                if not ident_re.match(param):
                    QMessageBox.warning(
                        self, 'Error', 'Parameter name %s is not valid (must '
                        'be a Python identifier using only alphabetic '
                        'characters and digits).' % param)
                    params = None
                    break
            if not params:
                continue
            break
        self.insert_model_code('Custom(%r, %r, %r)' % (modelname, params, value))

    def insert_model_code(self, code):
        currentmodel = str(self.modeldefEdit.toPlainText())
        prefix = ''
        if currentmodel:
            prefix = ' + '
        tc = self.modeldefEdit.textCursor()
        tc.movePosition(QTextCursor.End)
        tc.insertText(prefix + code)

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
        except Exception as e:
            self.logger.exception('Could not evaluate model')
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
