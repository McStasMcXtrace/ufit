#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Session and session item abstraction."""

from os import path

from PyQt4.QtCore import QObject, SIGNAL

from ufit import UFitError
from ufit.utils import attrdict
from ufit.pycompat import cPickle as pickle


# current save file version
SAVE_VERSION = 3


class SessionItem(QObject):
    """Represents an "item" in the item list of a session."""

    def __init__(self):
        QObject.__init__(self)
        self.group = None
        self.index = -1
        self.title = ''
        self.htmldesc = ''

    def set_group(self, group, index):
        self.group = group
        self.index = index
        self.update_htmldesc()

    def after_load(self):
        """Do whatever is necessary to upgrade the data format."""

    def update_htmldesc(self):
        """Update self.htmldesc and self.title."""
        self.htmldesc = self.title = '(item)'

    def create_panel(self, mainwindow, canvas):
        """Create a GUI panel that represents this item."""
        raise NotImplementedError('implement create_panel')

    def __reduce__(self):
        """Need a special __reduce__ since we don't want to pickle the panel."""
        raise NotImplementedError('implement __reduce__')

    def export_python(self, filename):
        """Export item as Python code."""

    def export_ascii(self, filename):
        """Export item data as ASCII data."""

    def export_fits(self, filename):
        """Export fits as ASCII data."""


class ItemGroup(object):
    expanded = False

    def __init__(self, name):
        self.name = name
        self.items = []
        self.update_htmldesc()

    def update_htmldesc(self):
        nitems = len(self.items)
        self.htmldesc = '<img src=":/drawer.png">&nbsp;&nbsp;<b>%s</b>' \
                        ' &ndash; %d items' % (self.name, nitems)


