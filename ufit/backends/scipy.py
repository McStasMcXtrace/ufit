# ufit backend using scipy.optimize.leastsq

from __future__ import absolute_import
from numpy import sqrt, inf
from scipy.optimize import leastsq
from ufit.core import UFitError, Result
from ufit.backends.util import prepare_params, update_params

__all__ = ['do_fit', 'backend_name']

backend_name = 'scipy'

def do_fit(data, fcn, params, add_kw):
    varying, varynames, dependent = prepare_params(params)

    def leastsqfcn(params, data):
        pd = dict(zip(varynames, params))
        update_params(dependent, pd)
        return (fcn(pd, data.x) - data.y) / data.dy

    initpars = []
    warned = False
    for p in varying:
        initpars.append(p.value)
        if (p.pmin is not None or p.pmax is not None) and not warned:
            print 'Sorry, scipy backend cannot handle parameter bounds.'
            warned = True

    res = leastsq(leastsqfcn, initpars, args=(data,), full_output=1, **add_kw)
    popt, pcov, infodict, errmsg, ier = res

    if ier not in [1, 2, 3, 4]:
        raise UFitError('Optimal parameters not found: ' + errmsg)

    nfree = len(data.y) - len(varying)
    if nfree > 0 and pcov is not None:
        s_sq = (leastsqfcn(popt, data)**2).sum() / nfree
        pcov = pcov * s_sq
    else:
        pcov = inf

    pd = {}
    for i, p in enumerate(varying):
        pd[p.name] = popt[i]
        if pcov is not inf:
            p.error = sqrt(pcov[i,i])
        else:
            p.error = 0
        p.correl = {}  # XXX
    update_params(dependent, pd)
    for p in params:
        p.value = pd[p.name]

    return Result(data, fcn, params, errmsg)
