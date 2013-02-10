# ufit data "run" classes

from numpy import array, concatenate, ones, sqrt
import matplotlib.pyplot as pl

from ufit import UFitError


class attrdict(dict):
    def __getattr__(self, key):
        return self[key]

class Run(object):
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
            return Run(self.name, self.colnames, self.data[key], self.meta,
                       self.xcol, self.ycol, self.ncol)
        return self.cols[key]

    def __or__(self, other):
        return Run(self.name + '|' + other.name,
                   self.colnames,
                   concatenate((self.data, other.data)),
                   self.meta,
                   self.xcol, self.ycol, self.ncol)

    def merge(self, places, *others):
        points = {}
        allruns = (self,) + others
        for run in allruns:
            if run.xcol != self.xcol or run.ycol != self.ycol:
                raise UFitError('cannot merge datasets with different x/ycols')
            for (x, y, n) in zip(run.x, run.y_raw, run.norm):
                xr = round(x, places)
                if xr in points:
                    points[xr] = (points[xr][0] + y, points[xr][1] + n)
                else:
                    points[xr] = (y, n)
        newcols = array([(x, y, n) for x, (y, n) in sorted(points.iteritems())])
        return Run('&'.join(d.name for d in allruns),
                   [self.xcol, self.ycol, self.ncol],
                   newcols, self.meta, self.xcol, self.ycol, self.ncol)

    def plot(self, _axes=None):
        if _axes is None:
            pl.figure()
            _axes = pl.gca()
        _axes.errorbar(self.x, self.y, self.dy, fmt='o', ms=8, label=self.name)
        _axes.set_xlabel(self.xcol)
        _axes.set_ylabel(self.ycol)
        _axes.legend()


class RunList(dict):

    def __getitem__(self, obj):
        if isinstance(obj, slice):
            return [self[i] for i in range(*obj.indices(10000))]
        return dict.__getitem__(self, obj)

    def c(self, r1, r2):
        return reduce(lambda a, b: a|b, self[r1:r2])
