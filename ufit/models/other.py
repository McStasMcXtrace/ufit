#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Diverse other models."""

from numpy import cos, sin, exp, pi, log, piecewise, sign, tanh

from ufit.param import Param
from ufit.models.base import Model

__all__ = ['Const', 'StraightLine', 'Parabola',
           'Cosine', 'Sinc', 'ExpDecay', 'PowerLaw', 'BrillouinT', 'BrillouinB']


class Const(Model):
    """A constant, to be used for modifying other models (e.g. exponentiation)

    For example: ``Sinc() ** Const('eta')``

    Parameters:

    * the constant  (named after the model's name)
    """

    def __init__(self, name='', c=None):
        # this initialization is a bit different from what _init_params does,
        # so we don't use it here: the parameter's name will be whatever the
        # model itself is called
        self.name = name
        pname = name or 'c'
        self.params = [Param.from_init(pname, c or 0)]
        self.fcn = lambda p, x: p[pname] + 0*x

    def is_modifier(self):
        return True


class StraightLine(Model):
    """Straight line

    y = slope * x + y0

    Parameters:

    * `slope`
    * `y0`  - intercept
    """
    param_names = ['slope', 'y0']

    def __init__(self, name='', slope=1, y0=0):
        psl, py0 = self._init_params(name, self.param_names, locals())
        self.fcn = lambda p, x: p[psl]*x + p[py0]

    pick_points = ['one point on curve', 'another point on curve']

    def convert_pick(self, b1, b2):
        slope = (b2[1] - b1[1]) / (b2[0] - b1[0])
        return {
            self.params[0].name: slope,
            self.params[1].name: b1[1] - slope*b1[0],
        }


class Parabola(Model):
    """Parabola

    y = stretch * (x - x0)^2 + y0

    Parameters:

    * `x0`  - x coordinate of vertex
    * `y0`  - y coordinate of vertex
    * `stretch` - stretch factor
    """
    param_names = ['x0', 'y0', 'stretch']

    def __init__(self, name='', x0=0, y0=0, stretch=1):
        px0, py0, ps = self._init_params(name, self.param_names, locals())
        self.fcn = lambda p, x: p[ps] * (x - p[px0])**2 + p[py0]

    pick_points = ['vertex', 'another point on curve']

    def convert_pick(self, vx, p2):
        return {
            self.params[0].name: vx[0],
            self.params[1].name: vx[1],
            self.params[2].name: (p2[1] - vx[1]) / (p2[0] - vx[0])**2,
        }


class Cosine(Model):
    """Cosine

    y = ampl * cos(freq * x + phase)

    Parameters:

    * `ampl` - amplitude
    * `freq` - frequency (omega or k)
    * `phase` - phase in radians
    """
    param_names = ['ampl', 'freq', 'phase']

    def __init__(self, name='', ampl=None, freq=None, phase=0):
        pa, pf, pp = self._init_params(name, self.param_names, locals())
        self.fcn = lambda p, x: p[pa] * cos(p[pf]*x + p[pp])

    pick_points = ['a maximum', 'next minimum']

    def convert_pick(self, pmax, pmin):
        freq = pi/abs(pmin[0] - pmax[0])
        return {
            self.params[0].name: pmax[1] - pmin[1],          # amplitude
            self.params[1].name: freq,                       # frequency
            self.params[2].name: (- freq*pmax[0]) % (2*pi),  # phase
        }


class Sinc(Model):
    """Sinc function

    y = ampl * sin(freq*(x - center)) / (freq*(x - center))

    Parameters:

    * `ampl` - amplitude at x = center
    * `freq` - frequency of the sine
    * `center` - point of maximum amplitude
    """
    param_names = ['ampl', 'freq', 'center']

    def __init__(self, name='', ampl=None, freq=None, center=0):
        pa, pf, pc = self._init_params(name, self.param_names, locals())
        self.fcn = lambda p, x: piecewise(
            x - p[pc], [x == p[pc]],
            [p[pa], lambda v: p[pa] * sin(p[pf]*v) / (p[pf]*v)])


class ExpDecay(Model):
    """Exponential decay

    y = y1 + (y0 - y1) * exp(-x/tau)

    Parameters:

    * `y0`  - value at x = 0
    * `tau` - decay constant: exp(-x/tau)
    * `y1`  - value at x -> infinity
    """
    param_names = ['y0', 'tau', 'y1']

    def __init__(self, name='', y0=1, tau=None, y1=0):
        p0, pt, p1 = self._init_params(name, self.param_names, locals())
        self.fcn = lambda p, x: p[p1] + (p[p0]-p[p1])*exp(-x/p[pt])

    pick_points = ['maximum value', 'minimum value', 'half maximum']

    def convert_pick(self, pmax, pmin, phalf):
        return {
            self.params[0].name: pmax[1],
            self.params[1].name: phalf[0]/log(2),
            self.params[2].name: pmin[1],
        }


class PowerLaw(Model):
    """Power law

    Parameters:

    * `start` - starting point
    * `scale` - x value scaling (positive => right side of starting point)
    * `beta`  - exponent
    """
    param_names = ['start', 'scale', 'beta']

    def __init__(self, name='', scale=1, start=0, ampl=None, beta=None):
        ps, psc, pb = self._init_params(name, self.param_names, locals())
        self.fcn = lambda p, x: piecewise(
            p[psc]*(x-p[ps]), [p[psc]*(x-p[ps]) < 0],
            [0, lambda v: pow(v, p[pb])])

    pick_points = ['starting point', 'one point on curve',
                   'another point on curve']

    def convert_pick(self, pstart, p1, p2):
        beta = log(p1[1]/p2[1])/log((p1[0]-pstart[0])/(p2[0]-pstart[0]))
        scale = sign(p1[0] - pstart[0])*(p1[1] / abs(p1[0] - pstart[0])**beta)
        return {
            self.params[0].name: pstart[0],
            self.params[1].name: scale,
            self.params[2].name: beta,
        }


class BrillouinT(Model):
    """Brillouin function versus temperature (in K)

    Parameters:

    * `J` - spin
    * `B` - applied field in T
    * `g` - g-factor
    * `scale` - scale of the Y values
    """
    param_names = ['J', 'B', 'g', 'scale']

    def __init__(self, name='', J=1, B=0, g=1, scale=1):
        pj, pb, pg, ps = self._init_params(name, self.param_names, locals())

        def fcn(p, x):
            J = p[pj]
            arg = 0.67171388 * p[pg] * p[pb] / x
            return p[ps] * ((2*J+1)/(2*J)/tanh((2*J+1)/(2*J)*arg) -
                            1/(2*J)/tanh(arg/(2*J)))
        self.fcn = fcn


class BrillouinB(Model):
    """Brillouin function versus field (in T)

    Parameters:

    * `J` - spin
    * `T` - temperature in K
    * `g` - g-factor
    * `scale` - scale of the Y values
    """
    param_names = ['J', 'T', 'g', 'scale']

    def __init__(self, name='', J=1, T=1, g=1, scale=1):
        pj, pt, pg, ps = self._init_params(name, self.param_names, locals())

        def fcn(p, x):
            J = p[pj]
            arg = 0.67171388 * p[pg] * x / p[pt]
            return p[ps] * ((2*J+1)/(2*J)/tanh((2*J+1)/(2*J)*arg) -
                            1/(2*J)/tanh(arg/(2*J)))
        self.fcn = fcn
