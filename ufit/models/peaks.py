# peak models

from numpy import exp, log, sqrt
from scipy.special import wofz

from ufit.models import Model


class Gauss(Model):
    """Gaussian peak

    Parameters:
    * pos - Peak center position
    * ampl - Amplitude at center
    * fwhm - Full width at half maximum
    """
    param_names = ['pos', 'ampl', 'fwhm']

    def __init__(self, name='', pos=None, ampl=None, fwhm=None):
        pp, pa, pf = self._init_params(name, self.param_names, locals())
        # amplitude and fwhm should be positive
        self.params[1].finalize = abs
        self.params[2].finalize = abs

        self.fcn = lambda p, x: \
            abs(p[pa]) * exp(-(x - p[pp])**2/p[pf]**2 * 4*log(2))

    pick_points = ['peak', 'width']

    def convert_pick(self, p, w):
        return {
            self.params[0].name: p[0],  # position
            self.params[1].name: p[1],  # peak amplitude
            self.params[2].name: 2*abs(w[0] - p[0]),  # FWHM
        }


class Lorentz(Model):
    """Lorentzian peak

    Parameters:
    * pos - Peak center position
    * ampl - Amplitude at center
    * fwhm - Full width at half maximum
    """
    param_names = ['pos', 'ampl', 'fwhm']

    def __init__(self, name='', pos=None, ampl=None, fwhm=None):
        pp, pa, pf = self._init_params(name, self.param_names, locals())
        # amplitude and fwhm should be positive
        self.params[1].finalize = abs
        self.params[2].finalize = abs

        self.fcn = lambda p, x: abs(p[pa]) / (1 + 4*(x - p[pp])**2/p[pf]**2)

    pick_points = ['peak', 'width']

    def convert_pick(self, p, w):
        return {
            self.params[0].name: p[0],  # position
            self.params[1].name: p[1],  # peak amplitude
            self.params[2].name: 2*abs(w[0] - p[0]),  # FWHM
        }


class Voigt(Model):
    """Voigt peak

    A convolution of a Gaussian and a Lorentzian.

    Parameters:
    * pos - Peak center position
    * ampl - Amplitude at center
    * fwhm - Full width at half maximum of the Gauss part
    * shape - Lorentz contribution
    """
    param_names = ['pos', 'ampl', 'fwhm', 'shape']

    def __init__(self, name='', pos=None, ampl=None, fwhm=None, shape=None):
        pp, pa, pf, psh = self._init_params(name, self.param_names, locals())
        # amplitude and fwhms should be positive
        self.params[1].finalize = abs
        self.params[2].finalize = abs
        self.params[3].finalize = abs

        self.fcn = lambda p, x: \
            p[pa] / wofz(1j*sqrt(log(2))*p[psh]).real * \
            wofz(2*sqrt(log(2)) * (x-p[pp])/p[pf] + 1j*sqrt(log(2))*p[psh]).real

    pick_points = ['peak', 'width']

    def convert_pick(self, p, w):
        return {
            self.params[0].name: p[0],  # position
            self.params[1].name: p[1],  # peak amplitude
            self.params[2].name: 2*abs(w[0] - p[0]),  # FWHM of Gauss
            self.params[3].name: 0,
        }


class PseudoVoigt(Model):
    """Pseudo-Voigt peak

    A pseudo-convolution of a Gaussian and a Lorentzian.

    Parameters:
    * pos - Peak center position
    * ampl - Amplitude at center
    * fwhm - Full width at half maximum
    * eta - Lorentzicity
    """
    param_names = ['pos', 'ampl', 'fwhm', 'eta']

    def __init__(self, name='', pos=None, ampl=None, fwhm=None, eta=0.5):
        pp, pa, pf, pe = self._init_params(name, self.param_names, locals())
        # amplitude and fwhm should be positive
        self.params[1].finalize = abs
        self.params[2].finalize = abs
        # eta should be between 0 and 1
        self.params[3].finalize = lambda e: e % 1.0

        self.fcn = lambda p, x: abs(p[pa]) * \
            ((p[pe] % 1.0) / (1 + 4*(x - p[pp])**2/p[pf]**2) +
             (1-(p[pe] % 1.0)) * exp(-(x - p[pp])**2/p[pf]**2 * 4*log(2)))

    pick_points = ['peak', 'width']

    def convert_pick(self, p, w):
        return {
            self.params[0].name: p[0],  # position
            self.params[1].name: p[1],  # peak amplitude
            self.params[2].name: 2*abs(w[0] - p[0]),  # FWHM
        }


class DHO(Model):
    """Damped Harmonic Oscillator

    Two Lorentzians centered around zero with a common width and amplitude,
    respecting the Bose factor.

    Parameters:
    * center - Energy zero
    * pos - omega_0
    * ampl - Amplitude
    * gamma - Damping
    * tt - Temperature in K
    """
    param_names = ['center', 'pos', 'ampl', 'gamma', 'tt']

    def __init__(self, name='',
                 center=0, pos=None, ampl=None, gamma=None, tt=None):
        pc, pp, pa, pg, ptt = self._init_params(name, self.param_names,
                                                locals())
        # pos, amplitude and gamma should be positive
        self.params[1].finalize = abs
        self.params[2].finalize = abs
        self.params[3].finalize = abs
        self.fcn = lambda p, x: x / (1. - exp(-11.6045*(x+0.00001) / p[ptt])) * \
            abs(p[pa]) * abs(p[pg]) / \
            ((p[pp]**2 - (x - p[pc])**2)**2 + (p[pg]*(x - p[pc]))**2)

    pick_points = ['left peak', 'width of left peak', 'right peak']

    def convert_pick(self, p1, w, p2):
        return {
            self.params[0].name: 0.5*(p1[0] + p2[0]),  # center
            self.params[1].name: 0.5*abs(p1[0] - p2[0]),  # position
            self.params[2].name: p1[1] * 0.01,  # peak amplitude
            self.params[3].name: 2*abs(w[0] - p1[0]),  # gamma
        }
