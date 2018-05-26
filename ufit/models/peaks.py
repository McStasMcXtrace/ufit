#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Models for different peak shapes."""

from numpy import exp, log, sqrt, sin, cos, pi
from scipy.special import wofz

from ufit.models import Model

__all__ = ['Gauss', 'GaussInt', 'Lorentz', 'LorentzInt',
           'Voigt', 'PseudoVoigt', 'DHO']


class Gauss(Model):
    """Gaussian peak

    Parameters:

    * `pos` - Peak center position
    * `ampl` - Amplitude at center
    * `fwhm` - Full width at half maximum
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


class GaussInt(Model):
    """Gaussian peak with integrated intensity parameter

    Parameters:

    * `pos` - Peak center position
    * `int` - Integrated intensity
    * `fwhm` - Full width at half maximum
    """
    param_names = ['pos', 'int', 'fwhm']

    def __init__(self, name='', pos=None, int=None, fwhm=None):
        pp, pint, pf = self._init_params(name, self.param_names, locals())
        # integration and fwhm should be positive
        self.params[1].finalize = abs
        self.params[2].finalize = abs

        self.fcn = lambda p, x: \
            abs(p[pint]) / (abs(p[pf]) * sqrt(pi/(4 * log(2)))) * \
            exp(-(x - p[pp])**2/p[pf]**2 * 4*log(2))

    pick_points = ['peak', 'width']

    def convert_pick(self, p, w):
        fwhm = 2*abs(w[0] - p[0])
        return {
            self.params[0].name: p[0],  # position
            self.params[1].name: p[1] * fwhm * sqrt(2*pi),  # peak intensity (integrated)
            self.params[2].name: fwhm,  # FWHM
        }


class Lorentz(Model):
    """Lorentzian peak

    Parameters:

    * `pos` - Peak center position
    * `ampl` - Amplitude at center
    * `fwhm` - Full width at half maximum
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


class LorentzInt(Model):
    """Lorentzian peak with integrated intensity parameter

    Parameters:

    * `pos` - Peak center position
    * `int` - Integrated intensity
    * `fwhm` - Full width at half maximum
    """
    param_names = ['pos', 'int', 'fwhm']

    def __init__(self, name='', pos=None, int=None, fwhm=None):
        pp, pint, pf = self._init_params(name, self.param_names, locals())
        # integration and fwhm should be positive
        self.params[1].finalize = abs
        self.params[2].finalize = abs

        self.fcn = lambda p, x: 2 * abs(p[pint]) / (pi * p[pf]) / (1 + 4*(x - p[pp])**2/p[pf]**2)

    pick_points = ['peak', 'width']

    def convert_pick(self, p, w):
        fwhm = 2*abs(w[0] - p[0])
        return {
            self.params[0].name: p[0],  # position
            self.params[1].name: p[1] * fwhm * pi/2,  # integrated intensity
            self.params[2].name: fwhm,  # FWHM
        }


class Voigt(Model):
    """Voigt peak

    A convolution of a Gaussian and a Lorentzian.

    Parameters:

    * `pos` - Peak center position
    * `ampl` - Amplitude at center
    * `fwhm` - Full width at half maximum of the Gauss part
    * `shape` - Lorentz contribution
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

    * `pos` - Peak center position
    * `ampl` - Amplitude at center
    * `fwhm` - Full width at half maximum
    * `eta` - Lorentzicity
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

    * `center` - Energy zero
    * `pos` - omega_0
    * `ampl` - Amplitude
    * `gamma` - Damping
    * `tt` - Temperature in K
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


class Gauss2D(Model):
    """Gaussian peak in two dimensions

    Parameters:

    * `bkgd`   - Background
    * `pos_x`  - X center position
    * `pos_y`  - Y center position
    * `ampl`   - amplitude
    * `fwhm_x` - Full width in X direction
    * `fwhm_y` - Full width in Y direction
    * `theta`  - rotation of Gaussian in radians
    """
    param_names = ['bkgd', 'pos_x', 'pos_y', 'ampl', 'fwhm_x', 'fwhm_y', 'theta']

    def __init__(self, name='', bkgd=None, pos_x=None, pos_y=None, ampl=None,
                 fwhm_x=None, fwhm_y=None, theta=None):
        pb, ppx, ppy, pa, pfx, pfy, pth = self._init_params(
            name, self.param_names, locals())
        self.params[3].finalize = abs
        self.params[4].finalize = abs
        self.params[5].finalize = abs

        def fcn(p, x):
            # rotate coordinate system by theta
            c, s = cos(p[pth]), sin(p[pth])
            x1 = (x[:, 0] - p[ppx])*c - (x[:, 1] - p[ppy])*s
            y1 = (x[:, 0] - p[ppx])*s + (x[:, 1] - p[ppy])*c
            return abs(p[pb]) + abs(p[pa]) * \
                exp(-x1**2/p[pfx]**2 * 4*log(2)) * \
                exp(-y1**2/p[pfy]**2 * 4*log(2))
        self.fcn = fcn
