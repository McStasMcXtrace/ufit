#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Session item for datasets and corresponding GUI."""

from os import path

from numpy import savetxt, array, linspace, sqrt, mean

from PyQt4.QtCore import pyqtSignature as qtsig, SIGNAL
from PyQt4.QtGui import QTabWidget, QWidget, QDialog, QMessageBox

from ufit.data.merge import rebin
from ufit.param import prepare_params
from ufit.models import eval_model
from ufit.gui import logger
from ufit.gui.modelbuilder import ModelBuilder
from ufit.gui.dataops import DataOps
from ufit.gui.fitter import Fitter
from ufit.gui.session import session, SessionItem
from ufit.gui.mappingitem import MappingItem
from ufit.gui.common import loadUi
from ufit.gui.dialogs import ParamSetDialog
from ufit.pycompat import from_encoding


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


class ScanDataItem(SessionItem):

    itemtype = 'scan'

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
        return ScanDataPanel(mainwindow, canvas, self)

    def create_multi_panel(self, mainwindow, canvas):
        return MultiDataOps(mainwindow, canvas)

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

    def export_python(self, filename):
        with open(filename, 'wb') as fp:
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
        with open(filename, 'w') as fp:
            self.data.export_ascii(fp)

    def export_fits(self, filename):
        xx = linspace(self.data.x.min(), self.data.x.max(), 1000)
        paramvalues = prepare_params(self.model.params, self.data.meta)[3]
        yy = self.model.fcn(paramvalues, xx)
        yys = []
        for comp in self.model.get_components():
            if comp is self.model:
                continue
            yys.append(comp.fcn(paramvalues, xx))
        savetxt(filename, array([xx, yy] + yys).T)


class ScanDataPanel(QTabWidget):
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

    def export_ascii(self, filename):
        self.item.export_ascii(filename)

    def export_fits(self, filename):
        self.item.export_fits(filename)

    def export_python(self, filename):
        self.item.export_python(filename)


class MultiDataOps(QWidget):

    def __init__(self, parent, canvas):
        QWidget.__init__(self, parent)
        self.canvas = canvas
        self.connect(self, SIGNAL('replotRequest'), self.plot)

        loadUi(self, 'multiops.ui')

    def initialize(self, items):
        self.items = [i for i in items if isinstance(i, ScanDataItem)]
        self.datas = [i.data for i in self.items]
        self.monscaleEdit.setText(str(int(mean([d.nscale for d in self.datas]))))
        self.onemodelBox.clear()
        self.onemodelBox.addItems(['%d' % i.index for i in self.items])

    def plot(self, limits=True, canvas=None):
        canvas = canvas or self.canvas
        xlabels = set()
        ylabels = set()
        titles = set()
        canvas.plotter.reset()
        for i in self.items:
            c = canvas.plotter.plot_data(i.data, multi=True)
            canvas.plotter.plot_model(i.model, i.data, labels=False, color=c)
            xlabels.add(i.data.xaxis)
            ylabels.add(i.data.yaxis)
            titles.add(i.data.title)
        canvas.plotter.plot_finish(', '.join(xlabels), ', '.join(ylabels),
                                   from_encoding(', '.join(titles),
                                                 'ascii', 'ignore'))
        canvas.draw()

    @qtsig('')
    def on_rebinBtn_clicked(self):
        try:
            binsize = float(self.precisionEdit.text())
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Enter a valid precision.')
            return
        for data in self.datas:
            new_array = rebin(data._data, binsize)
            data.__init__(data.meta, new_array,
                          data.xcol, data.ycol, data.ncol,
                          data.nscale, name=data.name,
                          sources=data.sources)
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty()

    @qtsig('')
    def on_mulBtn_clicked(self):
        try:
            const = float(self.scaleConstEdit.text())
        except ValueError:
            return
        for data in self.datas:
            data.y *= const
            data.y_raw *= const
            data.dy *= const
            data.dy_raw *= const
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty()

    @qtsig('')
    def on_addBtn_clicked(self):
        try:
            const = float(self.addConstEdit.text())
        except ValueError:
            return
        for data in self.datas:
            data.y += const
            data.y_raw += const * data.norm
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty()

    @qtsig('')
    def on_scaleXBtn_clicked(self):
        try:
            const = float(self.scaleXConstEdit.text())
        except ValueError:
            return
        for data in self.datas:
            data.x *= const
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty()

    @qtsig('')
    def on_shiftBtn_clicked(self):
        try:
            const = float(self.shiftConstEdit.text())
        except ValueError:
            return
        for data in self.datas:
            data.x += const
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty()

    @qtsig('')
    def on_monscaleBtn_clicked(self):
        try:
            const = int(self.monscaleEdit.text())
        except ValueError:
            return
        for data in self.datas:
            data.nscale = const
            data.norm = data.norm_raw / const
            data.y = data.y_raw/data.norm
            data.dy = sqrt(data.y_raw)/data.norm
            data.yaxis = data.ycol + ' / %s %s' % (const, data.ncol)
        self.emit(SIGNAL('replotRequest'), None)
        session.set_dirty()

    @qtsig('')
    def on_mergeBtn_clicked(self):
        try:
            precision = float(self.mergeEdit.text())
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Enter a valid precision.')
            return
        new_data = self.datas[0].merge(precision, *self.datas[1:])
        session.add_item(ScanDataItem(new_data), self.items[-1].group)

    @qtsig('')
    def on_floatMergeBtn_clicked(self):
        try:
            precision = float(self.mergeEdit.text())
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Enter a valid precision.')
            return
        new_data = self.datas[0].merge(precision, floatmerge=True, *self.datas[1:])
        session.add_item(ScanDataItem(new_data), self.items[-1].group)

    @qtsig('')
    def on_onemodelBtn_clicked(self):
        which = self.onemodelBox.currentIndex()
        if which < 0:
            return
        model = self.items[which].model
        for i, item in enumerate(self.items):
            if i == which:
                continue
            item.change_model(model.copy())
        self.emit(SIGNAL('replotRequest'), None)

    @qtsig('')
    def on_fitallBtn_clicked(self):
        for item in self.items:
            res = item.model.fit(item.data)
            session.emit(SIGNAL('modelFitted'), item, res)
        self.emit(SIGNAL('replotRequest'), None)

    @qtsig('')
    def on_paramsetBtn_clicked(self):
        dlg = ParamSetDialog(self, self.items)
        if dlg.exec_() != QDialog.Accepted:
            return
        session.add_item(ScanDataItem(dlg.new_data), self.items[-1].group)

    @qtsig('')
    def on_mappingBtn_clicked(self):
        item = MappingItem([item.data for item in self.items], None)
        session.add_item(item, self.items[-1].group)

    @qtsig('')
    def on_globalfitBtn_clicked(self):
        QMessageBox.warning(self, 'Sorry', 'Not implemented yet.')

    def export_ascii(self, filename):
        base, ext = path.splitext(filename)
        for i, item in enumerate(self.items):
            item.export_ascii(base + '.%d' % i + ext)

    def export_fits(self, filename):
        base, ext = path.splitext(filename)
        for i, item in enumerate(self.items):
            item.export_fits(base + '.%d' % i + ext)

    def export_python(self, filename):
        base, ext = path.splitext(filename)
        for i, item in enumerate(self.items):
            item.export_python(base + '.%d' % i + ext)
