# ufit core

from numpy import linspace, ones


def debug(str):
    if __debug__:
        print str


class UFitError(Exception):
    pass


class Data(object):
    def __init__(self, x, y, dy, name, info=None):
        self.name = name
        self.x = x
        self.y = y
        self.info = info
        if dy is None:
            self.dy = ones(len(x))
        else:
            self.dy = dy
        if not (len(x) == len(y) == len(self.dy)):
            raise UFitError('X, Y and DY must be of same length')

    def __repr__(self):
        return '<Data %s (%d points)>' % (self.name, len(self.x))


class Param(object):
    def __init__(self, name, initializer):
        self.name = name
        self.expr = None
        self.value = 0
        self.pmin = None
        self.pmax = None
        if isinstance(initializer, tuple) and len(initializer) == 3:
            self.pmin, self.pmax, initializer = initializer
        if isinstance(initializer, (int, long, float)):
            self.value = float(initializer)
        elif isinstance(initializer, str):
            self.expr = initializer
        else:
            raise UFitError('Parameter %s should be either a number, a string '
                            'or a 3-tuple (min, max, string or number)')
        # properties set on fit result
        self.error = 0
        self.correl = {}
        # transform parameter after successful fit
        self.finalize = lambda x: x

    def __str__(self):
        s = '%-15s = %10.4g +/- %10.4g' % (
            self.name, self.value, self.error)
        if self.expr:
            s += ' (fixed: %s)' % self.expr
        return s

    def __repr__(self):
        return '<Param %s>' % self


class Result(object):
    def __init__(self, data, fcn, params, message):
        self.data = data
        self.params = params
        self.message = message

        for p in params:
            p.value = p.finalize(p.value)

        self.paramdict = dict((p.name, p.value) for p in params)
        sum_sqr = ((fcn(self.paramdict, data.x) - data.y)**2 / data.dy**2).sum()
        nfree = len(data.y) - sum(1 for p in params if not p.expr)
        self.chisqr = sum_sqr / nfree

        self.xx = linspace(data.x[0], data.x[-1], 1000)
        self.yy = fcn(self.paramdict, self.xx)

    def printout(self):
        print 'Fit results for %s' % self.data.name
        if self.message:
            print '>', self.message
        print '-' * 80
        for p in self.params:
            print p
        print '%-15s = %10.4g' % ('chi^2/NDF', self.chisqr)
        print '=' * 80

    def plot(self, title=None, xlabel=None, ylabel=None):
        import matplotlib.pyplot as pl
        pl.figure()
        pl.errorbar(self.data.x, self.data.y, self.data.dy, fmt='o',
                    label=self.data.name)
        pl.plot(self.xx, self.yy, label='fit')
        if title:
            pl.title(title)
        if xlabel:
            pl.xlabel(xlabel)
        if ylabel:
            pl.ylabel(ylabel)
        pl.legend()

    def plot_components(self, model):
        import matplotlib.pyplot as pl
        for comp in model.get_components():
            yy = comp.fcn(self.paramdict, self.xx)
            pl.plot(self.xx, yy, '--', label=comp.name)
        pl.legend()
