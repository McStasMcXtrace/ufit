#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Models for several data corrections."""

from numpy import exp, sqrt, arcsin, tan, pi

from ufit.models import Model

__all__ = ['Background', 'SlopingBackground', 'CKI_Corr', 'Bose']


class Background(Model):
    """Constant background

    Parameters:

    * `bkgd` - the background (forced to be nonnegative)
    """
    param_names = ['bkgd']

    def __init__(self, name='', bkgd=0):
        pb, = self._init_params(name, self.param_names, locals())
        # background should be positive
        self.params[0].finalize = abs

        self.fcn = lambda p, x: abs(p[pb]) + 0*x

    def is_modifier(self):
        return True

    pick_points = ['background']

    def convert_pick(self, b):
        return {self.params[0].name: b[1]}


class SlopingBackground(Model):
    """Linearly sloping background

    Parameters:

    * `bkgd` - constant factor
    * `slope` - slope coefficient
    """
    param_names = ['bkgd', 'slope']

    def __init__(self, name='', bkgd=0, slope=0):
        pb, ps = self._init_params(name, self.param_names, locals())
        self.fcn = lambda p, x: p[pb] + x*p[ps]

    def is_modifier(self):
        return True

    pick_points = ['left background',
                   'right background']

    def convert_pick(self, b1, b2):
        slope = (b2[1] - b1[1]) / (b2[0] - b1[0])
        return {
            self.params[0].name: b1[1] - slope*b1[0],
            self.params[1].name: slope,
        }


class CKI_Corr(Model):
    """Correction for constant-k_i energy scans

    Parameters:

    * `ki` - the ki value in Ang-1
    * `dval` - the monochromator d-value in Ang
    """
    param_names = ['ki', 'dval']

    def __init__(self, name='', ki=None, dval='3.355'):
        pki, pdv = self._init_params(name, self.param_names, locals())

        def fcn(p, x):
            ki = p[pki]
            kf = sqrt(ki**2 - x/2.072)
            return kf**3/ki**3 * tan(arcsin(pi/ki/p[pdv]))/tan(arcsin(pi/kf/p[pdv]))
        self.fcn = fcn

    def is_modifier(self):
        return True


class Bose(Model):
    """Bose factor

    Parameters:

    * `tt` - the temperature in K
    """
    param_names = ['tt']

    def __init__(self, name='', tt=None):
        ptt, = self._init_params(name, self.param_names, locals())
        self.fcn = lambda p, x: x / (1. - exp(-11.6045*(x + 0.00001) / p[ptt]))

    def is_modifier(self):
        return True
