#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Main window for the standalone GUI."""

import sys
from os import path
import cPickle as pickle

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL, QModelIndex, QVariant
from PyQt4.QtGui import QMainWindow, QVBoxLayout, QApplication, QTabWidget, \
     QMessageBox, QFileDialog, QDialog, QAction, QActionGroup

from ufit import backends
from ufit.gui.common import MPLCanvas, MPLToolbar, SettingGroup, loadUi
from ufit.gui.dataloader import DataLoader
from ufit.gui.dataops import DataOps, MultiDataOps
from ufit.gui.modelbuilder import ModelBuilder
from ufit.gui.fitter import Fitter
from ufit.gui.datalist import DataListModel


SAVE_VERSION = 1

class DatasetPanel(QTabWidget):
    def __init__(self, parent, canvas, data, model, index):
        QTabWidget.__init__(self, parent)
        self.data = data
        self.dataops = DataOps(self)
        self.mbuilder = ModelBuilder(self)
        self.fitter = Fitter(self)
        self.model = model or self.mbuilder.default_model(data)
        self._limits = None
        self.picker_widget = None
        self.index = index

        self.canvas = canvas
        self.dataops.initialize(self.data)
        self.mbuilder.initialize(self.data, self.model)
        self.fitter.initialize(self.model, self.data, fit=False)
        self.connect(self.dataops, SIGNAL('pickRequest'), self.set_picker)
        self.connect(self.dataops, SIGNAL('replotRequest'), self.replot)
        self.connect(self.dataops, SIGNAL('dirty'), self.set_dirty)
        self.connect(self.mbuilder, SIGNAL('newModel'),
                     self.on_mbuilder_newModel)
        self.connect(self.fitter, SIGNAL('replotRequest'), self.replot)
        self.connect(self.fitter, SIGNAL('pickRequest'), self.set_picker)
        self.connect(self.fitter, SIGNAL('dirty'), self.set_dirty)
        self.addTab(self.dataops, 'Data operations')
        self.addTab(self.mbuilder, 'Modeling')
        self.addTab(self.fitter, 'Fitting')
        self.setCurrentWidget(self.mbuilder)

        title = self.data.meta.get('title', '')
        self.htmldesc = '<big><b>%s</b></big>' % self.index + \
            (title and ' - %s' % title or '') + \
            (self.data.environment and
             '<br>%s' % ', '.join(self.data.environment) or '') + \
            ('<br><small>%s</small>' % '<br>'.join(self.data.sources))

    def as_html(self):
        return self.htmldesc

    def set_dirty(self):
        self.emit(SIGNAL('dirty'))

    def on_mbuilder_newModel(self, model):
        self.handle_new_model(model, update_mbuilder=False)
        self.set_dirty()

    def handle_new_model(self, model, update_mbuilder=True,
                         keep_paramvalues=True):
        if update_mbuilder:
            self.mbuilder.modeldef.setText(model.get_description())
        self.model = model
        self.fitter.initialize(self.model, self.data, fit=False,
                               keep_old=keep_paramvalues)
        self.setCurrentWidget(self.fitter)

    def set_picker(self, widget):
        self.picker_widget = widget

    def on_canvas_pick(self, event):
        if self.picker_widget:
            self.picker_widget.on_canvas_pick(event)

    def save_limits(self):
        self._limits = self.canvas.axes.get_xlim(), self.canvas.axes.get_ylim()

    def replot(self, limits=True, paramdict=None):
        plotter = self.canvas.plotter
        plotter.reset(limits)
        try:
            plotter.plot_data(self.data)
            plotter.plot_model_full(self.model, self.data, paramdict=paramdict)
        except Exception, e:
            print 'Error while plotting:', e
            return
        self.canvas.draw()


