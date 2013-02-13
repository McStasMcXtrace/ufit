#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Backend using lmfit."""

from __future__ import absolute_import

from ufit.param import prepare_params, update_params

from lmfit import Parameters, minimize

__all__ = ['do_fit', 'backend_name']

backend_name = 'lmfit'

def do_fit(data, fcn, params, add_kw):

    # lmfit can handle expression-based parameters itself, but that is
    # a) buggy (cannot pass custom items into namespace without subclass)
    # and b) it is better to use the same mechanism in all backends

    x, y, dy = data.fit_columns
    meta = data.meta
    varying, varynames, dependent, _ = prepare_params(params, meta)

    lmfparams = Parameters()
    for p in varying:
        lmfparams.add(p.name, p.value, min=p.pmin, max=p.pmax)

    def lmfitfcn(lmfparams, data):
        pd = dict((pn, lmfparams[pn].value) for pn in varynames)
        update_params(dependent, meta, pd)
        return (fcn(pd, x) - y) / dy

    try:
        out = minimize(lmfitfcn, lmfparams, args=(data,), **add_kw)
    except Exception, e:
        return False, str(e), 0

    pd = dict((pn, lmfparams[pn].value) for pn in varynames)
    update_params(dependent, meta, pd)
    for p in params:
        p.value = pd[p.name]
        if p.name in lmfparams:
            p.error = lmfparams[p.name].stderr
            p.correl = lmfparams[p.name].correl
        else:
            p.error = 0
            p.correl = {}

    # sadly, out.message is a bit buggy
    message = ''
    if not out.success:
        message = out.lmdif_message
    if not out.errorbars:
        message += ' Could not estimate error bars.'
    return out.success, message, out.redchi
