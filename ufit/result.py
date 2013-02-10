# ufit result class

from numpy import linspace


class Result(object):
    def __init__(self, success, data, model, params, message):
        self.success = success
        self.data = data
        self.model = model
        self.params = params
        self.message = message
        self.paramdict = dict((p.name, p) for p in params)
        self.paramvalues = dict((p.name, p.value) for p in params)
        sum_sqr = ((model.fcn(self.paramvalues, data.x) - data.y)**2 / data.dy**2).sum()
        nfree = len(data.y) - sum(1 for p in params if not p.expr)
        self.chisqr = sum_sqr / nfree

        self.xx = linspace(data.x[0], data.x[-1], 1000)
        self.yy = model.fcn(self.paramvalues, self.xx)

    def printout(self):
        print 'Fit results for %s' % self.data.name
        if not self.success:
            print 'FIT FAILED: ' + self.message
        elif self.message:
            print '>', self.message
        print '-' * 80
        for p in self.params:
            print p
        print '%-15s = %10.4g' % ('chi^2/NDF', self.chisqr)
        print '=' * 80

    def plot(self, **kw):
        if 'title' not in kw:
            kw['title'] = 'red. chisqr = %.4f' % self.chisqr
        self.model.plot(self.data, _pdict=self.paramvalues, **kw)

    def plot_components(self, **kw):
        self.model.plot_components(self.data, _pdict=self.paramvalues, **kw)