class _Session(QObject):

    def __init__(self):
        QObject.__init__(self)
        self.filename = None
        self.groups = []
        self.all_items = set()
        self.clear()

    @property
    def dirname(self):
        if self.filename:
            return path.dirname(self.filename)
        return ''

    def clear(self):
        self.groups[:] = [ItemGroup('Default')]
        self.all_items.clear()
        self.props = attrdict()
        self.emit(SIGNAL('itemsUpdated'))
        self.emit(SIGNAL('propsUpdated'))
        self.emit(SIGNAL('dirtyChanged'), False)

    def new(self):
        self.filename = None
        self.emit(SIGNAL('filenameChanged'))
        self.clear()

    def set_filename(self, filename):
        self.filename = filename
        self.emit(SIGNAL('filenameChanged'))

    def _load_v0(self, info):
        info['version'] = 1
        info['datasets'] = info.pop('panels')
        info['template'] = ''
        self._load_v1(info)

    def _load_v1(self, info):
        info['version'] = 2
        datasets = info.pop('datasets')
        info['panels'] = [('dataset', d[0], d[1]) for d in datasets]
        self._load_v2(info)

    def _load_v2(self, info):
        info['version'] = 3
        group = ItemGroup('Default')
        info['groups'] = [group]
        panels = info.pop('panels')
        from ufit.gui.mappingitem import MappingItem
        from ufit.gui.scanitem import ScanDataItem
        for panel in panels:
            if panel[0] == 'dataset':
                group.items.append(ScanDataItem(panel[1], panel[2]))
            elif panel[0] == 'mapping':
                group.items.append(MappingItem(panel[1], panel[2]))
        info['props'] = attrdict()
        info['props'].template = info.pop('template')
        self._load_v3(info)

    def _load_v3(self, info):
        self.props = info['props']
        self.groups[:] = info['groups']

    def load(self, filename):
        self.clear()
        # unpickle everything
        with open(filename, 'rb') as fp:
            info = pickle.load(fp)
        # load with the respective method
        savever = info.get('version', 0)
        try:
            getattr(self, '_load_v%d' % savever)(info)
        except AttributeError:
            raise UFitError('save version %d not supported' % savever)
        self.filename = filename
        # reassign indices (also to regenerate descriptions)
        for group in self.groups:
            for i, item in enumerate(group.items):
                item.set_group(group, i + 1)
                item.after_load()
                self.all_items.add(item)
            group.update_htmldesc()
        # let GUI elements update from propsdata
        self.emit(SIGNAL('itemsUpdated'))
        self.emit(SIGNAL('propsUpdated'))
        self.emit(SIGNAL('filenameChanged'))

    def save(self):
        # let GUI elements update the stored propsdata
        self.emit(SIGNAL('propsRequested'))
        if self.filename is None:
            raise UFitError('session has no filename yet')
        info = {
            'version':  SAVE_VERSION,
            'groups':   self.groups,
            'props':    self.props,
        }
        with open(self.filename, 'wb') as fp:
            pickle.dump(info, fp, protocol=pickle.HIGHEST_PROTOCOL)
        self.emit(SIGNAL('dirtyChanged'), False)

    def add_group(self, name):
        group = ItemGroup(name)
        self.groups.append(group)
        self.set_dirty()
        self.emit(SIGNAL('groupAdded'), group)
        return group

    def remove_group(self, group):
        self.groups.remove(group)
        for item in group.items:
            self.all_items.discard(item)
        self.set_dirty()
        self.emit(SIGNAL('itemsUpdated'))

    def rename_group(self, group, name):
        group.name = name
        group.update_htmldesc()
        self.set_dirty()
        self.emit(SIGNAL('groupUpdated'), group)

    def add_item(self, item, group=None):
        if group is None:
            group = self.groups[-1]
        self.all_items.add(item)
        group.items.append(item)
        group.update_htmldesc()
        item.set_group(group, len(group.items))
        self.set_dirty()
        self.emit(SIGNAL('itemAdded'), item)

    def add_items(self, items, group=None):
        if not items:
            return
        if group is None:
            group = self.groups[-1]
        self.all_items.update(items)
        for item in items:
            group.items.append(item)
            item.set_group(group, len(group.items))
        group.update_htmldesc()
        self.set_dirty()
        self.emit(SIGNAL('itemsUpdated'))
        self.emit(SIGNAL('itemAdded'), items[-1])

    def remove_items(self, items):
        renumber_groups = set()
        for item in items:
            renumber_groups.add(item.group)
            item.group.items.remove(item)
            self.all_items.discard(item)
        for group in renumber_groups:
            if not group.items:
                self.groups.remove(group)
            for i, item in enumerate(group.items):
                item.set_group(group, i + 1)
            group.update_htmldesc()
        self.set_dirty()
        self.emit(SIGNAL('itemsUpdated'))

    def move_items(self, items, newgroup):
        renumber_groups = set([newgroup])
        for item in items:
            renumber_groups.add(item.group)
            item.group.items.remove(item)
            newgroup.items.append(item)
        for group in renumber_groups:
            for i, item in enumerate(group.items):
                item.set_group(group, i + 1)
            group.update_htmldesc()
        self.set_dirty()
        self.emit(SIGNAL('itemsUpdated'))

    def copy_items(self, items, newgroup):
        from ufit.gui.scanitem import ScanDataItem
        for item in items:
            new_data = item.data.copy()
            new_model = item.model.copy()
            new_item = ScanDataItem(new_data, new_model)
            self.all_items.add(new_item)
            newgroup.items.append(new_item)
            newgroup.update_htmldesc()
            new_item.set_group(newgroup, len(newgroup.items))
        self.set_dirty()
        self.emit(SIGNAL('itemsUpdated'))
        self.emit(SIGNAL('itemAdded'), items[-1])

    def reorder_groups(self, new_structure):
        del self.groups[:]
        for group, items in new_structure:
            self.groups.append(group)
            group.items[:] = items
            for i, item in enumerate(items):
                item.set_group(group, i + 1)
            group.update_htmldesc()
        self.set_dirty()
        self.emit(SIGNAL('itemsUpdated'))

    def set_dirty(self):
        self.emit(SIGNAL('dirtyChanged'), True)

# one singleton instance
session = _Session()

# one temporary instance
temp_session = _Session()
