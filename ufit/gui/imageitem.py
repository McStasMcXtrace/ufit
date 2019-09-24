#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2019, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Session item for datasets and corresponding GUI."""

import operator
from functools import reduce

from numpy import sqrt, array, arange

from ufit.qt import pyqtSlot, QMessageBox, QTabWidget, QWidget

from matplotlib.patches import Rectangle

from ufit.data.dataset import ScanData
from ufit.gui import logger
from ufit.gui.dataops import DataOps
from ufit.gui.session import session, SessionItem
from ufit.gui.scanitem import ScanDataItem
from ufit.gui.common import loadUi


class ImageDataItem(SessionItem):

    itemtype = 'image'

    def __init__(self, data):
        self.data = data
        SessionItem.__init__(self)

    def after_load(self):
        self.data.after_load()  # upgrade datastructures

    def __reduce__(self):
        return (self.__class__, (self.data, ))

    def create_panel(self, mainwindow, canvas):
        return ImageDataPanel(mainwindow, canvas, self)

    def create_multi_panel(self, mainwindow, canvas):
        return ImageMultiPanel(mainwindow, canvas)

    def update_htmldesc(self):
        title = self.data.title
        # XXX self.dataops.titleEdit.setText(title)
        self.title = title
        htmldesc = '<img src=":/image-sunset.png">&nbsp;&nbsp;' \
            '<big><b>%s</b></big>' % self.index + \
            (title and ' - %s' % title or '') + \
            (self.data.environment and
             '<br>%s' % ', '.join(self.data.environment) or '') + \
            ('<br><small>%s</small>' % '<br>'.join(self.data.sources[:5]))
        if len(self.data.sources) > 5:
            htmldesc += '<br><small>...</small>'
        self.htmldesc = htmldesc
        session.itemsUpdated.emit()

    def export_python(self, filename):
        QMessageBox.information(self, 'Error', 'Cannot export Python from an '
                                'image.')

    def export_ascii(self, filename):
        with open(filename, 'wb') as fp:
            self.data.export_ascii(fp)

    def export_fits(self, filename):
        QMessageBox.information(self, 'Error', 'Cannot export fits from an '
                                'image.')


class ImageDataPanel(QTabWidget):

    image_limits = None

    def __init__(self, parent, canvas, item):
        QTabWidget.__init__(self, parent)
        self.item = item
        self.dataops = DataOps(self)
        self._limits = None
        self.picker_widget = None

        self.canvas = canvas
        # XXX self.dataops.initialize(item)
        self.dataops.pickRequest.connect(self.set_picker)
        self.dataops.replotRequest.connect(self.plot)
        self.dataops.titleChanged.connect(self.item.update_htmldesc)
        self.addTab(self.dataops, 'Data operations')

    def set_picker(self, widget):
        self.picker_widget = widget

    def on_canvas_pick(self, event):
        if self.picker_widget:
            self.picker_widget.on_canvas_pick(event)

    def save_limits(self):
        # global limits for all images
        ImageDataPanel.image_limits = self.canvas.axes.get_xlim(), \
            self.canvas.axes.get_ylim()

    def get_saved_limits(self):
        return ImageDataPanel.image_limits

    def plot(self, limits=True, canvas=None):
        canvas = canvas or self.canvas
        plotter = canvas.plotter
        plotter.reset(limits)
        try:
            plotter.plot_image(self.item.data)
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


class ImageMultiPanel(QWidget):

    def __init__(self, parent, canvas):
        QWidget.__init__(self, parent)
        self.canvas = canvas
        self.boxes = []
        loadUi(self, 'imageops.ui')

    def initialize(self, items):
        self.items = [i for i in items if isinstance(i, ImageDataItem)]
        self.datas = [i.data for i in self.items]
        xparams = set()
        for data in self.datas:
            if not xparams:
                xparams.update(k for k in data.meta if isinstance(data.meta[k], float))
            xparams.intersection_update(k for k in data.meta
                                        if isinstance(data.meta[k], float))
        self.xparamBox.clear()
        xparams = ['image #'] + sorted(xparams)
        self.xparamBox.addItems(xparams)

    def plot(self, limits=True, canvas=None):
        canvas = canvas or self.canvas
        # XXX better title
        canvas.plotter.reset(ImageDataPanel.image_limits)
        sumdata = reduce(operator.add, self.datas[1:], self.datas[0])
        canvas.plotter.plot_image(sumdata)
        canvas.plotter.plot_finish(title='sum over %d images' % len(self.datas))
        for box in self.boxes:
            x1, y1, x2, y2 = box.x1Box.value(), box.y1Box.value(), \
                box.x2Box.value(), box.y2Box.value()
            canvas.plotter.axes.add_patch(
                Rectangle((x1, y1), x2-x1, y2-y1, fill=False, color='yellow'))
        canvas.draw()

    def save_limits(self):
        ImageDataPanel.image_limits = self.canvas.axes.get_xlim(), \
            self.canvas.axes.get_ylim()

    @pyqtSlot()
    def on_addboxBtn_clicked(self):
        x1, x2 = map(int, self.canvas.axes.get_xlim())
        y1, y2 = map(int, self.canvas.axes.get_ylim())
        box = QWidget(self)
        loadUi(box, 'box.ui')
        # there's always a stretcher at the bottom
        self.boxLayout.insertWidget(self.boxLayout.count()-1, box)
        self.boxes.append(box)
        box.nameBox.setText('Box %d' % len(self.boxes))
        box.x1Box.setValue(x1)
        box.x2Box.setValue(x2)
        box.y1Box.setValue(y1)
        box.y2Box.setValue(y2)

        def boxchange(v):
            self.plot(False)

        def boxremove(box=box):
            index = self.boxes.index(box)
            del self.boxes[index]
            item = self.boxLayout.takeAt(index)
            item.widget().deleteLater()
            self.plot(False)
        box.x1Box.valueChanged.connect(boxchange)
        box.x2Box.valueChanged.connect(boxchange)
        box.y1Box.valueChanged.connect(boxchange)
        box.y2Box.valueChanged.connect(boxchange)
        box.delBtn.clicked.connect(boxremove)
        self.plot(False)

    @pyqtSlot()
    def on_integrateBtn_clicked(self):
        xname = self.xparamBox.currentText()
        if xname == 'image #':
            xdata = arange(1, len(self.datas) + 1)
        else:
            xdata = array([data.meta[xname] for data in self.datas])
        boxnorm = self.boxNormBox.isChecked()
        for box in self.boxes:
            x1, y1, x2, y2 = box.x1Box.value(), box.y1Box.value(), \
                box.x2Box.value(), box.y2Box.value()
            name = box.nameBox.text()
            ydata = array([data.arr[x1:x2, y1:y2].sum()
                           for data in self.datas])
            dydata = array([sqrt((data.darr[x1:x2, y1:y2]**2).sum())
                            for data in self.datas])
            yname = 'box counts'
            if boxnorm:
                factor = 1. / ((y2 - y1) * (x2 - x1))
                ydata *= factor
                dydata *= factor
                yname = 'box counts (norm)'
            scan = ScanData.from_arrays(name, xdata, ydata, dydata,
                                        xcol=xname, ycol=yname)
            session.add_item(ScanDataItem(scan))
