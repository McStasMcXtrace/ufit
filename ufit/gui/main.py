#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2014, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Main window for the standalone GUI."""

from os import path

from PyQt4.QtCore import pyqtSignature as qtsig, Qt, SIGNAL, QModelIndex, \
    QByteArray
from PyQt4.QtGui import QMainWindow, QVBoxLayout, QMessageBox, QMenu, QIcon, \
    QFileDialog, QDialog, QAction, QActionGroup, QInputDialog, QSplitter, QLabel

from ufit import backends, __version__
from ufit.data.dataset import ScanData, ImageData
from ufit.gui import logger
from ufit.gui.common import MPLCanvas, MPLToolbar, SettingGroup, loadUi, \
    path_to_str
from ufit.gui.dialogs import ParamExportDialog
from ufit.gui.dataloader import DataLoader
from ufit.gui.itemlist import ItemListModel
from ufit.gui.inspector import InspectorWindow
from ufit.gui.annotations import AnnotationWindow
from ufit.gui.scanitem import ScanDataPanel, ScanDataItem
from ufit.gui.imageitem import ImageDataItem
from ufit.gui.session import session, SessionItem, ItemGroup

max_recent_files = 6


class UFitMain(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        self.itempanels = {}
        self.multipanels = {}
        self.current_panel = None
        self.inspector_window = None
        self.annotation_window = None

        self.sgroup = SettingGroup('main')
        loadUi(self, 'main.ui')

        self.connect(self.menuRecent, SIGNAL('aboutToShow()'),
                     self.on_menuRecent_aboutToShow)
        self.menuMoveToGroup = QMenu('Move selected to group', self)
        self.menuMoveToGroup.setIcon(QIcon(':/drawer-open.png'))
        self.connect(self.menuMoveToGroup, SIGNAL('aboutToShow()'),
                     self.on_menuMoveToGroup_aboutToShow)
        self.menuRemoveGroup = QMenu('Remove group', self)
        self.menuRemoveGroup.setIcon(QIcon(':/drawer--minus.png'))
        self.connect(self.menuMoveToGroup, SIGNAL('aboutToShow()'),
                     self.on_menuRemoveGroup_aboutToShow)

        # populate plot view
        layout2 = QVBoxLayout()
        layout2.setContentsMargins(0, 0, 0, 0)
        self.canvas = MPLCanvas(self)
        self.canvas.mpl_connect('button_press_event', self.on_canvas_pick)
        self.canvas.mpl_connect('pick_event', self.on_canvas_pick)
        self.toolbar = MPLToolbar(self.canvas, self)
        self.toolbar.setObjectName('mainplottoolbar')
        self.connect(self.toolbar, SIGNAL('popoutRequested'),
                     self.on_actionPopOut_triggered)
        self.addToolBar(self.toolbar)
        layout2.addWidget(self.canvas)
        self.plotframe.setLayout(layout2)

        # session events
        self.connect(session, SIGNAL('itemsUpdated'),
                     self.on_session_itemsUpdated)
        self.connect(session, SIGNAL('itemAdded'), self.on_session_itemAdded)
        self.connect(session, SIGNAL('filenameChanged'),
                     self.on_session_filenameChanged)
        self.connect(session, SIGNAL('dirtyChanged'),
                     self.on_session_dirtyChanged)

        # create data loader
        self.dloader = DataLoader(self, self.canvas.plotter)
        self.connect(self.dloader, SIGNAL('newDatas'), self.on_dloader_newDatas)
        self.stacker.addWidget(self.dloader)
        self.current_panel = self.dloader

        # create item model
        self.itemlistmodel = ItemListModel()
        self.itemTree.setModel(self.itemlistmodel)
        self.itemlistmodel.reset()
        self.itemTree.addAction(self.actionMergeData)
        self.itemTree.addAction(self.actionRemoveData)
        self.itemTree.addAction(self.menuMoveToGroup.menuAction())
        self.connect(self.itemTree, SIGNAL('newSelection'),
                     self.on_itemTree_newSelection)

        # backend selector
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

        # manage button
        menu = QMenu(self)
        menu.addAction(self.actionMergeData)
        menu.addAction(self.actionRemoveData)
        menu.addAction(self.actionReorder)
        menu.addSeparator()
        menu.addAction(self.actionNewGroup)
        menu.addMenu(self.menuMoveToGroup)
        menu.addMenu(self.menuRemoveGroup)
        self.manageBtn.setMenu(menu)

        # restore window state
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

    def on_dloader_newDatas(self, datas, ingroup):
        for group in session.groups:
            if group.name == ingroup:
                break
        else:
            group = session.add_group(ingroup)
        items = []
        for data in datas:
            if isinstance(data, ScanData):
                items.append(ScanDataItem(data))
            elif isinstance(data, ImageData):
                items.append(ImageDataItem(data))
            else:
                logger.warning('unknown data type: %s' % data)
        session.add_items(items, group)

    def on_session_itemsUpdated(self):
        # remove all panels whose item has vanished
        for item, panel in self.itempanels.items():
            if item not in session.all_items:
                self.stacker.removeWidget(panel)
                del self.itempanels[item]

    def on_session_itemAdded(self, item):
        # a single item has been added, show it
        self.itemTree.setCurrentIndex(self.itemlistmodel.index_for_item(item))

    def on_session_filenameChanged(self):
        if session.filename:
            self.setWindowTitle('ufit - %s[*]' % session.filename)
            self._add_recent_file(session.filename)
        else:
            self.setWindowTitle('ufit[*]')

    def on_session_dirtyChanged(self, dirty):
        self.setWindowModified(dirty)

    def _add_recent_file(self, fname):
        """Add to recent file list."""
        if not fname:
            return
        if fname in self.recent_files:
            self.recent_files.remove(fname)
        self.recent_files.insert(0, fname)
        if len(self.recent_files) > max_recent_files:
            self.recent_files.pop(-1)

    def on_menuRecent_aboutToShow(self):
        """Update recent file menu"""
        recent_files = []
        for fname in self.recent_files:
            if fname != session.filename and path.isfile(fname):
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

    def select_new_panel(self, panel):
        if hasattr(self.current_panel, 'save_limits'):
            self.current_panel.save_limits()
        self.current_panel = panel
        self.stacker.setCurrentWidget(self.current_panel)

    def on_canvas_pick(self, event):
        if isinstance(self.current_panel, ScanDataPanel):
            self.current_panel.on_canvas_pick(event)

    @qtsig('')
    def on_loadBtn_clicked(self):
        self.select_new_panel(self.dloader)
        self.itemTree.setCurrentIndex(QModelIndex())

    @qtsig('')
    def on_actionNewGroup_triggered(self):
        name = QInputDialog.getText(self, 'ufit', 'Please enter a name '
                                    'for the new group:')[0]
        if not name:
            return
        session.add_group(name)

    def on_menuMoveToGroup_aboutToShow(self):
        self.menuMoveToGroup.clear()
        for group in session.groups:
            action = QAction(group.name, self)
            def move_to(group=group):
                items = self.selected_items()
                if not items:
                    return
                session.move_items(items, group)
                self.itemTree.expandAll()
            self.connect(action, SIGNAL('triggered()'), move_to)
            self.menuMoveToGroup.addAction(action)

    def on_menuRemoveGroup_aboutToShow(self):
        self.menuRemoveGroup.clear()
        for group in session.groups:
            action = QAction(group.name, self)
            def remove(group=group):
                session.remove_group(group)
                self.itemTree.expandAll()
            self.connect(action, SIGNAL('triggered()'), remove)
            self.menuRemoveGroup.addAction(action)

    @qtsig('')
    def on_actionRemoveData_triggered(self):
        items = self.selected_items()
        if not items:
            return
        if QMessageBox.question(self, 'ufit',
                                'OK to remove %d item(s)?' % len(items),
                                QMessageBox.Yes|QMessageBox.No) == QMessageBox.No:
            return
        session.remove_items(items)
        self.itemTree.expandAll()

    @qtsig('')
    def on_actionReorder_triggered(self):
        dlg = QDialog(self)
        loadUi(dlg, 'reorder.ui')
        data2obj = dlg.itemList.populate()
        if not dlg.exec_():
            return
        new_structure = []
        for i in range(dlg.itemList.count()):
            new_index = dlg.itemList.item(i).type()
            obj = data2obj[new_index]
            if isinstance(obj, ItemGroup):
                new_structure.append((obj, []))
            else:
                if not new_structure:
                    QMessageBox.warning(self, 'ufit',
                                        'Reordering invalid: every data item '
                                        'must be below a group')
                    return
                new_structure[-1][1].append(obj)
        session.reorder_groups(new_structure)
        self.itemTree.expandAll()

    def selected_items(self, itemcls=SessionItem):
        """Return a list of selected items that belong to the given class."""
        items = (index.internalPointer()
                 for index in self.itemTree.selectedIndexes())
        if not itemcls:
            # This will also return ItemGroup objects!
            return list(items)
        return [item for item in items if isinstance(item, itemcls)]

    def on_itemTree_newSelection(self):
        items = self.selected_items(None)
        if len(items) == 1 and isinstance(items[0], ItemGroup):
            # a group is selected -- act as if we selected all items
            items = items[0].items
        if len(items) == 0:
            self.on_loadBtn_clicked()
        elif len(items) == 1:
            item = items[0]
            if item not in self.itempanels:
                panel = self.itempanels[item] = \
                        item.create_panel(self, self.canvas)
                self.stacker.addWidget(panel)
            else:
                panel = self.itempanels[item]
            self.select_new_panel(panel)
            panel.plot(panel.get_saved_limits())
            self.toolbar.update()
            if self.inspector_window and isinstance(item, ScanDataItem):
                self.inspector_window.setDataset(item.data)
        else:
            paneltype = type(items[0])
            if paneltype not in self.multipanels:
                panel = self.multipanels[paneltype] = \
                        items[0].create_multi_panel(self, self.canvas)
                self.stacker.addWidget(panel)
            else:
                panel = self.multipanels[paneltype]
            panel.initialize(items)
            self.select_new_panel(panel)
            panel.plot()

    @qtsig('')
    def on_actionInspector_triggered(self):
        if self.inspector_window:
            self.inspector_window.activateWindow()
            return
        self.inspector_window = InspectorWindow(self)
        def deref():
            self.inspector_window = None
        self.connect(self.inspector_window, SIGNAL('replotRequest'),
                     lambda: self.current_panel.plot(True))
        self.connect(self.inspector_window, SIGNAL('closed'), deref)
        if isinstance(self.current_panel, ScanDataPanel):
            self.inspector_window.setDataset(self.current_panel.item.data)
        self.inspector_window.show()

    @qtsig('')
    def on_actionAnnotations_triggered(self):
        if self.annotation_window:
            self.annotation_window.activateWindow()
            return
        self.annotation_window = AnnotationWindow(self)
        def deref():
            self.annotation_window = None
        self.connect(self.annotation_window, SIGNAL('closed'), deref)
        self.annotation_window.show()

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

    def _get_export_filename(self, filter='ASCII text (*.txt)'):
        initialdir = session.props.get('lastexportdir', session.dirname)
        filename = QFileDialog.getSaveFileName(
            self, 'Select export file name', initialdir, filter)
        if filename == '':
            return ''
        expfilename = path_to_str(filename)
        session.props.lastexportdir = path.dirname(expfilename)
        return expfilename

    @qtsig('')
    def on_actionExportASCII_triggered(self):
        expfilename = self._get_export_filename()
        if expfilename:
            self.current_panel.export_ascii(expfilename)

    @qtsig('')
    def on_actionExportFIT_triggered(self):
        expfilename = self._get_export_filename()
        if expfilename:
            self.current_panel.export_fits(expfilename)

    @qtsig('')
    def on_actionExportPython_triggered(self):
        expfilename = self._get_export_filename('Python files (*.py)')
        if expfilename:
            self.current_panel.export_python(expfilename)

    @qtsig('')
    def on_actionExportParams_triggered(self):
        items = self.selected_items(ScanDataItem)
        dlg = ParamExportDialog(self, items)
        if dlg.exec_() != QDialog.Accepted:
            return
        expfilename = self._get_export_filename()
        if expfilename:
            try:
                dlg.do_export(expfilename)
            except Exception, e:
                logger.exception('While exporting parameters')
                QMessageBox.warning(self, 'Error', 'Could not export '
                                    'parameters: %s' % e)

    @qtsig('')
    def on_actionPrint_triggered(self):
        self.canvas.print_()

    @qtsig('')
    def on_actionPopOut_triggered(self):
        new_win = QMainWindow()
        canvas = MPLCanvas(new_win)
        toolbar = MPLToolbar(canvas, new_win)
        new_win.addToolBar(toolbar)
        splitter = QSplitter(Qt.Vertical, new_win)
        splitter.addWidget(canvas)
        try:
            from ufit.gui.console import QIPythonWidget
        except ImportError:
            lbl = QLabel('Please install IPython with qtconsole to '
                         'activate the console part of this window.', new_win)
            splitter.addWidget(lbl)
        else:
            iw = QIPythonWidget('interactive pylab plotting prompt', new_win)
            iw.pushVariables({'ax': canvas.axes})
            iw.executeCommand('from ufit.lab import *')
            iw.executeCommand('sca(ax)')
            iw.setFocus()
            self.connect(iw, SIGNAL('redraw'), canvas.draw_idle)
            splitter.addWidget(iw)
        new_win.setCentralWidget(splitter)
        self.current_panel.plot(limits=None, canvas=canvas)
        new_win.show()

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

    @qtsig('')
    def on_actionNewSession_triggered(self):
        if not self.check_save():
            return
        session.clear()
        self.on_loadBtn_clicked()

    @qtsig('')
    def on_actionLoad_triggered(self):
        if not self.check_save():
            return
        initialdir = session.dirname
        if not initialdir:
            with self.sgroup as settings:
                initialdir = settings.value('loadfiledirectory', '')
        filename = QFileDialog.getOpenFileName(
            self, 'Select file name', initialdir, 'ufit files (*.ufit)')
        if filename == '':
            return
        self.load_session(path_to_str(filename))

    def load_session(self, filename=None):
        if not filename:
            # Recent files action
            action = self.sender()
            if isinstance(action, QAction):
                filename = action.data()
        try:
            session.load(filename)
            with self.sgroup as settings:
                settings.setValue('loadfiledirectory', path.dirname(filename))
        except Exception, err:
            logger.exception('Loading session %r failed' % filename)
            QMessageBox.warning(self, 'Error', 'Loading failed: %s' % err)
        else:
            self.itemTree.expandAll()
            # if there are annotations, show the window automatically
            if session.props.get('annotations'):
                self.on_actionAnnotations_triggered()

    @qtsig('')
    def on_actionSave_triggered(self):
        self.save_session()

    @qtsig('')
    def on_actionSaveAs_triggered(self):
        self.save_session_as()

    def save_session(self):
        if session.filename is None:
            return self.save_session_as()
        try:
            session.save()
        except Exception, err:
            logger.exception('Saving session failed')
            QMessageBox.warning(self, 'Error', 'Saving failed: %s' % err)
            return False
        return True

    def save_session_as(self):
        initialdir = session.dirname
        filename = QFileDialog.getSaveFileName(
            self, 'Select file name', initialdir, 'ufit files (*.ufit)')
        if filename == '':
            return False
        session.set_filename(path_to_str(filename))
        try:
            session.save()
        except Exception, err:
            logger.exception('Saving session failed')
            QMessageBox.warning(self, 'Error', 'Saving failed: %s' % err)
            return False
        return True

    @qtsig('')
    def on_actionMergeData_triggered(self):
        items = self.selected_items(ScanDataItem)
        if len(items) < 2:
            return
        dlg = QDialog(self)
        loadUi(dlg, 'rebin.ui')
        if dlg.exec_():
            try:
                precision = float(dlg.precisionEdit.text())
            except ValueError:
                return
            datalist = [i.data for i in items]
            new_data = datalist[0].merge(precision, *datalist[1:])
            session.add_item(ScanDataItem(new_data), self.items[-1].group)

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
