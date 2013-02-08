# ufit backend using scipy.optimize.leastsq

from __future__ import absolute_import
from numpy import sqrt, inf
from scipy.optimize import leastsq
from ufit.core import UFitError, Result
from ufit.backends.util import update_evalpars

__all__ = ['do_fit', 'backend_name']

backend_name = 'scipy'

def do_fit(data, fcn, params, add_kw):

    # find parameters that need to vary
    evalpars = {}
    varypars = []
    for p in params:
        if p.expr:
            evalpars[p.name] = p.expr
        else:
            varypars.append(p)

    def leastsqfcn(params, data):
        p = dict((p.name, pv) for (p, pv) in zip(varypars, params))
        update_evalpars(evalpars, p)
        return (fcn(p, data.x) - data.y) / data.dy

    initpars = []
    warned = False
    for p in varypars:
        initpars.append(p.value)
        if (p.pmin is not None or p.pmax is not None) and not warned:
            print 'Sorry, scipy backend cannot handle parameter bounds.'
            warned = True

    res = leastsq(leastsqfcn, initpars, args=(data,), full_output=1, **add_kw)
    popt, pcov, infodict, errmsg, ier = res

    if ier not in [1, 2, 3, 4]:
        raise UFitError('Optimal parameters not found: ' + errmsg)

    nfree = len(data.y) - len(varypars)
    if nfree > 0 and pcov is not None:
        s_sq = (leastsqfcn(popt, data)**2).sum() / nfree
        pcov = pcov * s_sq
    else:
        pcov = inf

    d = {}
    for i, p in enumerate(varypars):
        d[p.name] = popt[i]
        if pcov is not inf:
            p.error = sqrt(pcov[i,i])
        else:
            p.error = 0
        p.correl = {}
    update_evalpars(evalpars, d)
    for p in params:
        p.value = d[p.name]

    return Result(data, fcn, params, errmsg)
