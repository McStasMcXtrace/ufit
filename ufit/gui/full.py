# ufit full GUI window

import cPickle as pickle

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL
from PyQt4.QtGui import QMainWindow, QVBoxLayout, QApplication, QTabWidget, \
     QFrame, QMessageBox, QFileDialog

from ufit.models import Background, Gauss
from ufit.gui.common import MPLCanvas, MPLToolbar, loadUi
from ufit.gui.dataloader import DataLoader
from ufit.gui.modelbuilder import ModelBuilder
from ufit.gui.fitter import Fitter
from ufit.gui.datalist import DataListModel, DataListDelegate


class DatasetPanel(QTabWidget):
    def __init__(self, parent, canvas, data, model=None):
        QTabWidget.__init__(self, parent)
        self.data = data
        # XXX make a more intelligent model
        self.model = model or \
            (Background(bkgd=0) + Gauss('peak', pos=0, ampl=1, fwhm=1))
        self._limits = None

        self.canvas = canvas
        self.mbuilder = ModelBuilder(self, canvas)
        self.fitter = Fitter(self, canvas)
        # XXX restore model in modelbuilder
        self.mbuilder.initialize(self.data)
        self.fitter.initialize(self.model, self.data, fit=False)
        self.connect(self.mbuilder, SIGNAL('newModel'),
                     self.on_mbuilder_newModel)
        self.addTab(self.mbuilder, 'Model')
        self.addTab(self.fitter, 'Fit')

    def on_mbuilder_newModel(self, model):
        self.model = model
        self.fitter.initialize(self.model, self.data, fit=False)
        self.setCurrentIndex(1)

    def save_limits(self):
        self._limits = self.canvas.axes.get_xlim(), self.canvas.axes.get_ylim()

    # XXX keep this mess in one place
    def replot(self):
        self.canvas.axes.clear()
        try:
            self.model.plot(self.data, _axes=self.canvas.axes)
            self.model.plot_components(self.data, _axes=self.canvas.axes)
        except Exception:
            return
        if self._limits:
            self.canvas.axes.set_xlim(*self._limits[0])
            self.canvas.axes.set_ylim(*self._limits[1])
        self.canvas.draw()


class UFitMain(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        self._loading = False
        self.current_panel = None
        self.panels = []

        loadUi(self, 'full.ui')

        # populate plot view
        layout2 = QVBoxLayout()
        layout2.setContentsMargins(0, 0, 0, 0)
        self.canvas = MPLCanvas(self)
        self.canvas.mpl_connect('button_press_event', self.on_canvas_pick)
        self.toolbar = MPLToolbar(self.canvas, self)
        layout2.addWidget(self.toolbar)
        layout2.addWidget(self.canvas)
        self.plotframe.setLayout(layout2)

        # create data loader
        self.dloader = DataLoader(self, self.canvas)
        self.connect(self.dloader, SIGNAL('newData'), self.handle_new_data)
        self.stacker.addWidget(self.dloader)
        self.current_panel = self.dloader

        self.empty = QFrame(self)
        self.stacker.addWidget(self.empty)

        self.datalistmodel = DataListModel(self.panels)
        self.panels.append(('<h3>Load data</h3>', self.dloader))

        self.datalist.setModel(self.datalistmodel)
        self.datalist.setItemDelegate(DataListDelegate(self))
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
            self.current_panel.fitter.on_canvas_pick(event)

    def on_datalist_newSelection(self):
        if self._loading:
            return
        indlist = [ind.row() for ind in self.datalist.selectedIndexes()]
        if 0 in indlist:
            self.datalist.setCurrentIndex(self.datalistmodel.index(0,0))
            self.select_new_panel(self.dloader)
        elif len(indlist) == 1:
            panel = self.panels[indlist[0]][1]
            self.select_new_panel(panel)
            panel.replot()
            self.toolbar.update()
        else:
            panels = [self.panels[i][1] for i in indlist]
            self.canvas.axes.clear()
            # XXX select same color for data+fit, cycle markers
            for p in panels:
                p.model.plot(p.data, _axes=self.canvas.axes, labels=False)
            self.canvas.draw()
            self.select_new_panel(self.empty)

    def handle_new_data(self, data, model=None):
        panel = DatasetPanel(self, self.canvas, data, model)
        self.stacker.addWidget(panel)
        self.stacker.setCurrentWidget(panel)
        self.panels.append(
            ('<big><b>%s</b></big> - %s<br>%s<br><small>%s</small>' %
             (len(self.panels),
              data.data_title,
              data.environment,
              '<br>'.join(data.sources)), panel))
        self.datalistmodel.reset()
        self.datalist.setCurrentIndex(
            self.datalistmodel.index(len(self.panels)-1, 0))

    @qtsig('')
    def on_actionLoadData_triggered(self):
        self.datalist.setCurrentIndex(self.datalistmodel.index(0,0))

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

    @qtsig('')
    def on_actionSave_triggered(self):
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
            'panels': [(panel[1].data, panel[1].model) for panel in self.panels[1:]]
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
    print 'starting up app...'
    app = QApplication([])
    # XXX window geometry
    win = UFitMain()

    if args:
        datafile = args[0]
        if datafile.endswith('.ufit'):
            win.load_session(datafile)
        else:
            win.dloader.set_template(datafile)

    print 'loading finished, main window showing...'
    win.show()
    app.exec_()
