#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2017, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Backend using pyminuit."""

from __future__ import absolute_import

from ufit.param import prepare_params, update_params
from ufit.utils import get_chisqr

try:
    from minuit import Minuit
except ImportError:
    # unfortunately, minuit2 crashes with GIL problems here
    # from minuit2 import Minuit2 as Minuit
    raise

__all__ = ['do_fit', 'backend_name']

backend_name = 'minuit'


def do_fit(data, fcn, params, add_kw):
    x, y, dy = data.fit_columns
    meta = data.meta
    varying, varynames, dependent, _ = prepare_params(params, meta)

    # sadly, parameter names are restricted to 10 characters with pyminuit
    minuitnames = ['p%d' % j for j in range(len(varynames))]
    minuit_map = dict(zip(varynames, minuitnames))

    # also sadly, pyminuit insists on a function with the exact number and
    # names of the parameters in the signature, so we have to create
    # such a function dynamically

    code = 'def minuitfcn(' + ', '.join(minuitnames) + '''):
        pd = {''' + ', '.join("%r: %s" % v for v in minuit_map.items()) + '''}
        update_params(dependent, meta, pd)
        return ((fcn(pd, x) - y)**2 / dy**2).sum()
    '''

    fcn_environment = {'meta': meta, 'x': x, 'y': y, 'dy': dy,
                       'fcn': fcn, 'dependent': dependent}
    fcn_environment['update_params'] = update_params   # it's a global
    exec(code, fcn_environment)

    m = Minuit(fcn_environment['minuitfcn'])
    m.up = 1.0
    for kw in add_kw:
        setattr(m, kw, add_kw[kw])
    for p in varying:
        m.values[minuit_map[p.name]] = p.value
        m.errors[minuit_map[p.name]] = 100*p.delta or p.value/100. or 0.01
        if p.pmin is not None or p.pmax is not None:
            m.limits[minuit_map[p.name]] = (p.pmin is None and -1e8 or p.pmin,
                                            p.pmax is None and +1e8 or p.pmax)
    try:
        m.migrad()
        m.hesse()
    except Exception as e:
        return False, str(e), 0
    # m.minos()  -> would calculate more exact and asymmetric errors

    pd = dict((pn, m.values[minuit_map[pn]]) for pn in varynames)
    update_params(dependent, meta, pd)
    for p in params:
        p.value = pd[p.name]
        if p.name in minuit_map:
            p.error = m.errors[minuit_map[p.name]]
            p.correl = {}  # XXX
        else:
            p.error = 0
            p.correl = {}

    return True, '', get_chisqr(fcn, x, y, dy, params)
