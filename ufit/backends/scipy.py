#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Backend using plain scipy leastsq."""

from __future__ import absolute_import

from numpy import sqrt, inf
from scipy.optimize import leastsq

from ufit.param import prepare_params, update_params
from ufit.utils import get_chisqr

__all__ = ['do_fit', 'backend_name']

backend_name = 'scipy'


def do_fit(data, fcn, params, add_kw):
    x, y, dy = data.fit_columns
    meta = data.meta
    varying, varynames, dependent, _ = prepare_params(params, meta)

    def leastsqfcn(params, data):
        pd = dict(zip(varynames, params))
        update_params(dependent, meta, pd)
        return (fcn(pd, x) - y) / dy

    initpars = []
    warned = False
    for p in varying:
        initpars.append(p.value)
        if (p.pmin is not None or p.pmax is not None) and not warned:
            print('Sorry, scipy backend cannot handle parameter bounds.')
            warned = True

    try:
        res = leastsq(leastsqfcn, initpars, args=(data,), full_output=1, **add_kw)
    except Exception as e:
        return False, str(e), 0

    popt, pcov, infodict, errmsg, ier = res
    success = (ier in [1, 2, 3, 4])

    nfree = len(y) - len(varying)
    if nfree > 0 and pcov is not None:
        s_sq = (leastsqfcn(popt, data)**2).sum() / nfree
        pcov = pcov * s_sq
    else:
        pcov = inf

    pd = {}
    for i, p in enumerate(varying):
        pd[p.name] = popt[i]
        if pcov is not inf:
            p.error = sqrt(pcov[i, i])
        else:
            p.error = 0
        p.correl = {}  # XXX
    update_params(dependent, meta, pd)
    for p in params:
        p.value = pd[p.name]

    return success, errmsg, get_chisqr(fcn, x, y, dy, params)
