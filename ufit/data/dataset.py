#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Base dataset class."""

import copy

from numpy import array, concatenate, ones, broadcast_arrays, savetxt

from ufit.utils import attrdict
from ufit.data.merge import rebin
from ufit.plotting import DataPlotter


class Dataset(object):
    def __init__(self, meta, data, xcol, ycol, ncol=None, nscale=1,
                 name='', sources=None):
        self.meta = attrdict(meta)
        self.name = name or str(self.meta.filenumber)
        self.sources = sources or [getattr(self, 'filedesc', '')]
        if 'title' not in meta:
            self.meta.title = self.name
        if 'environment' not in meta:
            self.meta.environment = ''
        self._data = data

        self.xcol = self.xaxis = xcol
        self.x = self.x_raw = data[:,0]
        self.x_plot = self.x

        self.ycol = self.yaxis = ycol
        self.y_raw = data[:,1]
        self.dy_raw = data[:,2]

        self.ncol = ncol
        self.nscale = nscale
        if ncol is not None and data.shape[1] > 3:
            self.norm_raw = data[:,3]
            self.norm = self.norm_raw / nscale
            if nscale != 1:
                self.yaxis += ' / %s %s' % (nscale, ncol)
            else:
                self.yaxis += ' / %s' % ncol
        else:
            self.norm_raw = self.norm = ones(len(self.y_raw))

        self.y = self.y_raw / self.norm
        self.dy = self.dy_raw / self.norm

        self.reset_mask()
        self.fitmin = None
        self.fitmax = None

    def copy(self):
        return copy.deepcopy(self)

    @property
    def fit_columns(self):
        mask = self.mask.copy()
        if self.fitmin is not None:
            mask &= self.x >= self.fitmin
        if self.fitmax is not None:
            mask &= self.x <= self.fitmax
        return self.x[mask], self.y[mask], self.dy[mask]

    @classmethod
    def from_arrays(cls, name, x, y, dy, meta=None, xcol='x', ycol='y'):
        multix = False
        if len(x.shape) > 1:
            multix = True
            xorig = x
            x = x[:,0]
        data = array(broadcast_arrays(x, y, dy)).T
        ret = cls(meta or {}, data, xcol, ycol, name=name)
        if multix:
            ret.x = xorig
        return ret

    def reset_mask(self):
        # points with mask = False are masked out
        self.mask = ones(len(self.x), bool)
        self.mask[self.dy==0] = False

    def __repr__(self):
        return '<%s (%d points)>' % (self.name, len(self.x))

    def __getattr__(self, key):
        if key == '__setstate__':
            # pickling support
            raise AttributeError(key)
        elif key in self.meta:
            return self.meta[key]
        raise AttributeError('no such data column: %s' % key)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.__class__(self.meta, self._data[key],
                                  self.xcol, self.ycol, self.ncol, self.nscale,
                                  name=self.name, sources=self.sources)
        return getattr(self, key)

    def __or__(self, other):
        return self.__class__(self.meta, concatenate((self._data, other._data)),
                              self.xcol, self.ycol, self.ncol, self.nscale,
                              name=self.name + '|' + other.name,
                              sources=self.sources + other.sources)

    def merge(self, binsize, *others):
        """Merge this dataset with others.

        The X values are redistributed into bins according to the given bin
        size.
        """
        if not others:
            return self
        allsets = (self,) + others
        alldata = concatenate([dset._data for dset in allsets])
        new_array = rebin(alldata, binsize)
        sources = sum((dset.sources for dset in allsets), [])
        # XXX should we merge meta's?
        return self.__class__(self.meta, new_array,
                              self.xcol, self.ycol, self.ncol, self.nscale,
                              name='_'.join(d.name for d in allsets),
                              sources=sources)

    def plot(self, axes=None, symbols=True, lines=False):
        """Plot the dataset using matplotlib.

        *axes* is a matplotlib Axes object, as returned by :func:`gca()`.  If
        no axes are given, the current figure is used.

        *symbols* and *lines* control whether the data is plotted using symbols,
        lines or both.
        """
        dp = DataPlotter(axes=axes)
        dp.symbols = symbols
        dp.lines = lines
        dp.plot_data(self)

    def export_ascii(self, fp):
        savetxt(fp, array([self.x, self.y, self.dy]).T)


class DataList(dict):

    def __getitem__(self, obj):
        if isinstance(obj, slice):
            return [self[i] for i in range(*obj.indices(10000))]
        return dict.__getitem__(self, obj)

    def c(self, r1, r2):
        return reduce(lambda a, b: a|b, self[r1:r2])


class DatasetList(list):

    def __getattr__(self, key):
        return array([getattr(d, key) for d in self])
