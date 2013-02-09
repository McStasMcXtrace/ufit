# ufit data run classes

from numpy import concatenate

class Run(object):
    def __init__(self, name, colnames, data, x=None, meta=None):
        self.name = name
        self.colnames = colnames
        self.cols = dict((cn, data[:,i]) for (i, cn) in enumerate(colnames))
        self.data = data
        self.x = x
        self.meta = meta
        for k in meta:
            setattr(self, k, meta[k])
        if x is not None:
            self.X = getattr(self, x)

    def __repr__(self):
        return '<%s (%d points)>' % (self.name, len(self.X))

    def __getattr__(self, key):
        if key in self.cols:
            return self.cols[key]
        raise AttributeError('no such data column: %s' % key)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return Run(self.name,
                       self.colnames,
                       self.data[key],
                       self.x,
                       self.meta)
        return self.cols[key]

    def __or__(self, other):
        return Run(self.name + '|' + other.name,
                   self.colnames,
                   concatenate((self.data, other.data)),
                   self.x,
                   self.meta,
                   )


class RunList(dict):

    def __getitem__(self, obj):
        if isinstance(obj, slice):
            return [self[i] for i in range(*obj.indices(10000))]
        return dict.__getitem__(self, obj)

    def c(self, r1, r2):
        return reduce(lambda a, b: a|b, self[r1:r2])
