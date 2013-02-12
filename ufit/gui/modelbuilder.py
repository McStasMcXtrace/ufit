#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Model builder panel."""

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL, Qt
from PyQt4.QtGui import QWidget, QApplication, QSplitter, QMainWindow, \
     QListWidgetItem, QDialogButtonBox, QMessageBox, QInputDialog, QTextCursor

from ufit import models, param
from ufit.models import Background, Gauss, concrete_models
from ufit.gui.common import loadUi, MPLCanvas, MPLToolbar


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

    # XXX make a more intelligent model
    def default_model(self, data):
        return Background(bkgd=0) + Gauss('peak', pos=0, ampl=1, fwhm=1)

    def initialize(self, data, model):
        self.model = model
        self.data = data
        self.modeldef.setText(model.get_description())

    def eval_model(self, final=False):
        modeldef = str(self.modeldef.toPlainText()).replace('\n', ' ')
        if not modeldef:
            QMessageBox.information(self, 'Error', 'No model defined.')
            return
        d = models.__dict__.copy()
        d.update(param.__dict__)
        try:
            model = eval(modeldef, d)
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
