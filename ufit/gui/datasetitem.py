#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2014, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Session item for datasets and corresponding GUI."""

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QTabWidget

from ufit.models import eval_model
from ufit.gui.modelbuilder import ModelBuilder
from ufit.gui.dataops import DataOps
from ufit.gui.fitter import Fitter
from ufit.gui.session import session, SessionItem
from ufit.gui import logger


def default_model(data):
    ymin = data.y.min()
    ymaxidx = data.y.argmax()
    ymax = data.y[ymaxidx]
    xmax = data.x[ymaxidx]
    overhalf = data.x[data.y > (ymax + ymin)/2.]
    if len(overhalf) >= 2:
        xwidth = abs(overhalf[0] - overhalf[-1]) or 0.1
    else:
        xwidth = 0.1
    new_model = eval_model('Background() + Gauss(\'peak\')')
    new_model.params[0].value = ymin
    new_model.params[1].value = xmax
    new_model.params[2].value = ymax-ymin
    new_model.params[3].value = xwidth
    return new_model


class DatasetItem(SessionItem):

    def __init__(self, data, model=None):
        self.data = data
        self.model = model or default_model(data)
        SessionItem.__init__(self)

    def change_model(self, model):
        self.model = model
        self.emit(SIGNAL('newModel'), model)
        session.set_dirty()

    def after_load(self):
        self.data.after_load()  # upgrade datastructures

    def __reduce__(self):
        return (self.__class__, (self.data, self.model))

    def create_panel(self, mainwindow, canvas):
        return DatasetPanel(mainwindow, canvas, self)

    def update_htmldesc(self):
        title = self.data.title
        # XXX self.dataops.titleEdit.setText(title)
        self.title = title
        self.htmldesc = '<big><b>%s</b></big>' % self.index + \
            (title and ' - %s' % title or '') + \
            (self.data.environment and
             '<br>%s' % ', '.join(self.data.environment) or '') + \
            ('<br><small>%s</small>' % '<br>'.join(self.data.sources))
        session.emit(SIGNAL('itemsUpdated'))

    def export_python(self, fp):
        fp.write('from ufit.lab import *\n')
        fp.write('\n')
        self.data.export_python(fp, 'data')
        fp.write('\n')
        self.model.export_python(fp, 'model')
        fp.write('''\
## just plot current values
data.plot()
model.plot_components(data)
model.plot(data)

## to fit again use this...
#result = model.fit(data)
#result.printout()
#result.plot()

show()
''')

    def export_ascii(self, filename):
        with open(filename, 'wb') as fp:
            self.data.export_ascii(fp)


class DatasetPanel(QTabWidget):
    def __init__(self, parent, canvas, item):
        QTabWidget.__init__(self, parent)
        self.item = item
        self.dataops = DataOps(self)
        self.mbuilder = ModelBuilder(self)
        self.fitter = Fitter(self)
        self._limits = None
        self._dont_update_modeldef = False
        self.picker_widget = None

        self.connect(self.item, SIGNAL('newModel'), self.on_item_newModel)

        self.canvas = canvas
        self.dataops.initialize(item)
        self.mbuilder.initialize(item.data, item.model)
        self.fitter.initialize(item.model, item.data, fit=False)
        self.connect(self.dataops, SIGNAL('pickRequest'), self.set_picker)
        self.connect(self.dataops, SIGNAL('replotRequest'), self.plot)
        self.connect(self.dataops, SIGNAL('titleChanged'), self.item.update_htmldesc)
        self.connect(self.mbuilder, SIGNAL('newModel'), self.on_mbuilder_newModel)
        self.connect(self.mbuilder, SIGNAL('pickRequest'), self.set_picker)
        self.connect(self.fitter, SIGNAL('replotRequest'), self.plot)
        self.connect(self.fitter, SIGNAL('pickRequest'), self.set_picker)
        self.addTab(self.dataops, 'Data operations')
        self.addTab(self.mbuilder, 'Modeling')
        self.addTab(self.fitter, 'Fitting')
        self.setCurrentWidget(self.mbuilder)

    def on_mbuilder_newModel(self, model, update_modeldef=False,
                             switch_fitter=True):
        self._dont_update_modeldef = not update_modeldef
        try:
            self.item.change_model(model)
        finally:
            self._dont_update_modeldef = False
        if switch_fitter:
            self.setCurrentWidget(self.fitter)

    def on_item_newModel(self, model):
        if not self._dont_update_modeldef:
            self.mbuilder.modeldefEdit.setText(model.get_description())
        self.fitter.initialize(model, self.item.data, fit=False, keep_old=True)

    def set_picker(self, widget):
        self.picker_widget = widget

    def on_canvas_pick(self, event):
        if self.picker_widget:
            self.picker_widget.on_canvas_pick(event)

    def save_limits(self):
        self._limits = self.canvas.axes.get_xlim(), self.canvas.axes.get_ylim()

    def get_saved_limits(self):
        return self._limits

    def plot(self, limits=True, canvas=None):
        canvas = canvas or self.canvas
        plotter = canvas.plotter
        plotter.reset(limits)
        try:
            plotter.plot_data(self.item.data)
            plotter.plot_model_full(self.item.model, self.item.data)
        except Exception:
            logger.exception('Error while plotting')
        else:
            canvas.draw()
