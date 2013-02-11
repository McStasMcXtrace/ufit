# ufit full GUI window

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QMainWindow, QVBoxLayout, QApplication, QTabWidget, QFrame

from ufit.models import Background
from ufit.gui.common import MPLCanvas, MPLToolbar, loadUi
from ufit.gui.dataloader import DataLoader
from ufit.gui.modelbuilder import ModelBuilder
from ufit.gui.fitter import Fitter
from ufit.gui.datalist import DataListModel, DataListDelegate


class DatasetPanel(QTabWidget):
    def __init__(self, parent, canvas, data):
        QTabWidget.__init__(self, parent)
        self.data = data
        self.model = Background()
        self._limits = None

        self.canvas = canvas
        self.mbuilder = ModelBuilder(self, canvas)
        self.fitter = Fitter(self, canvas)
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

        self.current_panel = None
        self.panels = {}

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

        self.datalistmodel = DataListModel()
        self.datalistmodel.panels.append(('<h3>Load data</h3>', self.dloader))

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
        indlist = [ind.row() for ind in self.datalist.selectedIndexes()]
        if 0 in indlist:
            self.datalist.setCurrentIndex(self.datalistmodel.index(0,0))
            self.select_new_panel(self.dloader)
        elif len(indlist) == 1:
            panel = self.datalistmodel.panels[indlist[0]][1]
            self.select_new_panel(panel)
            panel.replot()
            self.toolbar.update()
        else:
            panels = [self.datalistmodel.panels[i][1] for i in indlist]
            self.canvas.axes.clear()
            # XXX select same color for data+fit, cycle markersx
            for p in panels:
                p.model.plot(p.data, _axes=self.canvas.axes, labels=False)
            self.canvas.draw()
            self.select_new_panel(self.empty)

    def handle_new_data(self, data):
        panel = DatasetPanel(self, self.canvas, data)
        self.stacker.addWidget(panel)
        self.stacker.setCurrentWidget(panel)
        self.datalistmodel.panels.append(
            ('<big><b>%s</b></big> - %s<br>%s<br><small>%s</small>' %
             (len(self.datalistmodel.panels),
              data.data_title,
              data.environment,
              '<br>'.join(data.sources)), panel))
        self.datalistmodel.reset()
        self.datalist.setCurrentIndex(self.datalistmodel.index(len(self.datalistmodel.panels)-1,0))

    def handle_new_model(self, model):
        self.fitter.initialize(model, self.dloader.last_data, fit=False)
        self.tabber.setCurrentIndex(2)


def main(args):
    app = QApplication([])
    win = UFitMain()

    if args:
        datafile = args[0]
        win.dloader.set_template(datafile)

    win.show()
    app.exec_()
