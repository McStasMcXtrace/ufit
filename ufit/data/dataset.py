#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Base dataset class."""

import copy
import operator
from functools import reduce

from numpy import array, concatenate, ones, broadcast_arrays, savetxt, sqrt

from ufit.utils import attrdict
from ufit.data.merge import rebin, floatmerge
from ufit.plotting import DataPlotter


def sanitize_meta(meta, name):
    """
    Sanitize metadata so that keys that must always be there, are there.

    These special metadata keys, to be set by the loaders if possible, are:

    * instrument: the name of the instrument used
    * experiment: the number or short name of the experiment/proposal
    * filenumber: the file number of the data file
    * filedesc: a combination of instrument, experiment and filenumber
    * title: "title" of the data file, i.e. experiment name or sample name
    * subtitle: "scan info", normally the scan command used
    * environment: a list of "sample environment" type strings
    * datafilename: the file name when the data was loaded
    """
    if 'instrument' not in meta:
        meta.instrument = ''
    if 'experiment' not in meta:
        meta.experiment = ''
    if 'filenumber' not in meta:
        meta.filenumber = 0
    if 'title' not in meta:
        meta.title = name or str(meta.filenumber or '---')
    if 'subtitle' not in meta:
        # 'info' is the old name of 'subtitle'
        meta.subtitle = meta.get('info', '')
    if 'environment' not in meta:
        meta.environment = []
    if 'filedesc' not in meta:
        meta.filedesc = '%s:%s:%s' % (meta.instrument, meta.experiment,
                                      meta.filenumber)
    if 'datafilename' not in meta:
        meta.datafilename = ''


class DataBase(object):

    def __init__(self, meta, name='', sources=None):
        self.meta = attrdict(meta)
        sanitize_meta(self.meta, name)
        self.name = name or str(self.meta.filenumber or '---')
        self.sources = sources or [self.meta.filedesc]

    def after_load(self):
        pass

    def __getattr__(self, key):
        if key == '__setstate__':
            # pickling support
            raise AttributeError(key)
        elif key in self.meta:
            return self.meta[key]
        elif key == 'x_plot':
            # backwards compatibility
            self.x_plot = self.x
            return self.x
        raise AttributeError('no such data column or metadata: %s' % key)

    def copy(self):
        return copy.deepcopy(self)


class ScanData(DataBase):
    def __init__(self, meta, data, xcol, ycol, ncol=None, nscale=1,
                 name='', sources=None):
        DataBase.__init__(self, meta, name, sources)

        self._data = data

        self.xcol = self.xaxis = xcol
        self.x = self.x_raw = data[:, 0]
        self.x_plot = self.x

        self.ycol = self.yaxis = ycol
        self.y_raw = data[:, 1]
        self.dy_raw = data[:, 2]

        self.ncol = ncol
        self.nscale = nscale
        if ncol is not None and data.shape[1] > 3:
            self.norm_raw = data[:, 3]
            self.norm = self.norm_raw / nscale
            if nscale != 1:
                self.yaxis += ' per %s %s' % (nscale, ncol)
            else:
                self.yaxis += ' / %s' % ncol
        else:
            self.norm_raw = self.norm = ones(len(self.y_raw))

        self.y = self.y_raw / self.norm
        self.dy = self.dy_raw / self.norm

        self.reset_mask()
        self.fitmin = None
        self.fitmax = None

    def after_load(self):
        """Update internal data structures after unpickling."""
        if 'fitmin' not in self.__dict__:
            self.fitmin = self.fitmax = None
        if 'mask' not in self.__dict__:
            self.reset_mask()
        sanitize_meta(self.meta, self.name)

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
        if isinstance(x, list):
            x = array(x)
        if len(x.shape) > 1:
            multix = True
            xorig = x
            x = x[:, 0]
        data = array(broadcast_arrays(x, y, dy)).T
        ret = cls(meta or {}, data, xcol, ycol, name=name)
        if multix:
            ret.x = xorig
        return ret

    def reset_mask(self):
        # points with mask = False are masked out
        self.mask = ones(len(self.x), bool)
        self.mask[self.dy == 0] = False

    def rescale(self, const):
        self.nscale = const
        self.norm = self.norm_raw / const
        self.y = self.y_raw / self.norm
        self.dy = self.dy_raw / self.norm
        self.yaxis = self.ycol + ' / %s %s' % (const, self.ncol)

    def __repr__(self):
        return '<%s (%d points)>' % (self.name, len(self.x))

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

    def merge(self, binsize, *others, **settings):
        """Merge this dataset with others.

        The X values are redistributed into bins according to the given bin
        size.
        """
        if not others and binsize == 0:
            return self
        allsets = (self,) + others
        # copy meta from first
        new_meta = self.meta.copy()
        # copy all datapoints
        alldata = concatenate([dset._data for dset in allsets])
        # copy all columns
        for col in self.meta:
            if not col.startswith('col_'):
                continue
            new_meta[col] = concatenate([dset.meta.get(col, [])
                                         for dset in allsets])
        # merge
        if settings.get('floatmerge'):
            new_array, new_meta = floatmerge(alldata, binsize, new_meta)
        else:
            new_array, new_meta = rebin(alldata, binsize, new_meta)
        sources = sum((dset.sources for dset in allsets), [])
        # XXX hkl data is a mess
        if 'is_hkldata' in self.meta:
            concat = concatenate([dset.meta['hkle'] for dset in allsets])
            if binsize != 0:
                if len(set(dset.meta['hkle_vary'] for dset in allsets)) != 1:
                    raise Exception('datasets have differing varying dimension')
                concat = array([concat[0]]*len(new_array))
                idx = ['h', 'k', 'l', 'E'].index(self.meta['hkle_vary'])
                concat[:, idx] = new_array[:, 0]
            new_meta['hkle'] = concat
        # XXX should we merge other meta's?
        ret = self.__class__(new_meta, new_array,
                             self.xcol, self.ycol, self.ncol, self.nscale,
                             name='_'.join(d.name for d in allsets),
                             sources=sources)
        if 'is_hkldata' in self.meta:
            ret.x = ret.meta['hkle']
        return ret

    def plot(self, axes=None, symbols=True, lines=False, **kw):
        """Plot the dataset using matplotlib.

        *axes* is a matplotlib Axes object, as returned by :func:`gca()`.  If
        no axes are given, the current figure is used.

        *symbols* and *lines* control whether the data is plotted using symbols,
        lines or both.
        """
        dp = DataPlotter(axes=axes)
        dp.symbols = symbols
        dp.lines = lines
        dp.plot_data(self, **kw)

    def export_ascii(self, fp):
        savetxt(fp, array([self.x, self.y, self.dy]).T)

    def export_python(self, fp, objname='data'):
        fp.write('%s = as_data(%r, %r, %r, %r)\n' %
                 (objname, self.x, self.y, self.dy, self.name))

