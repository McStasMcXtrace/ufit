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

from ufit.rescalc import resmat, calc_MC, calc_MC_cluster, load_cfg, load_par, \
     PARNAMES, CFGNAMES, plot_resatpoint
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

    Initial parameters can include parameters named cfg_... and par_...; this
    will add instrument configuration and parameters to the fitting parameters.
    They can be given initial values or a None value, in which case the initial
    value will come from the .cfg or .par file.

    Use cfg_ALL=1 or par_ALL=1 to add all cfg or par entries to the fit
    parameters (this is mostly useful to interactively play around with the
    resolution in one scan).
    """
    nsamples = -4  # for plotting: plot only 4x as many points as datapoints

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

        instparnames = []
        par_all = False
        cfg_all = False
        self._instpars = []

        cfg_orig = load_cfg(instfiles[0])
        par_orig = load_par(instfiles[1])

        for par in init:
            if par == 'par_ALL':
                par_all = True
            elif par == 'cfg_ALL':
                cfg_all = True
            elif par.startswith('par_'):
                if par[4:] in PARNAMES:
                    self._instpars.append(par[4:])
                    instparnames.append(par)
                    if init[par] is None:
                        init[par] = str(par_orig[par[4:]])
                else:
                    raise Exception('invalid instrument parameter: %r' % par)
            elif par.startswith('cfg_'):
                if par[4:] in CFGNAMES:
                    self._instpars.append(CFGNAMES.index(par[4:]))
                    instparnames.append(par)
                    if init[par] is None:
                        init[par] = str(cfg_orig[CFGNAMES.index(par[4:])])
                else:
                    raise Exception('invalid instrument configuration: %r' % par)

        if par_all:
            instparnames = [pn for pn in instparnames if not pn.startswith('par_')]
            self._instpars = [pn for pn in self._instpars if not isinstance(pn, str)]
            instparnames.extend('par_' + pn for pn in PARNAMES)
            self._instpars.extend(PARNAMES)
            for pn in PARNAMES:
                init['par_' + pn] = str(par_orig[pn])
        if cfg_all:
            instparnames = [pn for pn in instparnames if not pn.startswith('cfg_')]
            self._instpars = [ip for ip in self._instpars if isinstance(ip, str)]
            instparnames.extend('cfg_' + x for x in CFGNAMES)
            self._instpars.extend(range(len(CFGNAMES)))
            for i in range(len(CFGNAMES)):
                init['cfg_' + CFGNAMES[i]] = str(cfg_orig[i])

        self._pvs = self._init_params(name,
            ['NMC', 'bkgd'] + inspect.getargspec(self._sqw)[0][6:] +
            instparnames, init)
        self._ninstpar = len(instparnames)
        self._resmat = resmat(cfg_orig, par_orig)

    def fcn(self, p, x):
        parvalues = [p[pv] for pv in self._pvs]
        t1 = time.time()
        print 'Sqw: values = ', parvalues
        if self._ninstpar:
            sqwpar  = parvalues[2:-self._ninstpar]
            for pn, pv in zip(self._instpars, parvalues[-self._ninstpar:]):
                if isinstance(pn, str):
                    self._resmat.par[pn] = pv
                else:
                    self._resmat.cfg[pn] = pv
            use_caching = False
        else:
            sqwpar = parvalues[2:]
            use_caching = True
        if self._cluster:
            res = calc_MC_cluster(x, sqwpar, self._sqwcode,
                                  self._sqwfunc, self._resmat, parvalues[0],
                                  use_caching=use_caching)
        else:
            res = calc_MC(x, sqwpar, self._sqw, self._resmat,
                          parvalues[0], use_caching=use_caching)
        res += parvalues[1]  # background
        t2 = time.time()
        print 'Sqw: iteration = %.3f sec' % (t2-t1)
        return res

    def resplot(self, h, k, l, e):
        self._resmat.sethklen(h, k, l, e)
        plot_resatpoint(self._resmat.cfg, self._resmat.par, self._resmat)
