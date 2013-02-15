#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""A list view and model for different datasets in the GUI."""

# parts borrowed from M. Janoschek' nfit2 GUI

from PyQt4.QtCore import Qt, QVariant, QSize, QString, SIGNAL, \
     QAbstractListModel, QModelIndex
from PyQt4.QtGui import QListView, QStyledItemDelegate, QTextDocument, QStyle, \
     QAbstractItemView


class DataListView(QListView):

    def __init__(self, parent):
        QListView.__init__(self, parent)
        self.setItemDelegate(DataListDelegate(self))
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

    def selectionChanged(self, selected, deselected):
        self.emit(SIGNAL('newSelection'))
        QListView.selectionChanged(self, selected, deselected)


class DataListModel(QAbstractListModel):

    def __init__(self, panels):
        QAbstractListModel.__init__(self)
        self.panels = panels

    def rowCount(self, index=QModelIndex()):
        return len(self.panels)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.panels)):
            return QVariant()
        nr = index.row()
        if role == Qt.DisplayRole:
            return QVariant(self.panels[nr].as_html())
        elif role == Qt.TextAlignmentRole:
            return QVariant(int(Qt.AlignLeft|Qt.AlignVCenter))
        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                return QVariant(int(Qt.AlignLeft|Qt.AlignVCenter))
            return QVariant(int(Qt.AlignRight|Qt.AlignVCenter))
        if role != Qt.DisplayRole:
            return QVariant()


class DataListDelegate(QStyledItemDelegate):

    def paint(self, painter, option, index):
        text = index.model().data(index).toString()
        palette = self.parent().palette()
        document = QTextDocument()
        document.setDefaultFont(option.font)
        if option.state & QStyle.State_Selected:
            document.setHtml(QString("<font color=%1>%2</font>")
                    .arg(palette.highlightedText().color().name())
                    .arg(text))
            color = palette.highlight().color()
        else:
            document.setHtml(text)
            color = palette.base().color()
        painter.save()
        painter.fillRect(option.rect, color)
        painter.translate(option.rect.x(), option.rect.y())
        document.drawContents(painter)
        painter.restore()

    def sizeHint(self, option, index):
        text = index.model().data(index).toString()
        document = QTextDocument()
        document.setDefaultFont(option.font)
        document.setHtml(text)
        return QSize(document.idealWidth(), int(document.size().height()))
