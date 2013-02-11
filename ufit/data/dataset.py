# ufit dataset classes

from numpy import array, concatenate, ones, sqrt
import matplotlib.pyplot as pl

from ufit import UFitError
from ufit.utils import attrdict
from ufit.data.merge import rebin


class Dataset(object):
    def __init__(self, name, colnames, data, meta, xcol, ycol,
                 ncol=None, nscale=1):
        self.name = name
        self.colnames = colnames
        self.cols = dict((cn, data[:,i]) for (i, cn) in enumerate(colnames))
        self.data = data
        self.meta = attrdict(meta)

        self.xcol = xcol
        self.x = self[xcol]
        self.xaxis = xcol

        self.ycol = ycol
        self.y_raw = self[ycol]
        self.yaxis = ycol

        self.ncol = ncol
        self.nscale = nscale
        if ncol is not None:
            self.norm = self[ncol] / nscale
            if nscale != 1:
                self.yaxis += ' / %s %s' % (nscale, ncol)
            else:
                self.yaxis += ' / %s' % ncol
        else:
            self.norm = ones(len(self.y_raw))

        self.y = self.y_raw/self.norm
        self.dy = sqrt(self.y_raw)/self.norm
        self.dy[self.dy==0] = 0.1

    @classmethod
    def from_arrays(cls, name, x, y, dy, meta=None, xcol='x', ycol='y'):
        arr = array((x, y)).T
        obj = cls(name, [xcol, ycol], arr, meta or {}, xcol, ycol)
        obj.dy = dy
        return obj

    def __repr__(self):
        return '<%s (%d points)>' % (self.name, len(self.x))

    def __getattr__(self, key):
        if key in self.cols:
            return self.cols[key]
        elif key in self.meta:
            return self.meta[key]
        raise AttributeError('no such data column: %s' % key)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.__class__(self.name, self.colnames,
                                  self.data[key], self.meta,
                                  self.xcol, self.ycol, self.ncol)
        elif key in self.cols:
            return self.cols[key]
        raise KeyError('no such data column: %s' % key)

    def __or__(self, other):
        return self.__class__(self.name + '|' + other.name,
                              self.colnames,
                              concatenate((self.data, other.data)),
                              self.meta,
                              self.xcol, self.ycol, self.ncol)

    def merge(self, binsize, *others):
        allsets = (self,) + others
        all_x = concatenate([dset.x for dset in allsets])
        all_y = concatenate([dset.y_raw for dset in allsets])
        all_n = concatenate([dset.norm for dset in allsets])
        new_array = rebin(all_x, all_y, all_n, binsize)
        # XXX should we merge meta's?
        return self.__class__('&'.join(d.name for d in allsets),
                              [self.xcol, self.ycol, self.ncol], new_array,
                               self.meta, self.xcol, self.ycol, self.ncol,
                               self.nscale)

    def plot(self, _axes=None, title=None, xlabel=None, ylabel=None):
        if _axes is None:
            pl.figure()
            _axes = pl.gca()
        _axes.errorbar(self.x, self.y, self.dy, fmt='o', ms=8,
                       label='%s:%s:%s' % (self.meta.get('instrument', ''),
                                           self.meta.get('experiment', ''),
                                           self.name))
        _axes.set_title(title or '%s\n%s' % (self.meta.get('title', ''),
                                             self.meta.get('info', '')),
                        size='medium')
        _axes.set_xlabel(xlabel or self.xaxis)
        _axes.set_ylabel(ylabel or self.yaxis)
        _axes.legend(prop={'size': 'small'})
        _axes.grid()


class DataList(dict):

    def __getitem__(self, obj):
        if isinstance(obj, slice):
            return [self[i] for i in range(*obj.indices(10000))]
        return dict.__getitem__(self, obj)

    def c(self, r1, r2):
        return reduce(lambda a, b: a|b, self[r1:r2])
