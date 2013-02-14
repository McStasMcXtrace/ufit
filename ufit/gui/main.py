#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Main window for the standalone GUI."""

import cPickle as pickle

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL, QModelIndex
from PyQt4.QtGui import QMainWindow, QVBoxLayout, QApplication, QTabWidget, \
     QFrame, QMessageBox, QFileDialog

from ufit.gui.common import MPLCanvas, MPLToolbar, loadUi
from ufit.gui.dataloader import DataLoader
from ufit.gui.dataops import DataOps
from ufit.gui.modelbuilder import ModelBuilder
from ufit.gui.fitter import Fitter
from ufit.gui.datalist import DataListModel


class DatasetPanel(QTabWidget):
    def __init__(self, parent, canvas, data, model=None):
        QTabWidget.__init__(self, parent)
        self.data = data
        self.dataops = DataOps(self)
        self.mbuilder = ModelBuilder(self)
        self.fitter = Fitter(self)
        self.model = model or self.mbuilder.default_model(data)
        self._limits = None
        self.picker_widget = None

        self.canvas = canvas
        self.dataops.initialize(self.data)
        self.mbuilder.initialize(self.data, self.model)
        self.fitter.initialize(self.model, self.data, fit=False)
        self.connect(self.dataops, SIGNAL('pickRequest'), self.set_picker)
        self.connect(self.dataops, SIGNAL('replotRequest'), self.replot)
        self.connect(self.mbuilder, SIGNAL('newModel'),
                     self.on_mbuilder_newModel)
        self.connect(self.fitter, SIGNAL('replotRequest'), self.replot)
        self.connect(self.fitter, SIGNAL('pickRequest'), self.set_picker)
        self.addTab(self.dataops, 'Data operations')
        self.addTab(self.mbuilder, 'Modeling')
        self.addTab(self.fitter, 'Fitting')

    def on_mbuilder_newModel(self, model):
        self.model = model
        self.fitter.initialize(self.model, self.data, fit=False)
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

        loadUi(self, 'main.ui')

        # populate plot view
        layout2 = QVBoxLayout()
        layout2.setContentsMargins(0, 0, 0, 0)
        self.canvas = MPLCanvas(self)
        self.canvas.mpl_connect('button_press_event', self.on_canvas_pick)
        self.canvas.mpl_connect('pick_event', self.on_canvas_pick)
        # XXX can one add to the MPL toolbar?
        self.toolbar = MPLToolbar(self.canvas, self)
        layout2.addWidget(self.toolbar)
        layout2.addWidget(self.canvas)
        self.plotframe.setLayout(layout2)

        # create data loader
        # XXX more inputs: data name, take model from
        self.dloader = DataLoader(self, self.canvas.plotter)
        self.connect(self.dloader, SIGNAL('newData'), self.handle_new_data)
        self.stacker.addWidget(self.dloader)
        self.current_panel = self.dloader

        # XXX stopgap: add some useful things to do with multiple datasets
        # (e.g. plot fit parameters vs another parameter)
        self.empty = QFrame(self)
        self.stacker.addWidget(self.empty)

        # XXX context menu: remove, merge with other
        self.datalistmodel = DataListModel(self.panels)
        self.datalist.setModel(self.datalistmodel)
        self.datalistmodel.reset()
        self.connect(self.datalist, SIGNAL('newSelection'),
                     self.on_datalist_newSelection)

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

    def on_datalist_newSelection(self):
        if self._loading:
            return
        indlist = [ind.row() for ind in self.datalist.selectedIndexes()]
        if len(indlist) == 0:
            self.on_loadBtn_clicked()
        elif len(indlist) == 1:
            panel = self.panels[indlist[0]][1]
            self.select_new_panel(panel)
            panel.replot(panel._limits)
            self.toolbar.update()
        else:
            panels = [self.panels[i][1] for i in indlist]
            self.canvas.plotter.reset()
            # XXX this doesn't belong here
            for p in panels:
                c = self.canvas.plotter.plot_data(p.data, multi=True)
                self.canvas.plotter.plot_model(p.model, p.data, labels=False,
                                               color=c)
            # XXX better title
            self.canvas.draw()
            self.select_new_panel(self.empty)

    def handle_new_data(self, data, model=None):
        panel = DatasetPanel(self, self.canvas, data, model)
        self.stacker.addWidget(panel)
        self.stacker.setCurrentWidget(panel)
        self.panels.append(
            ('<big><b>%s</b></big> - %s<br>%s<br><small>%s</small>' %
             (len(self.panels) + 1,
              data.data_title,
              data.environment,
              '<br>'.join(data.sources)), panel))
        self.datalistmodel.reset()
        if not self._loading:
            self.datalist.setCurrentIndex(
                self.datalistmodel.index(len(self.panels)-1, 0))

    @qtsig('')
    def on_actionLoadData_triggered(self):
        self.on_loadBtn_clicked()

    @qtsig('')
    def on_actionConnectData_toggled(self, on):
        self.canvas.plotter.lines = on
        # XXX replot

    @qtsig('')
    def on_actionLoad_triggered(self):
        filename = QFileDialog.getOpenFileName(
            self, 'Select file name', '', 'ufit files (*.ufit)')
        if filename == '':
            return
        self.load_session(str(filename))

    def load_session(self, filename):
        for panel in self.panels[1:]:
            self.stacker.removeWidget(panel[1])
        del self.panels[1:]
        info = pickle.load(open(filename, 'rb'))
        self._loading = True
        try:
            for data, model in info['panels']:
                self.handle_new_data(data, model)
        finally:
            self._loading = False
        self.datalist.setCurrentIndex(
            self.datalistmodel.index(len(self.panels)-1, 0))

    @qtsig('')
    def on_actionSave_triggered(self):
        # XXX track self filename
        self.on_actionSaveAs_triggered()

    @qtsig('')
    def on_actionSaveAs_triggered(self):
        filename = QFileDialog.getSaveFileName(
            self, 'Select file name', '', 'ufit files (*.ufit)')
        if filename == '':
            return
        self.save_session(str(filename))

    def save_session(self, filename):
        fp = open(filename, 'wb')
        info = {
            'panels': [(panel[1].data, panel[1].model) for panel in self.panels]
        }
        pickle.dump(info, fp, protocol=pickle.HIGHEST_PROTOCOL)

    @qtsig('')
    def on_actionAbout_triggered(self):
        QMessageBox.information(self, 'About',
                                'ufit, written by Georg Brandl 2013.')

    @qtsig('')
    def on_actionQuit_triggered(self):
        # XXX ask for saving
        self.close()


def main(args):
    import time
    print 'starting up app...'
    t1 = time.time()
    app = QApplication([])
    # XXX window geometry
    win = UFitMain()

    if args:
        datafile = args[0]
        if datafile.endswith('.ufit'):
            win.load_session(datafile)
        else:
            win.dloader.set_template(datafile)

    t2 = time.time()
    print 'loading finished (%.3f), main window showing...' % (t2-t1)
    win.show()
    app.exec_()