class UFitMain(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        self._loading = False
        self.current_panel = None
        self.panels = []
        self.filename = None
        self.sgroup = SettingGroup('main')
        self.max_index = 1

        loadUi(self, 'main.ui')

        # XXX add an annotations tab

        # populate plot view
        layout2 = QVBoxLayout()
        layout2.setContentsMargins(0, 0, 0, 0)
        self.canvas = MPLCanvas(self)
        self.canvas.mpl_connect('button_press_event', self.on_canvas_pick)
        self.canvas.mpl_connect('pick_event', self.on_canvas_pick)
        self.toolbar = MPLToolbar(self.canvas, self)
        firstaction = self.toolbar.actions()[0]
        self.toolbar.insertAction(firstaction, self.actionLoad)
        self.toolbar.insertAction(firstaction, self.actionSave)
        self.toolbar.insertSeparator(firstaction)
        self.toolbar.setObjectName('maintoolbar')
        self.addToolBar(self.toolbar)
        layout2.addWidget(self.canvas)
        self.plotframe.setLayout(layout2)

        # create data loader
        self.dloader = DataLoader(self, self.canvas.plotter)
        self.connect(self.dloader, SIGNAL('newData'), self.handle_new_data)
        self.stacker.addWidget(self.dloader)
        self.current_panel = self.dloader

        self.multiops = MultiDataOps(self)
        self.connect(self.multiops, SIGNAL('newData'), self.handle_new_data)
        self.connect(self.multiops, SIGNAL('replotRequest'), self.plot_multi)
        self.connect(self.multiops, SIGNAL('dirty'), self.set_dirty)
        self.stacker.addWidget(self.multiops)

        self.datalistmodel = DataListModel(self.panels)
        self.datalist.setModel(self.datalistmodel)
        self.datalistmodel.reset()
        self.datalist.addAction(self.actionMergeData)
        self.datalist.addAction(self.actionRemoveData)
        self.connect(self.datalist, SIGNAL('newSelection'),
                     self.on_datalist_newSelection)

        self.backend_group = QActionGroup(self)
        for backend in backends.available:
            action = QAction(backend.backend_name, self)
            action.setCheckable(True)
            if backends.backend.backend_name == backend.backend_name:
                action.setChecked(True)
            self.backend_group.addAction(action)
            self.menuBackend.addAction(action)
            self.connect(action, SIGNAL('triggered()'),
                         self.on_backend_action_triggered)

        with self.sgroup as settings:
            geometry = settings.value('geometry').toByteArray()
            self.restoreGeometry(geometry)
            windowstate = settings.value('windowstate').toByteArray()
            self.restoreState(windowstate)
            splitstate = settings.value('splitstate').toByteArray()
            self.splitter.restoreState(splitstate)
            vsplitstate = settings.value('vsplitstate').toByteArray()
            self.vsplitter.restoreState(vsplitstate)

    def set_dirty(self):
        self.setWindowModified(True)

    def select_new_panel(self, panel):
        if isinstance(self.current_panel, DatasetPanel):
            self.current_panel.save_limits()
        self.current_panel = panel
        self.stacker.setCurrentWidget(self.current_panel)

    def on_canvas_pick(self, event):
        if isinstance(self.current_panel, DatasetPanel):
            self.current_panel.on_canvas_pick(event)

    @qtsig('')
    def on_loadBtn_clicked(self):
        self.select_new_panel(self.dloader)
        self.datalist.setCurrentIndex(QModelIndex())

    @qtsig('')
    def on_removeBtn_clicked(self):
        indlist = [ind.row() for ind in self.datalist.selectedIndexes()]
        if not indlist:
            return
        if QMessageBox.question(self, 'ufit',
                                'OK to remove %d dataset(s)?' % len(indlist),
                                QMessageBox.Yes|QMessageBox.No) == QMessageBox.No:
            return
        new_panels = [p for i, p in enumerate(self.panels) if i not in indlist]
        self.panels[:] = new_panels
        self.datalistmodel.reset()
        self.setWindowModified(True)
        self.on_loadBtn_clicked()

    def on_datalist_newSelection(self):
        if self._loading:
            return
        indlist = [ind.row() for ind in self.datalist.selectedIndexes()]
        if len(indlist) == 0:
            self.on_loadBtn_clicked()
        elif len(indlist) == 1:
            panel = self.panels[indlist[0]]
            self.select_new_panel(panel)
            panel.replot(panel._limits)
            self.toolbar.update()
        else:
            self.plot_multi()
            self.multiops.initialize([self.panels[i] for i in indlist])
            self.select_new_panel(self.multiops)

    def plot_multi(self, *ignored):
        # XXX better title
        self.canvas.plotter.reset()
        indlist = [ind.row() for ind in self.datalist.selectedIndexes()]
        panels = [self.panels[i] for i in indlist]
        for p in panels:
            c = self.canvas.plotter.plot_data(p.data, multi=True)
            self.canvas.plotter.plot_model(p.model, p.data, labels=False,
                                           color=c)
        self.canvas.draw()

    def handle_new_data(self, data, update=True, model=None):
        panel = DatasetPanel(self, self.canvas, data, model, self.max_index)
        self.connect(panel, SIGNAL('dirty'), self.set_dirty)
        self.max_index += 1
        self.stacker.addWidget(panel)
        self.stacker.setCurrentWidget(panel)
        self.panels.append(panel)
        self.setWindowModified(True)
        if not self._loading and update:
            self.datalistmodel.reset()
            self.datalist.setCurrentIndex(
                self.datalistmodel.index(len(self.panels)-1, 0))

    @qtsig('')
    def on_actionLoadData_triggered(self):
        self.on_loadBtn_clicked()

    def on_actionConnectData_toggled(self, on):
        self.canvas.plotter.lines = on
        # XXX replot

    def on_actionDrawSymbols_toggled(self, on):
        self.canvas.plotter.symbols = on
        # XXX replot

    def check_save(self):
        if not self.isWindowModified():  # nothing there to be saved
            return True
        resp = QMessageBox.question(self, 'ufit', 'Save current session?',
            QMessageBox.Yes|QMessageBox.No|QMessageBox.Cancel)
        if resp == QMessageBox.Yes:
            return self.save_session()
        elif resp == QMessageBox.No:
            return True
        return False

    @qtsig('')
    def on_actionLoad_triggered(self):
        if not self.check_save():
            return
        if self.filename:
            initialdir = path.dirname(self.filename)
        else:
            initialdir = ''
        filename = QFileDialog.getOpenFileName(
            self, 'Select file name', initialdir, 'ufit files (*.ufit)')
        if filename == '':
            return
        self.filename = unicode(filename).encode(sys.getfilesystemencoding())
        try:
            self.load_session(self.filename)
        except Exception, err:
            QMessageBox.warning(self, 'Error', 'Loading failed: %s' % err)

    def load_session(self, filename):
        for panel in self.panels[1:]:
            self.stacker.removeWidget(panel)
        del self.panels[1:]
        info = pickle.load(open(filename, 'rb'))
        self._loading = True
        try:
            for data, model in info['datasets']:
                self.handle_new_data(data, False, model)
            self.dloader.datatemplate.setText(info['template'])
        finally:
            self._loading = False
        self.datalistmodel.reset()
        self.datalist.setCurrentIndex(
            self.datalistmodel.index(len(self.panels)-1, 0))
        self.setWindowModified(False)
        self.setWindowTitle('ufit - %s[*]' % self.filename)

    @qtsig('')
    def on_actionSave_triggered(self):
        self.save_session()

    @qtsig('')
    def on_actionSaveAs_triggered(self):
        self.save_session_as()

    def save_session(self):
        if self.filename is None:
            return self.save_session_as()
        try:
            self.save_session_inner(self.filename)
        except Exception, err:
            QMessageBox.warning(self, 'Error', 'Saving failed: %s' % err)
            return False
        self.setWindowModified(False)
        return True

    def save_session_as(self):
        if self.filename:
            initialdir = path.dirname(self.filename)
        else:
            initialdir = ''
        filename = QFileDialog.getSaveFileName(
            self, 'Select file name', initialdir, 'ufit files (*.ufit)')
        if filename == '':
            return False
        self.filename = unicode(filename).encode(sys.getfilesystemencoding())
        try:
            self.save_session_inner(self.filename)
        except Exception, err:
            QMessageBox.warning(self, 'Error', 'Saving failed: %s' % err)
            return False
        else:
            self.setWindowModified(False)
            self.setWindowTitle('ufit - %s[*]' % self.filename)
            return True

    def save_session_inner(self, filename):
        fp = open(filename, 'wb')
        info = {
            'datasets': [(panel.data, panel.model) for panel in self.panels],
            'template': str(self.dloader.datatemplate.text()),
            'version':  SAVE_VERSION,
        }
        pickle.dump(info, fp, protocol=pickle.HIGHEST_PROTOCOL)

    @qtsig('')
    def on_actionRemoveData_triggered(self):
        self.on_removeBtn_clicked()

    @qtsig('')
    def on_actionMergeData_triggered(self):
        indlist = [ind.row() for ind in self.datalist.selectedIndexes()]
        if len(indlist) < 2:
            return
        dlg = QDialog(self)
        loadUi(dlg, 'rebin.ui')
        if dlg.exec_():
            precision = dlg.precision.value()
            datalist = [p.data for i, p in enumerate(self.panels)
                        if i in indlist]
            new_data = datalist[0].merge(precision, *datalist[1:])
            self.handle_new_data(new_data)

    @qtsig('')
    def on_actionQuit_triggered(self):
        self.close()

    def closeEvent(self, event):
        if not self.check_save():
            event.ignore()
            return
        event.accept()
        with self.sgroup as settings:
            settings.setValue('geometry', QVariant(self.saveGeometry()))
            settings.setValue('windowstate', QVariant(self.saveState()))
            settings.setValue('splitstate', QVariant(self.splitter.saveState()))
            settings.setValue('vsplitstate',
                              QVariant(self.vsplitter.saveState()))

    @qtsig('')
    def on_actionAbout_triggered(self):
        QMessageBox.information(self, 'About',
                                'ufit, written by Georg Brandl 2013.')

    @qtsig('')
    def on_backend_action_triggered(self):
        backends.set_backend(str(self.sender().text()))


def main(args):
    import time
    print 'starting up app...'
    t1 = time.time()
    app = QApplication([])
    app.setOrganizationName('ufit')
    app.setApplicationName('gui')
    mainwindow = UFitMain()

    if args:
        datafile = path.abspath(args[0])
        if datafile.endswith('.ufit'):
            try:
                mainwindow.filename = datafile
                mainwindow.load_session(datafile)
            except Exception, err:
                QMessageBox.warning(mainwindow,
                                    'Error', 'Loading failed: %s' % err)
                mainwindow.filename = None
        else:
            mainwindow.dloader.set_template(datafile)

    t2 = time.time()
    print 'loading finished (%.3f s), main window showing...' % (t2-t1)
    mainwindow.show()
    app.exec_()
