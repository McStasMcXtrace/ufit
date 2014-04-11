#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2014, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""A list view and model for different session items in the GUI."""

# parts borrowed from M. Janoschek' nfit2 GUI

from PyQt4.QtCore import Qt, QSize, SIGNAL, QAbstractItemModel, QModelIndex
from PyQt4.QtGui import QTreeView, QStyledItemDelegate, QTextDocument, QStyle, \
    QAbstractItemView

from ufit.gui.session import session, ItemGroup


class ItemTreeView(QTreeView):

    def __init__(self, parent):
        QTreeView.__init__(self, parent)
        self.header().hide()
        #self.setRootIsDecorated(False)
        #self.setStyleSheet("QTreeView::branch { display: none; }")
        self.setItemDelegate(ItemListDelegate(self))
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

    def selectionChanged(self, selected, deselected):
        self.emit(SIGNAL('newSelection'))
        QTreeView.selectionChanged(self, selected, deselected)


class ItemListModel(QAbstractItemModel):

    def __init__(self):
        QAbstractItemModel.__init__(self)
        self.connect(session, SIGNAL('itemsUpdated'), self.reset)
        self.groups = session.groups

    def columnCount(self, parent=QModelIndex()):
        return 1

    def rowCount(self, index=QModelIndex()):
        if index.isValid():   # data items
            obj = index.internalPointer()
            if isinstance(obj, ItemGroup):
                return len(self.groups[index.row()].items)
            return 0
        return len(self.groups)

    def index(self, row, column, parent=QModelIndex()):
        if parent.isValid():  # data items
            group = parent.internalPointer()
            return self.createIndex(row, column, group.items[row])
        return self.createIndex(row, column, self.groups[row])

    def parent(self, index):
        obj = index.internalPointer()
        if isinstance(obj, ItemGroup):
            return QModelIndex()
        group = obj.group
        return self.createIndex(self.groups.index(group), 0, group)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        obj = index.internalPointer()
        if role == Qt.DisplayRole:
            return obj.htmldesc
        elif role == Qt.TextAlignmentRole:
            return int(Qt.AlignLeft|Qt.AlignVCenter)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                return int(Qt.AlignLeft|Qt.AlignVCenter)
            return int(Qt.AlignRight|Qt.AlignVCenter)
        if role != Qt.DisplayRole:
            return None


class ItemListDelegate(QStyledItemDelegate):

    def paint(self, painter, option, index):
        text = index.model().data(index)
        palette = self.parent().palette()
        document = QTextDocument()
        document.setDefaultFont(option.font)
        if option.state & QStyle.State_Selected:
            document.setHtml("<font color=%s>%s</font>" %
                    (palette.highlightedText().color().name(), text))
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
        text = index.model().data(index)
        document = QTextDocument()
        document.setDefaultFont(option.font)
        document.setHtml(text)
        return QSize(document.idealWidth(), int(document.size().height()))
