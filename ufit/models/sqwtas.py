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

from ufit.rescalc import resmat, calc_MC, calc_MC_cluster, load_cfg, load_par
from ufit.models.base import Model

__all__ = ['ConvolvedScatteringLaw']


class ConvolvedScatteringLaw(Model):
    """Model using a scattering law given as a function and a set of resolution
    parameters for a triple-axis spectrometer.

    Signature of the S(q,w) function given by *sqw*::

       sqw(h, k, l, E, QE0, Sigma, par0, par1, ...)

    If the function is given as a string, it it taken as ``module:function``.
    The calculation is then clustered using SSH and ufit.cluster.

    h,k,l,E are arrays of the Monte-Carlo point coordinates, QE0 is the center
    of the ellipse, Sigma are the ellipse widths around the center.  A constant
    background is always included as a parameter named "bkgd".

    *instfiles* must be ('instr.cfg', 'instr.par').
    """
    nsamples = -4  # as many as there are datapoints

    def __init__(self, sqw, instfiles, NMC=2000, name=None, cluster=False, **init):
        self._cluster = False
        if isinstance(sqw, str):
            modname, funcname = sqw.split(':')
            mod = __import__(modname)
            code = open(mod.__file__.rstrip('c')).read()
            self._sqwfunc = funcname
            self._sqwcode = code
            self._sqw = getattr(mod, funcname)
            self.name = funcname
            self._cluster = cluster
        else:  # cannot cluster
            self._sqw = sqw
            self.name = name or sqw.__name__
        init['NMC'] = str(NMC)  # str() makes it a fixed parameter
        self._pvs = self._init_params(name,
            ['NMC', 'bkgd'] + inspect.getargspec(self._sqw)[0][6:], init)
        self._resmat = resmat(load_cfg(instfiles[0]), load_par(instfiles[1]))

    def fcn(self, p, x):
        parvalues = [p[pv] for pv in self._pvs]
        t1 = time.time()
        print 'Sqw: values = ', parvalues
        if self._cluster:
            res = calc_MC_cluster(x, parvalues[2:], self._sqwcode, self._sqwfunc,
                                  self._resmat, parvalues[0])
        else:
            res = calc_MC(x, parvalues[2:], self._sqw, self._resmat, parvalues[0])
        res += parvalues[1]  # background
        t2 = time.time()
        print 'Sqw: iteration = %.3f sec' % (t2-t1)
        return res
