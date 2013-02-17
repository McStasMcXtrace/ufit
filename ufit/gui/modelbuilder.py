#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Model builder panel."""

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL
from PyQt4.QtGui import QWidget, QListWidgetItem, QDialogButtonBox, \
     QMessageBox, QInputDialog, QTextCursor

from ufit.models import concrete_models, eval_model
from ufit.gui.common import loadUi


class ModelBuilder(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.data = None
        self.last_model = None
        self.createUI()

    def createUI(self):
        loadUi(self, 'modelbuilder.ui')
        self.model_dict = {}
        for model in concrete_models:
            QListWidgetItem(model.__name__, self.premodels)
            self.model_dict[model.__name__] = model
        self.buttonBox.addButton('Check', QDialogButtonBox.NoRole)
        self.buttonBox.addButton(QDialogButtonBox.Apply)

    def on_buttonBox_clicked(self, button):
        role = self.buttonBox.buttonRole(button)
        if role == QDialogButtonBox.ResetRole:
            self.modeldef.setText('')
        elif role == QDialogButtonBox.NoRole:
            self.eval_model()
        else:  # "apply"
            self.eval_model(final=True)

    def on_premodels_currentItemChanged(self, current, previous):
        model = self.model_dict[str(current.text())]
        self.modelinfo.setText(model.__doc__)

    def on_premodels_itemDoubleClicked(self, item):
        self.on_addmodel_clicked()

    @qtsig('')
    def on_addmodel_clicked(self):
        modelitem = self.premodels.currentItem()
        if not modelitem:
            return
        model = self.model_dict[str(modelitem.text())]
        modelname = QInputDialog.getText(self, 'ufit', 'Please enter a name '
                                         'for the model part:')[0]
        if not modelname:
            return
        currentmodel = str(self.modeldef.toPlainText())
        prefix = ''
        if currentmodel:
            prefix = ' + '
        tc = self.modeldef.textCursor()
        tc.movePosition(QTextCursor.End)
        tc.insertText('%s%s(%r)' % (prefix, model.__name__, str(modelname)))

    def default_model(self, data):
        ymin = data.y.min()
        ymaxidx = data.y.argmax()
        ymax = data.y[ymaxidx]
        xmax = data.x[ymaxidx]
        overhalf = data.x[data.y > ymax/2.]
        xwidth = abs((overhalf[0] - overhalf[-1]) / 1.8) or 0.1
        new_model = eval_model('Background() + Gauss(\'peak\')')
        new_model.params[0].value = ymin
        new_model.params[1].value = xmax
        new_model.params[2].value = ymax-ymin
        new_model.params[3].value = xwidth
        return new_model

    def initialize(self, data, model):
        self.model = model
        self.data = data
        self.modeldef.setText(model.get_description())

    def eval_model(self, final=False):
        modeldef = str(self.modeldef.toPlainText()).replace('\n', ' ')
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
            self.last_model = model
            self.emit(SIGNAL('newModel'), model)
            self.emit(SIGNAL('closeRequest'))
        else:
            self.statusLabel.setText('Model definition is good.')
