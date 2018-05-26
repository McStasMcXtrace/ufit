#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Various dialogs."""

from numpy import array, savetxt, nan

from PyQt4.QtCore import pyqtSignature as qtsig
from PyQt4.QtGui import QDialog, QListWidgetItem

from ufit.gui.common import loadUi
from ufit.data.dataset import Dataset


class ParamExportDialog(QDialog):
    def __init__(self, parent, items):
        QDialog.__init__(self, parent)
        loadUi(self, 'paramselect.ui')
        self.availList.populate(items, intersect=False)
        self.items = items

    def on_availList_itemDoubleClicked(self, item):
        QListWidgetItem(item.text(), self.selectList, item.type())

    @qtsig('')
    def on_addBtn_clicked(self):
        item = self.availList.currentItem()
        if not item:
            return
        QListWidgetItem(item.text(), self.selectList, item.type())

    @qtsig('')
    def on_removeBtn_clicked(self):
        item = self.selectList.currentItem()
        if not item:
            return
        self.selectList.takeItem(self.selectList.row(item))

    def do_export(self, filename):
        data = []
        colnames = [self.selectList.item(i).text().strip()
                    for i in range(self.selectList.count())]
        coltypes = [self.selectList.item(i).type()
                    for i in range(self.selectList.count())]
        errors = self.errorBox.isChecked()
        for item in self.items:
            drow = []
            for coltype, name in zip(coltypes, colnames):
                if coltype == 1:   # parameter
                    if name in item.model.paramdict:
                        drow.append(item.model[name].value)
                        if errors:
                            drow.append(item.model[name].error)
                    else:
                        drow.append(nan)
                        if errors:
                            drow.append(nan)
                else:    # data value
                    if name in item.data.meta:
                        drow.append(item.data.meta[name])
                    else:
                        drow.append(nan)
            data.append(drow)
        data = array(data)
        if self.headerBox.isChecked():
            header = []
            for coltype, name in zip(coltypes, colnames):
                header.append(name)
                if coltype == 1 and self.errorBox.isChecked():
                    header.append(name + '_error')
            header = '\t'.join(header)
        else:
            header = ''
        savetxt(filename, data, header=header)


class ParamSetDialog(QDialog):
    def __init__(self, parent, items):
        QDialog.__init__(self, parent)
        loadUi(self, 'paramset.ui')
        self.new_data = None
        self.items = items
        self.xaxisList.populate(items)
        self.yaxisList.populate(items)
        self._auto_name = ''

    def _gen_name(self):
        xi = self.xaxisList.currentItem()
        yi = self.yaxisList.currentItem()
        if self.nameBox.text() != self._auto_name:
            return
        auto_name = ''
        if yi:
            auto_name += yi.text().strip()
        if xi:
            auto_name += ' vs. ' + xi.text().strip()
        self._auto_name = auto_name
        self.nameBox.setText(auto_name)

    def on_xaxisList_itemSelectionChanged(self):
        self._gen_name()

    def on_yaxisList_itemSelectionChanged(self):
        self._gen_name()

    def exec_(self):
        res = QDialog.exec_(self)
        if res != QDialog.Accepted:
            return res
        xx, yy, dy = [], [], []
        xp = yp = False
        xv = self.xaxisList.currentItem().text().strip()
        if self.xaxisList.currentItem().type() == 1:
            xp = True
        yv = self.yaxisList.currentItem().text().strip()
        if self.yaxisList.currentItem().type() == 1:
            yp = True

        for item in self.items:
            if xp:
                xx.append(item.model.paramdict[xv].value)
            else:
                xx.append(item.data.meta[xv])
            if yp:
                yy.append(item.model.paramdict[yv].value)
                dy.append(item.model.paramdict[yv].error)
            else:
                yy.append(item.data.meta[yv])
                dy.append(1)
        xx, yy, dy = map(array, [xx, yy, dy])

        self.new_data = Dataset.from_arrays(str(self.nameBox.text()),
                                            xx, yy, dy, xcol=xv, ycol=yv)
        return res
