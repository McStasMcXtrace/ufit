# ufit backend using lmfit

from __future__ import absolute_import
from ufit.core import UFitError
from ufit.backends.util import prepare_params, update_params

from lmfit import Parameters, minimize

__all__ = ['do_fit', 'backend_name']

backend_name = 'lmfit'

def do_fit(data, fcn, params, add_kw):

    # lmfit can handle expression-based parameters itself, but that is
    # a) buggy (cannot pass custom items into namespace without subclass)
    # and b) it is better to use the same mechanism in all backends

    varying, varynames, dependent, _ = prepare_params(params, data)

    lmfparams = Parameters()
    for p in varying:
        lmfparams.add(p.name, p.value, min=p.pmin, max=p.pmax)

    def lmfitfcn(lmfparams, data):
        pd = dict((pn, lmfparams[pn].value) for pn in varynames)
        update_params(dependent, data, pd)
        return (fcn(pd, data.x) - data.y) / data.dy

    try:
        out = minimize(lmfitfcn, lmfparams, args=(data,), **add_kw)
    except Exception, e:
        raise UFitError('Error while fitting: %s' % e)
    #if not out.success:
    #    raise UFitError(out.message)

    pd = dict((pn, lmfparams[pn].value) for pn in varynames)
    update_params(dependent, data, pd)
    for p in params:
        p.value = pd[p.name]
        if p.name in lmfparams:
            p.error = lmfparams[p.name].stderr
            p.correl = lmfparams[p.name].correl
        else:
            p.error = 0
            p.correl = {}

    return out.message
