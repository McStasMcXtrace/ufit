# -*- coding: utf-8 -*-
# ufit interactive fitting gui

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL, Qt
from PyQt4.QtGui import QWidget, QApplication, QSplitter, QMainWindow, \
     QListWidgetItem, QDialogButtonBox, QMessageBox, QInputDialog, QTextCursor

from ufit import models, param
from ufit.models import concrete_models
from ufit.gui.common import loadUi, MPLCanvas, MPLToolbar


class ModelBuilder(QWidget):

    def __init__(self, parent, plotter, standalone=False):
        QWidget.__init__(self, parent)
        self.plotter = plotter
        self.data = None
        self.last_model = None

        self.createUI(standalone)

    def createUI(self, standalone):
        loadUi(self, 'modelbuilder.ui')
        self.model_dict = {}
        for model in concrete_models:
            QListWidgetItem(model.__name__, self.premodels)
            self.model_dict[model.__name__] = model
        self.buttonBox.addButton('Preview', QDialogButtonBox.NoRole)
        self.buttonBox.addButton(QDialogButtonBox.Ok)

    def on_buttonBox_clicked(self, button):
        role = self.buttonBox.buttonRole(button)
        if role == QDialogButtonBox.ResetRole:
            self.modeldef.setText('')
        elif role == QDialogButtonBox.NoRole:
            self.eval_model()
        else:  # "ok"
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
        params = ', '.join('%s=0' % s for s in model.param_names)
        currentmodel = str(self.modeldef.toPlainText())
        prefix = ''
        if currentmodel:
            prefix = '\n+ '
        tc = self.modeldef.textCursor()
        tc.movePosition(QTextCursor.End)
        tc.insertText('%s%s(%r, %s)' % (prefix, model.__name__,
                                        str(modelname), params))

    def initialize(self, data):
        self.data = data
        self.setWindowTitle('Model: data %s' % data.name)
        # XXX stop this when loading GUI session
        self.plotter.reset()
        self.plotter.plot_data(data)
        self.plotter.draw()

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


class ModelBuilderMain(QMainWindow):
    def __init__(self, data):
        QMainWindow.__init__(self)
        layout = QSplitter(Qt.Vertical, self)
        self.canvas = MPLCanvas(self)
        self.toolbar = MPLToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.mbuilder = ModelBuilder(self, self.canvas.plotter,
                                     standalone=True)
        self.mbuilder.initialize(data)
        self.connect(self.mbuilder, SIGNAL('closeRequest'), self.close)
        layout.addWidget(self.fitter)
        self.setCentralWidget(layout)
        self.setWindowTitle(self.fitter.windowTitle())


def start(data):
    app = QApplication([])
    win = ModelBuilderMain(data)
    win.show()
    app.exec_()
    return win.mbuilder.last_model
