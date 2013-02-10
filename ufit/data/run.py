# ufit data "run" classes

from numpy import array, concatenate, ones, sqrt
import matplotlib.pyplot as pl

from ufit import UFitError

class Run(object):
    def __init__(self, name, colnames, data, meta, xcol, ycol,
                 ncol=None, nscale=1):
        self.name = name
        self.colnames = colnames
        self.cols = dict((cn, data[:,i]) for (i, cn) in enumerate(colnames))
        self.data = data
        self.xcol = xcol
        self.ycol = ycol
        self.ncol = ncol
        self.nscale = nscale
        self.meta = meta
        #for k in meta:
        #    setattr(self, k, meta[k])
        self.x = self[xcol]
        self.y = self[ycol]
        if ncol is not None:
            self.n = self[ncol] / nscale
        else:
            self.n = ones(len(self.y))

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
            for (x, y, n) in zip(run.x, run.y, run.n):
                xr = round(x, places)
                if xr in points:
                    points[xr] = (points[xr][0] + y, points[xr][1] + n)
                else:
                    points[xr] = (y, n)
        newcols = array([(x, y, n) for x, (y, n) in sorted(points.iteritems())])
        return Run('&'.join(d.name for d in allruns),
                   [self.xcol, self.ycol, self.ncol],
                   newcols, self.meta, self.xcol, self.ycol, self.ncol)

    def plot(self):
        pl.errorbar(self.x, self.y/self.n, sqrt(self.y)/self.n, fmt='o', ms=8)


class RunList(dict):

    def __getitem__(self, obj):
        if isinstance(obj, slice):
            return [self[i] for i in range(*obj.indices(10000))]
        return dict.__getitem__(self, obj)

    def c(self, r1, r2):
        return reduce(lambda a, b: a|b, self[r1:r2])
