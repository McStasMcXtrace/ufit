# ufit dataset classes

from numpy import array, concatenate, ones, sqrt
import matplotlib.pyplot as pl

from ufit import UFitError
from ufit.utils import attrdict


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

        self.ycol = ycol
        self.y_raw = self[ycol]

        self.ncol = ncol
        self.nscale = nscale
        if ncol is not None:
            self.norm = self[ncol] / nscale
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

    def merge(self, places, *others):
        points = {}
        allsets = (self,) + others
        for dset in allsets:
            if dset.xcol != self.xcol or dset.ycol != self.ycol:
                raise UFitError('cannot merge datasets with different x/ycols')
            for (x, y, n) in zip(dset.x, dset.y_raw, dset.norm):
                xr = round(x, places)
                if xr in points:
                    points[xr] = (points[xr][0] + y, points[xr][1] + n)
                else:
                    points[xr] = (y, n)
        newcols = array([(x, y, n) for x, (y, n) in sorted(points.iteritems())])
        return self.__class__('&'.join(d.name for d in allsets),
                              [self.xcol, self.ycol, self.ncol], newcols,
                              self.meta, self.xcol, self.ycol, self.ncol)

    def plot(self, _axes=None, title=None, xlabel=None, ylabel=None):
        if _axes is None:
            pl.figure()
            _axes = pl.gca()
        _axes.errorbar(self.x, self.y, self.dy, fmt='o', ms=8,
                       label='%s:%s:%s' % (self.meta.get('instrument', ''),
                                           self.meta.get('experiment', ''),
                                           self.name))
        _axes.set_title(title or '%s\n%s' % (self.meta.get('title', ''),
                                             self.meta.get('info', '')))
        _axes.set_xlabel(xlabel or self.xcol)
        _axes.set_ylabel(ylabel or self.ycol)
        _axes.legend(prop={'size': 'small'})


class DataList(dict):

    def __getitem__(self, obj):
        if isinstance(obj, slice):
            return [self[i] for i in range(*obj.indices(10000))]
        return dict.__getitem__(self, obj)

    def c(self, r1, r2):
        return reduce(lambda a, b: a|b, self[r1:r2])