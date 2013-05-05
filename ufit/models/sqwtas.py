#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Model of S(q,w) with resolution convolution for TAS."""

import time
import inspect

from ufit.rescalc import resmat, calc_MC, load_cfg, load_par
from ufit.models.base import Model


class ConvolvedScatteringLaw(Model):
    """Model using a scattering law given as a function and a set of resolution
    parameters for a triple-axis spectrometer.

    Signature of the S(q,w) function given by *sqw*::

       sqw(h, k, l, E, QE0, Sigma, par0, par1, ...)

    h,k,l,E is the Monte-Carlo point, QE0 is the center of the ellipse, Sigma
    are the ellipse widths around the center.  A constant background is always
    included as a parameter named "bkgd".

    *instfiles* must be ('instr.cfg', 'instr.par').
    """
    nsamples = 0  # as many as there are datapoints

    def __init__(self, sqw, instfiles, N=500, name=None, **init):
        self.name = name or sqw.__name__
        self._N = N
        self._sqw = sqw
        self._pvs = self._init_params(name,
                                      ['bkgd'] + inspect.getargspec(sqw)[0][6:], init)
        self._resmat = resmat(load_cfg(instfiles[0]), load_par(instfiles[1]))

    def fcn(self, p, x):
        parvalues = [p[pv] for pv in self._pvs]
        #t1 = time.time()
        #print 'Sqw: values = ', parvalues
        res = calc_MC(x, parvalues[1:], self._sqw, self._resmat, self._N)
        res += parvalues[0]  # background
        #t2 = time.time()
        #print 'Sqw: iteration = %.3f sec' % (t2-t1)
        return res
