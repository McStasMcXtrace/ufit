# ufit backend using lmfit

from __future__ import absolute_import
from ufit.core import UFitError

from lmfit import Parameters, minimize

__all__ = ['do_fit', 'backend_name']

backend_name = 'lmfit'

def do_fit(data, fcn, params, add_kw):

    lmfparams = Parameters()
    for p in params:
        lmfparams.add(p.name, p.value, expr=p.expr, min=p.pmin, max=p.pmax)

    def lmfitfcn(lmfparams, data):
        pd = dict((p.name, lmfparams[p.name].value) for p in params)
        return (fcn(pd, data.x) - data.y) / data.dy

    try:
        out = minimize(lmfitfcn, lmfparams, args=(data,), **add_kw)
    except Exception, e:
        raise UFitError('Error while fitting: %s' % e)
    #if not out.success:
    #    raise UFitError(out.message)

    for p in params:
        p.value = lmfparams[p.name].value
        p.error = lmfparams[p.name].stderr
        p.correl = lmfparams[p.name].correl

    return out.message