# compatibility name
Dataset = ScanData


class ImageData(DataBase):
    def __init__(self, meta, arr, darr, norm=None, nscale=1,
                 name='', sources=None):
        DataBase.__init__(self, meta, name, sources)

        self.arr_raw = arr
        self.darr_raw = darr
        self.nscale = nscale

        if norm:
            self.norm_raw = norm
            self.norm = norm / nscale
        else:
            self.norm_raw = self.norm = 1

        self.arr = arr / self.norm
        self.darr = darr / self.norm

        # XXX implement scaling?
        self.xaxis = 'pixels X'
        self.yaxis = 'pixels Y'

    def __reduce__(self):
        # avoid storing both arr and arr_raw in the pickle files
        return (self.__class__, (self.meta, self.arr, self.darr, self.norm,
                                 self.nscale, self.name, self.sources))

    def __add__(self, other):
        if not isinstance(other, ImageData):
            raise TypeError
        return self.__class__(self.meta, self.arr_raw + other.arr_raw,
                              sqrt(self.darr_raw**2 + other.darr_raw**2),
                              self.norm_raw + other.norm_raw,
                              self.nscale, name=self.name + '+' + other.name,
                              sources=self.sources + other.sources)

    def __subtract__(self, other):
        if not isinstance(other, ImageData):
            raise TypeError
        scaled_arr = other.arr / other.nscale * self.nscale
        scaled_darr = other.darr / other.nscale * self.nscale
        return self.__class__(self.meta, self.arr_raw - scaled_arr,
                              sqrt(self.darr_raw**2 + scaled_darr**2),
                              self.norm_raw, self.nscale,
                              name=self.name + '-' + other.name,
                              sources=self.sources + other.sources)

    def plot(self, axes=None, **kw):
        """Plot the image dataset using matplotlib.

        *axes* is a matplotlib Axes object, as returned by :func:`gca()`.  If
        no axes are given, the current figure is used.
        """
        dp = DataPlotter(axes=axes)
        dp.plot_image(self, **kw)

    def merge(self, binsize, *others, **kwds):
        return reduce(operator.add, others, self)

    def __repr__(self):
        return '<%s (%dx%d pixels)>' % (self.name, self.arr.shape[0],
                                        self.arr.shape[1])


class DataList(dict):

    def __getitem__(self, obj):
        if isinstance(obj, slice):
            return [self[i] for i in range(*obj.indices(10000))]
        return dict.__getitem__(self, obj)

    def c(self, r1, r2):
        return reduce(lambda a, b: a | b, self[r1:r2])


class DatasetList(list):

    def __getattr__(self, key):
        return array([getattr(d, key) for d in self])
