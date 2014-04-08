#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2014, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Main window for the standalone GUI."""

from os import path
import cPickle as pickle
from cStringIO import StringIO

from PyQt4.QtCore import pyqtSignature as qtsig, Qt, SIGNAL, QModelIndex, \
    QByteArray, QRectF
from PyQt4.QtGui import QMainWindow, QVBoxLayout, QMessageBox, QPixmap, \
    QFileDialog, QDialog, QPainter, QAction, QActionGroup, QPrinter, \
    QPrintPreviewWidget, QPrintDialog, QListWidgetItem, QSplashScreen
from PyQt4.QtSvg import QSvgRenderer

from ufit import backends, __version__
from ufit.gui import logger
from ufit.gui.common import MPLCanvas, MPLToolbar, SettingGroup, loadUi, \
    path_to_str
from ufit.gui.dataloader import DataLoader
from ufit.gui.multiops import MultiDataOps
from ufit.gui.itemlist import ItemListModel
from ufit.gui.inspector import InspectorWindow
from ufit.gui.datasetitem import DatasetPanel
from ufit.gui.mappingitem import MappingPanel

SAVE_VERSION = 2
max_recent_files = 6

panel_types = {
    'dataset': DatasetPanel,
    'mapping': MappingPanel,
}


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
        self.inspector_window = None

        loadUi(self, 'main.ui')

        # XXX add an annotations tab

        # populate plot view
        layout2 = QVBoxLayout()
        layout2.setContentsMargins(0, 0, 0, 0)
        self.canvas = MPLCanvas(self)
        self.canvas.mpl_connect('button_press_event', self.on_canvas_pick)
        self.canvas.mpl_connect('pick_event', self.on_canvas_pick)
        self.toolbar = MPLToolbar(self.canvas, self)
        self.toolbar.setObjectName('mainplottoolbar')
        self.connect(self.toolbar, SIGNAL('printRequested'),
                     self.on_actionPrint_triggered)
        self.addToolBar(self.toolbar)
        layout2.addWidget(self.canvas)
        self.plotframe.setLayout(layout2)

        # create data loader
        self.dloader = DataLoader(self, self.canvas.plotter)
        self.connect(self.dloader, SIGNAL('newData'), self.handle_new_data)
        self.stacker.addWidget(self.dloader)
        self.current_panel = self.dloader

        self.multiops = MultiDataOps(self, self.canvas)
        self.connect(self.multiops, SIGNAL('newData'), self.handle_new_data)
        self.connect(self.multiops, SIGNAL('newItem'), self.handle_new_item)
        self.connect(self.multiops, SIGNAL('replotRequest'), self.plot_multi)
        self.connect(self.multiops, SIGNAL('dirty'), self.set_dirty)
        self.stacker.addWidget(self.multiops)

        self.itemlistmodel = ItemListModel(self.panels)
        self.itemList.setModel(self.itemlistmodel)
        self.itemlistmodel.reset()
        self.itemList.addAction(self.actionMergeData)
        self.itemList.addAction(self.actionRemoveData)
        self.connect(self.itemList, SIGNAL('newSelection'),
                     self.on_itemList_newSelection)

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
            geometry = settings.value('geometry', QByteArray())
            self.restoreGeometry(geometry)
            windowstate = settings.value('windowstate', QByteArray())
            self.restoreState(windowstate)
            splitstate = settings.value('splitstate', QByteArray())
            self.splitter.restoreState(splitstate)
            vsplitstate = settings.value('vsplitstate', QByteArray())
            self.vsplitter.restoreState(vsplitstate)
            self.recent_files = settings.value('recentfiles', []) or []

        self.connect(self.menuRecent, SIGNAL('aboutToShow()'),
                     self.update_recent_file_menu)

    def _add_recent_file(self, fname):
        """Add to recent file list."""
        if not fname:
            return
        if fname in self.recent_files:
            self.recent_files.remove(fname)
        self.recent_files.insert(0, fname)
        if len(self.recent_files) > max_recent_files:
            self.recent_files.pop(-1)

    def update_recent_file_menu(self):
        """Update recent file menu"""
        recent_files = []
        for fname in self.recent_files:
            if not fname == self.filename and path.isfile(fname):
                recent_files.append(fname)
        self.menuRecent.clear()
        if recent_files:
            for i, fname in enumerate(recent_files):
                action = QAction('%d - %s' % (i+1, fname), self)
                self.connect(action, SIGNAL("triggered()"), self.load_session)
                action.setData(fname)
                self.menuRecent.addAction(action)
        self.actionClearRecent.setEnabled(len(recent_files) > 0)
        self.menuRecent.addSeparator()
        self.menuRecent.addAction(self.actionClearRecent)

    @qtsig('')
    def on_actionClearRecent_triggered(self):
        """Clear recent files list"""
        self.recent_files = []

    def set_dirty(self):
        self.setWindowModified(True)

    def select_new_panel(self, panel):
        if hasattr(self.current_panel, 'save_limits'):
            self.current_panel.save_limits()
        self.current_panel = panel
        self.stacker.setCurrentWidget(self.current_panel)

    def on_canvas_pick(self, event):
        if isinstance(self.current_panel, DatasetPanel):
            self.current_panel.on_canvas_pick(event)

    @qtsig('')
    def on_loadBtn_clicked(self):
        self.select_new_panel(self.dloader)
        self.itemList.setCurrentIndex(QModelIndex())

    @qtsig('')
    def on_removeBtn_clicked(self):
        indlist = [ind.row() for ind in self.itemList.selectedIndexes()]
        if not indlist:
            return
        if QMessageBox.question(self, 'ufit',
                                'OK to remove %d item(s)?' % len(indlist),
                                QMessageBox.Yes|QMessageBox.No) == QMessageBox.No:
            return
        new_panels = [p for i, p in enumerate(self.panels) if i not in indlist]
        self.panels[:] = new_panels
        self.itemlistmodel.reset()
        self.setWindowModified(True)
        self.on_loadBtn_clicked()

    @qtsig('')
    def on_reorderBtn_clicked(self):
        dlg = QDialog(self)
        loadUi(dlg, 'reorder.ui')
        for i, panel in enumerate(self.panels):
            QListWidgetItem('%s - %s' % (panel.index, panel.title),
                            dlg.itemList, i)
        if dlg.exec_():
            new_panels = []
            for i in range(dlg.itemList.count()):
                new_index = dlg.itemList.item(i).type()
                panel = self.panels[new_index]
                panel.index = i+1
                panel.gen_htmldesc()
                new_panels.append(panel)
            self.panels[:] = new_panels
            self.itemlistmodel.reset()
            self.setWindowModified(True)

    def on_itemList_newSelection(self):
        if self._loading:
            return
        indlist = [ind.row() for ind in self.itemList.selectedIndexes()]
        if len(indlist) == 0:
            self.on_loadBtn_clicked()
        elif len(indlist) == 1:
            panel = self.panels[indlist[0]]
            self.select_new_panel(panel)
            panel.replot(panel.get_saved_limits())
            self.toolbar.update()
            if self.inspector_window and isinstance(panel, DatasetPanel):
                self.inspector_window.setDataPanel(panel)
        else:
            self.select_new_panel(self.multiops)
            self.plot_multi()
            self.multiops.initialize([self.panels[i] for i in indlist])

    def plot_multi(self, *ignored):
        # XXX better title
        self.canvas.plotter.reset()
        indlist = [ind.row() for ind in self.itemList.selectedIndexes()]
        panels = [self.panels[i] for i in indlist]
        for p in panels:
            if not isinstance(p, DatasetPanel):
                continue
            c = self.canvas.plotter.plot_data(p.data, multi=True)
            self.canvas.plotter.plot_model(p.model, p.data, labels=False,
                                           color=c)
        self.canvas.plotter.plot_finish()
        self.canvas.draw()

    def handle_new_data(self, data, update=True, model=None):
        panel = DatasetPanel(self, self.canvas, data, model)
        self.handle_new_item(panel, update=update)

    def handle_new_item(self, panel, update=True):
        self.connect(panel, SIGNAL('dirty'), self.set_dirty)
        self.connect(panel, SIGNAL('newData'), self.handle_new_data)
        self.connect(panel, SIGNAL('updateList'), self.itemlistmodel.reset)
        panel.set_index(self.max_index)
        self.max_index += 1
        self.stacker.addWidget(panel)
        self.stacker.setCurrentWidget(panel)
        self.panels.append(panel)
        self.setWindowModified(True)
        if not self._loading and update:
            self.itemlistmodel.reset()
            self.itemList.setCurrentIndex(
                self.itemlistmodel.index(len(self.panels)-1, 0))

    @qtsig('')
    def on_actionInspector_triggered(self):
        if self.inspector_window:
            self.inspector_window.activateWindow()
            return
        self.inspector_window = InspectorWindow(self)
        self.connect(self.inspector_window, SIGNAL('dirty'), self.set_dirty)
        def deref():
            self.inspector_window = None
        self.connect(self.inspector_window, SIGNAL('closed'), deref)
        if isinstance(self.current_panel, DatasetPanel):
            self.inspector_window.setDataPanel(self.current_panel)
        self.inspector_window.show()

    @qtsig('')
    def on_actionLoadData_triggered(self):
        self.on_loadBtn_clicked()

    def on_actionConnectData_toggled(self, on):
        self.canvas.plotter.lines = on
        QMessageBox.information(self, 'Info', 'The new style will be used '
                                'the next time a plot is generated.')

    def on_actionDrawSymbols_toggled(self, on):
        self.canvas.plotter.symbols = on
        QMessageBox.information(self, 'Info', 'The new style will be used '
                                'the next time a plot is generated.')

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
        expfilename = path_to_str(filename)
        self.current_panel.export_ascii(expfilename)

    @qtsig('')
    def on_actionExportFIT_triggered(self):
        if self.filename:
            initialdir = path.dirname(self.filename)
        else:
            initialdir = ''
        filename = QFileDialog.getSaveFileName(
            self, 'Select export file name', initialdir, 'ASCII text (*.txt)')
        if filename == '':
            return False
        expfilename = path_to_str(filename)
        with open(expfilename, 'wb') as fp:
            self.current_panel.fitter.export_fits(fp)

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
        expfilename = path_to_str(filename)
        with open(expfilename, 'wb') as fp:
            self.current_panel.export_python(fp)

    @qtsig('')
    def on_actionPrint_triggered(self):
        sio = StringIO()
        self.canvas.print_figure(sio, format='svg')
        svg = QSvgRenderer(QByteArray(sio.getvalue()))
        sz = svg.defaultSize()
        aspect = sz.width()/float(sz.height())

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

    @qtsig('')
    def on_actionSavePlot_triggered(self):
        self.canvas.save_figure()

    @qtsig('')
    def on_actionUnzoom_triggered(self):
        self.toolbar.home()

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

    def clear_datasets(self):
        for panel in self.panels[:]:
            self.stacker.removeWidget(panel)
        del self.panels[:]
        self.itemlistmodel.reset()
        self.max_index = 1

    @qtsig('')
    def on_actionNewSession_triggered(self):
        if not self.check_save():
            return
        self.clear_datasets()
        self.filename = None
        self.setWindowModified(False)
        self.setWindowTitle('ufit[*]')
        self.on_loadBtn_clicked()

    @qtsig('')
    def on_actionLoad_triggered(self):
        if not self.check_save():
            return
        if self.filename:
            initialdir = path.dirname(self.filename)
        else:
            with self.sgroup as settings:
                initialdir = settings.value('loadfiledirectory', '')
        filename = QFileDialog.getOpenFileName(
            self, 'Select file name', initialdir, 'ufit files (*.ufit)')
        if filename == '':
            return
        self.filename = path_to_str(filename)
        self.load_session(self.filename)

    def load_session(self, filename=None):
        if not filename:
            # Recent files action
            action = self.sender()
            if isinstance(action, QAction):
                filename = action.data()
                self.filename = filename
        try:
            self.clear_datasets()
            info = pickle.load(open(filename, 'rb'))
            # upgrade from version 0 to 1
            if 'version' not in info and 'panels' in info:
                info['version'] = 1
                info['datasets'] = info.pop('panels')
                info['template'] = ''
            # upgrade from version 1 to 2
            if info['version'] == 1:
                datasets = info.pop('datasets')
                info['panels'] = [('dataset', d[0], d[1]) for d in datasets]
                info['version'] = 2
            self._loading = True
            try:
                for panelinfo in info['panels']:
                    panelcls = panel_types[panelinfo[0]]
                    panel = panelcls(self, self.canvas, *panelinfo[1:])
                    self.handle_new_item(panel, update=False)
                self.dloader.templateEdit.setText(info['template'])
            finally:
                self._loading = False
            self.itemlistmodel.reset()
            self.itemList.setCurrentIndex(
                self.itemlistmodel.index(len(self.panels)-1, 0))
            self.setWindowModified(False)
            self.setWindowTitle('ufit - %s[*]' % filename)
            self._add_recent_file(filename)
            with self.sgroup as settings:
                settings.setValue('loadfiledirectory', path.dirname(filename))
        except Exception, err:
            logger.exception('Loading session %r failed' % self.filename)
            QMessageBox.warning(self, 'Error', 'Loading failed: %s' % err)

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
            logger.exception('Saving session failed')
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
        self.filename = path_to_str(filename)
        try:
            self.save_session_inner(self.filename)
        except Exception, err:
            logger.exception('Saving session failed')
            QMessageBox.warning(self, 'Error', 'Saving failed: %s' % err)
            return False
        else:
            self.setWindowModified(False)
            self.setWindowTitle('ufit - %s[*]' % self.filename)
            self._add_recent_file(self.filename)
            return True

    def save_session_inner(self, filename):
        fp = open(filename, 'wb')
        info = {
            'panels': [panel.serialize() for panel in self.panels],
            'template': self.dloader.templateEdit.text(),
            'version':  SAVE_VERSION,
        }
        pickle.dump(info, fp, protocol=pickle.HIGHEST_PROTOCOL)

    @qtsig('')
    def on_actionRemoveData_triggered(self):
        self.on_removeBtn_clicked()

    @qtsig('')
    def on_actionMergeData_triggered(self):
        indlist = [ind.row() for ind in self.itemList.selectedIndexes()]
        if len(indlist) < 2:
            return
        dlg = QDialog(self)
        loadUi(dlg, 'rebin.ui')
        if dlg.exec_():
            try:
                precision = float(dlg.precisionEdit.text())
            except ValueError:
                return
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
            settings.setValue('geometry', self.saveGeometry())
            settings.setValue('windowstate', self.saveState())
            settings.setValue('splitstate', self.splitter.saveState())
            settings.setValue('vsplitstate', self.vsplitter.saveState())
            settings.setValue('recentfiles', self.recent_files)

    @qtsig('')
    def on_actionAbout_triggered(self):
        dlg = QDialog(self)
        dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        loadUi(dlg, 'about.ui')
        dlg.lbl.setText(dlg.lbl.text().replace('VERSION', __version__))
        dlg.exec_()

    @qtsig('')
    def on_backend_action_triggered(self):
        backends.set_backend(str(self.sender().text()))
