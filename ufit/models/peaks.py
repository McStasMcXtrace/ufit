# peak models

from numpy import exp, log

from ufit.models import Model


class Gauss(Model):
    """Model for a Gauss peak.

    Parameters:
    * pos - Peak center position
    * ampl - Amplitude at center
    * fwhm - Full width at half maximum
    """
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
    """Model for a Lorentzian peak.

    Parameters:
    * pos - Peak center position
    * ampl - Amplitude at center
    * fwhm - Full width at half maximum
    """
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
    """Model for a Damped Harmonic Oscillator (two Lorentzians).

    Parameters:
    * center - Energy center
    * pos - omega_0
    * ampl - Amplitude
    * gamma - Damping
    * tt - Temperature in K
    """
    def __init__(self, name='',
                 center=0, pos=None, ampl=None, gamma=None, tt=None):
        pc, pp, pa, pg, ptt = self._init_params(
            name, ['center', 'pos', 'ampl', 'gamma', 'tt'], locals())
        # all parameters except center should be positive
        for p in self.params[1:]:
            if p.pmin is None:
                p.pmin = 0
        self.fcn = lambda p, x: x / (1. - exp(-11.6045*x / p[ptt])) * \
            abs(p[pa]) * p[pg] / ((p[pp]**2 - x**2)**2 + (p[pg]*x)**2)
