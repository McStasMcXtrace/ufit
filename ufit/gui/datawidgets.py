#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Various data display widgets for the GUI."""

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QListWidget, QListWidgetItem


class DataValueListWidget(QListWidget):
    """View of data values from some datasets."""

    def populate(self, items, intersect=True):
        allparams = set()
        alldatav = set()
        for item in items:
            if not item.model or not item.data:
                return
            pgen = (p.name for p in item.model.params)
            if not allparams:
                allparams = set(pgen)
            elif intersect:
                allparams.intersection_update(pgen)
            else:
                allparams.update(pgen)
            vgen = (v for v in item.data.meta if not v.startswith('col_'))
            if not alldatav:
                alldatav = set(vgen)
            elif intersect:
                alldatav.intersection_update(vgen)
            else:
                alldatav.update(vgen)

        wi = QListWidgetItem('Parameters', self)
        wi.setFlags(Qt.NoItemFlags)  # not selectable
        for param in sorted(allparams):
            QListWidgetItem('   ' + param, self, 1)
        wi = QListWidgetItem('Data values', self)
        wi.setFlags(Qt.NoItemFlags)
        for datav in sorted(alldatav):
            QListWidgetItem('   ' + datav, self, 2)
