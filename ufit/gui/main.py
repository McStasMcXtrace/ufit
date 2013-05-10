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
from cStringIO import StringIO

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL, QModelIndex, \
     QVariant, QByteArray, QRectF
from PyQt4.QtGui import QMainWindow, QVBoxLayout, QApplication, QTabWidget, \
     QMessageBox, QFileDialog, QDialog, QAction, QActionGroup, QPrinter, \
     QPrintPreviewWidget, QPainter, QPrintDialog, QListWidgetItem
from PyQt4.QtSvg import QSvgRenderer

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
        self.title = ''

        self.canvas = canvas
        self.dataops.initialize(self.data, self.model)
        self.mbuilder.initialize(self.data, self.model)
        self.fitter.initialize(self.model, self.data, fit=False)
        self.connect(self.dataops, SIGNAL('pickRequest'), self.set_picker)
        self.connect(self.dataops, SIGNAL('replotRequest'), self.replot)
        self.connect(self.dataops, SIGNAL('titleChanged'), self.update_htmldesc)
        self.connect(self.dataops, SIGNAL('dirty'), self.set_dirty)
        self.connect(self.dataops, SIGNAL('newData'), self.handle_new_data)
        self.connect(self.mbuilder, SIGNAL('newModel'),
                     self.on_mbuilder_newModel)
        self.connect(self.fitter, SIGNAL('replotRequest'), self.replot)
        self.connect(self.fitter, SIGNAL('pickRequest'), self.set_picker)
        self.connect(self.fitter, SIGNAL('dirty'), self.set_dirty)
        self.addTab(self.dataops, 'Data operations')
        self.addTab(self.mbuilder, 'Modeling')
        self.addTab(self.fitter, 'Fitting')
        self.setCurrentWidget(self.mbuilder)

        self.gen_htmldesc()

    def update_htmldesc(self):
        self.gen_htmldesc()
        self.emit(SIGNAL('updateList'))

    def gen_htmldesc(self):
        title = self.data.meta.get('title', '')
        self.dataops.datatitle.setText(title)
        self.title = title
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

    def handle_new_data(self, *args):
        self.emit(SIGNAL('newData'), *args)

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

    def replot(self, limits=True, paramvalues=None):
        plotter = self.canvas.plotter
        plotter.reset(limits)
        try:
            plotter.plot_data(self.data)
            plotter.plot_model_full(self.model, self.data,
                                    paramvalues=paramvalues)
        except Exception, e:
            print 'Error while plotting:', e
            return
        self.canvas.draw()

    def export_python(self, fp):
        fp.write('from ufit.lab import *\n')
        self.data.export_python(fp)
        self.model.export_python(fp)


class UFitMain(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        self._loading = False
        self.current_panel = None
        self.panels = []
        self.filename = None
        self.sgroup = SettingGroup('main')
        self.max_index = 1
        self.printer = None  # delay construction; takes half a second
        self.print_width = 0

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
        self.toolbar.insertAction(firstaction, self.actionPrint)
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

    @qtsig('')
    def on_reorderBtn_clicked(self):
        dlg = QDialog(self)
        loadUi(dlg, 'reorder.ui')
        for i, panel in enumerate(self.panels):
            QListWidgetItem('%s - %s' % (panel.index, panel.title),
                            dlg.datalist, i)
        if dlg.exec_():
            new_panels = []
            for i in range(dlg.datalist.count()):
                new_index = dlg.datalist.item(i).type()
                panel = self.panels[new_index]
                panel.index = i+1
                panel.gen_htmldesc()
                new_panels.append(panel)
            self.panels[:] = new_panels
            self.datalistmodel.reset()
            self.setWindowModified(True)

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
        self.canvas.plotter.plot_finish()
        self.canvas.draw()

    def handle_new_data(self, data, update=True, model=None):
        panel = DatasetPanel(self, self.canvas, data, model, self.max_index)
        self.connect(panel, SIGNAL('dirty'), self.set_dirty)
        self.connect(panel, SIGNAL('newData'), self.handle_new_data)
        self.connect(panel, SIGNAL('updateList'), self.datalistmodel.reset)
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

    @qtsig('')
    def on_actionExportASCII_triggered(self):
        if self.filename:
            initialdir = path.dirname(self.filename)
        else:
            initialdir = ''
        filename = QFileDialog.getSaveFileName(
            self, 'Select export file name', initialdir, 'ASCII text (*.txt)')
        if filename == '':
            return False
        expfilename = unicode(filename).encode(sys.getfilesystemencoding())
        with open(expfilename, 'wb') as fp:
            self.current_panel.data.export_ascii(fp)

    @qtsig('')
    def on_actionExportParams_triggered(self):
        QMessageBox.warning(self, 'Sorry', 'Not implemented yet.')

    @qtsig('')
    def on_actionExportPython_triggered(self):
        if self.filename:
            initialdir = path.dirname(self.filename)
        else:
            initialdir = ''
        filename = QFileDialog.getSaveFileName(
            self, 'Select export file name', initialdir, 'Python files (*.py)')
        if filename == '':
            return False
        expfilename = unicode(filename).encode(sys.getfilesystemencoding())
        with open(expfilename, 'wb') as fp:
            self.current_panel.export_python(fp)

    @qtsig('')
    def on_actionPrint_triggered(self):
        sio = StringIO()
        self.canvas.print_figure(sio, format='svg')
        svg = QSvgRenderer(QByteArray(sio.getvalue()))
        sz = svg.defaultSize()
        aspect = sz.width()/sz.height()

        if self.printer is None:
            self.printer = QPrinter(QPrinter.HighResolution)
            self.printer.setOrientation(QPrinter.Landscape)

        dlg = QDialog(self)
        loadUi(dlg, 'printpreview.ui')
        dlg.width.setValue(self.print_width or 500)
        ppw = QPrintPreviewWidget(self.printer, dlg)
        dlg.layout().insertWidget(1, ppw)
        def render(printer):
            height = printer.height() * (dlg.width.value()/1000.)
            width = aspect * height
            painter = QPainter(printer)
            svg.render(painter, QRectF(0, 0, width, height))
        def sliderchanged(newval):
            ppw.updatePreview()
        self.connect(ppw, SIGNAL('paintRequested(QPrinter *)'), render)
        self.connect(dlg.width, SIGNAL('valueChanged(int)'), sliderchanged)
        if dlg.exec_() != QDialog.Accepted:
            return
        self.print_width = dlg.width.value()
        pdlg = QPrintDialog(self.printer, self)
        if pdlg.exec_() != QDialog.Accepted:
            return
        render(self.printer)

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


def main(args, t0):
    import time
    t1 = time.time()
    print 'import finished (%.3f s), starting up app...' % (t1-t0)
    app = QApplication([])
    app.setOrganizationName('ufit')
    app.setApplicationName('gui')
    mainwindow = UFitMain()

    if len(args) == 1:
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
