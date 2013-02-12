#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Base dataset class."""

from numpy import array, concatenate, ones, sqrt

from ufit.utils import attrdict
from ufit.data.merge import rebin
from ufit.plotting import DataPlotter


class Dataset(object):
    def __init__(self, colnames, data, meta, xcol, ycol,
                 ncol=None, nscale=1, name='', sources=None):
        self.colnames = colnames
        self.cols = dict((cn, data[:,i]) for (i, cn) in enumerate(colnames))
        self.data = data
        self.meta = attrdict(meta)
        self.name = name or str(self.meta.get('filenumber', ''))
        self.full_name = '%s:%s:%s' % (self.meta.get('instrument', ''),
                                       self.meta.get('experiment', ''),
                                       self.name)
        self.sources = sources or [self.full_name]

        self.xcol = xcol
        self.x = self[xcol]
        self.xaxis = xcol

        self.ycol = ycol
        self.y_raw = self[ycol]
        self.yaxis = ycol

        self.ncol = ncol
        self.nscale = nscale
        if ncol is not None:
            self.norm_raw = self[ncol]
            self.norm = self[ncol] / nscale
            if nscale != 1:
                self.yaxis += ' / %s %s' % (nscale, ncol)
            else:
                self.yaxis += ' / %s' % ncol
        else:
            self.norm = ones(len(self.y_raw))

        self.indices = ones(len(self.x), bool)

        self.y = self.y_raw/self.norm
        self.dy = sqrt(self.y_raw)/self.norm
        self.dy[self.dy==0] = 0.1

    @property
    def environment(self):
        s = []
        if 'temperature' in self.meta:
            s.append('T = %.3f K' % self.meta['temperature'])
        return ', '.join(s)

    @property
    def data_title(self):
        return self.meta.get('title', '')

    @classmethod
    def from_arrays(cls, name, x, y, dy, meta=None, xcol='x', ycol='y'):
        arr = array((x, y)).T
        obj = cls([xcol, ycol], arr, meta or {}, xcol, ycol, name=name)
        obj.dy = dy
        return obj

    def __repr__(self):
        return '<%s (%d points)>' % (self.name, len(self.x))

    def __getattr__(self, key):
        if key == '__setstate__':
            # pickling support
            raise AttributeError
        if key in self.cols:
            return self.cols[key]
        elif key in self.meta:
            return self.meta[key]
        raise AttributeError('no such data column: %s' % key)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.__class__(self.colnames, self.data[key], self.meta,
                                  self.xcol, self.ycol, self.ncol, name=self.name)
        elif key in self.cols:
            return self.cols[key]
        raise KeyError('no such data column: %s' % key)

    def __or__(self, other):
        return self.__class__(self.colnames,
                              concatenate((self.data, other.data)),
                              self.meta,
                              self.xcol, self.ycol, self.ncol,
                              name=self.name + '|' + other.name)

    def merge(self, binsize, *others):
        allsets = (self,) + others
        all_x = concatenate([dset.x for dset in allsets])
        all_y = concatenate([dset.y_raw for dset in allsets])
        all_n = concatenate([dset.norm_raw for dset in allsets])
        new_array = rebin(all_x, all_y, all_n, binsize)
        sources = sum((dset.sources for dset in allsets), [])
        # XXX should we merge meta's?
        return self.__class__([self.xcol, self.ycol, self.ncol], new_array,
                               self.meta, self.xcol, self.ycol, self.ncol,
                               self.nscale,
                               name='&'.join(d.name for d in allsets),
                               sources=sources)

    def plot(self, _axes=None):
        DataPlotter(_axes).plot_data(self)


class DataList(dict):

    def __getitem__(self, obj):
        if isinstance(obj, slice):
            return [self[i] for i in range(*obj.indices(10000))]
        return dict.__getitem__(self, obj)

    def c(self, r1, r2):
        return reduce(lambda a, b: a|b, self[r1:r2])
