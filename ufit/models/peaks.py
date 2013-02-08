# peak models

from numpy import exp, log

from ufit.models import Model


class Gauss(Model):
    def __init__(self, name='', pos=None, ampl=None, fwhm=None):
        pp, pa, pf = self._init_params(name, ['pos', 'ampl', 'fwhm'], locals())
        # amplitude and fwhm should be positive
        if self.params[1].pmin is None:
            self.params[1].pmin = 0
        if self.params[2].pmin is None:
            self.params[2].pmin = 0

        # XXX fix normalization
        self.fcn = lambda p, x: \
            abs(p[pa]) * exp(-(x - p[pp])**2/p[pf]**2 * 4*log(2))


class Lorentz(Model):
    def __init__(self, name='', pos=None, ampl=None, fwhm=None):
        pp, pa, pf = self._init_params(name, ['pos', 'ampl', 'fwhm'], locals())
        # amplitude and fwhm should be positive
        if self.params[1].pmin is None:
            self.params[1].pmin = 0
        if self.params[2].pmin is None:
            self.params[2].pmin = 0

        # XXX normalization?
        self.fcn = lambda p, x: abs(p[pa]) / (1 + (x - p[pp])**2/p[pf]**2)


class DHO(Model):
    def __init__(self, name='', center=0, pos=None, ampl=None, fwhm=None):
        pc, pp, pa, pf = self._init_params(name, ['center', 'pos',
                                                  'ampl', 'fwhm'], locals())
        # all parameters except center should be positive
        for p in self.params[1:]:
            if p.pmin is None:
                p.pmin = 0
        self.fcn = lambda p, x: \
            abs(p[pa]) / (1 + (x - p[pc] - p[pp])**2/p[pf]**2) + \
            abs(p[pa]) / (1 + (x - p[pc] + p[pp])**2/p[pf]**2)
