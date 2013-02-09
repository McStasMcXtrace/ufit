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
        self.params[1].finalize = abs
        self.params[2].finalize = abs

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
        self.params[1].finalize = abs
        self.params[2].finalize = abs

        self.fcn = lambda p, x: abs(p[pa]) / (1 + 4*(x - p[pp])**2/p[pf]**2)


class PVoigt(Model):
    """Model for a pseudo-Voigt peak.

    Parameters:
    * pos - Peak center position
    * ampl - Amplitude at center
    * fwhm - Full width at half maximum
    * eta - Lorentzicity
    """
    def __init__(self, name='', pos=None, ampl=None, fwhm=None, eta=0.5):
        pp, pa, pf, pe = self._init_params(name, ['pos', 'ampl', 'fwhm', 'eta'], locals())
        # amplitude and fwhm should be positive
        self.params[1].finalize = abs
        self.params[2].finalize = abs
        # eta should be between 0 and 1
        self.params[3].finalize = lambda e: e % 1.0

        self.fcn = lambda p, x: abs(p[pa]) * \
            ((p[pe] % 1.0) / (1 + 4*(x - p[pp])**2/p[pf]**2) +
             (1-(p[pe] % 1.0)) * exp(-(x - p[pp])**2/p[pf]**2 * 4*log(2)))


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
        # pos, amplitude and gamma should be positive
        self.params[1].finalize = abs
        self.params[2].finalize = abs
        self.params[3].finalize = abs
        self.fcn = lambda p, x: x / (1. - exp(-11.6045*(x+0.00001) / p[ptt])) * \
            abs(p[pa]) * abs(p[pg]) / ((p[pp]**2 - x**2)**2 + (p[pg]*x)**2)
