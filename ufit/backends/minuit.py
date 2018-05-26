#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Backend using iminuit."""

from __future__ import absolute_import

from ufit.param import prepare_params, update_params
from ufit.utils import get_chisqr

from iminuit import Minuit

__all__ = ['do_fit', 'backend_name']

backend_name = 'minuit'


def do_fit(data, fcn, params, add_kw):
    x, y, dy = data.fit_columns
    meta = data.meta
    varying, varynames, dependent, _ = prepare_params(params, meta)

    def minuitfcn(*args):
        pd = dict(zip(varynames, args))
        update_params(dependent, meta, pd)
        return ((fcn(pd, x) - y)**2 / dy**2).sum()

    printReport = add_kw.pop('printReport', False)

    marg = dict(
        print_level=int(printReport),
        forced_parameters=varynames,
    )
    marg.update(add_kw)
    if 'errordef' not in marg:
        marg['errordef'] = 1
    for p in varying:
        marg[p.name] = p.value
        marg['error_' + p.name] = 100*p.delta or p.value/100. or 0.01
        if p.pmin is not None or p.pmax is not None:
            marg['limit_' + p.name] = (p.pmin is None and -1e8 or p.pmin,
                                       p.pmax is None and +1e8 or p.pmax)

    m = Minuit(minuitfcn, **marg)
    try:
        m.migrad()
        m.hesse()
    except Exception as e:
        return False, str(e), 0
    # m.minos()  -> would calculate more exact and asymmetric errors

    pd = dict((pn, m.values[pn]) for pn in varynames)
    update_params(dependent, meta, pd)
    for p in params:
        p.value = pd[p.name]
        if p.name in varynames:
            p.error = m.errors[p.name]
            p.correl = {}  # XXX
        else:
            p.error = 0
            p.correl = {}

    return True, '', get_chisqr(fcn, x, y, dy, params)
