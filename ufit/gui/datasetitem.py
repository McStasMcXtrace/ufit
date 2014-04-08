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

from ufit.gui.modelbuilder import ModelBuilder
from ufit.gui.dataops import DataOps
from ufit.gui.fitter import Fitter
from ufit.gui import logger


class DatasetPanel(QTabWidget):
    def __init__(self, parent, canvas, data, model):
        QTabWidget.__init__(self, parent)
        data.after_load()
        self.data = data
        self.dataops = DataOps(self, parent.panels)
        self.mbuilder = ModelBuilder(self)
        self.fitter = Fitter(self)
        self.model = model or self.mbuilder.default_model(data)
        self._limits = None
        self.picker_widget = None
        self.index = 0
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
        self.connect(self.mbuilder, SIGNAL('pickRequest'), self.set_picker)
        self.connect(self.fitter, SIGNAL('replotRequest'), self.replot)
        self.connect(self.fitter, SIGNAL('pickRequest'), self.set_picker)
        self.connect(self.fitter, SIGNAL('dirty'), self.set_dirty)
        self.addTab(self.dataops, 'Data operations')
        self.addTab(self.mbuilder, 'Modeling')
        self.addTab(self.fitter, 'Fitting')
        self.setCurrentWidget(self.mbuilder)

    def set_index(self, index):
        self.index = index
        self.gen_htmldesc()

    def serialize(self):
        return ('dataset', self.data, self.model)

    def update_htmldesc(self):
        self.gen_htmldesc()
        self.emit(SIGNAL('updateList'))

    def gen_htmldesc(self):
        title = self.data.title
        self.dataops.titleEdit.setText(title)
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

    def on_mbuilder_newModel(self, model, switch_fitter=True):
        self.handle_new_model(model, update_mbuilder=False,
                              switch_fitter=switch_fitter)
        self.set_dirty()

    def handle_new_data(self, *args):
        self.emit(SIGNAL('newData'), *args)

    def handle_new_model(self, model, update_mbuilder=True,
                         keep_paramvalues=True, switch_fitter=True):
        if update_mbuilder:
            self.mbuilder.modeldefEdit.setText(model.get_description())
        self.model = model
        self.fitter.initialize(self.model, self.data, fit=False,
                               keep_old=keep_paramvalues)
        if switch_fitter:
            self.setCurrentWidget(self.fitter)

    def set_picker(self, widget):
        self.picker_widget = widget

    def on_canvas_pick(self, event):
        if self.picker_widget:
            self.picker_widget.on_canvas_pick(event)

    def save_limits(self):
        self._limits = self.canvas.axes.get_xlim(), self.canvas.axes.get_ylim()

    def get_saved_limits(self):
        return self._limits

    def replot(self, limits=True, paramvalues=None):
        plotter = self.canvas.plotter
        plotter.reset(limits)
        try:
            plotter.plot_data(self.data)
            plotter.plot_model_full(self.model, self.data,
                                    paramvalues=paramvalues)
        except Exception:
            logger.exception('Error while plotting')
        else:
            self.canvas.draw()

    def export_ascii(self, filename):
        with open(filename, 'wb') as fp:
            self.data.export_ascii(fp)

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
