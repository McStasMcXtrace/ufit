# ufit backend using minuit2

from __future__ import absolute_import
from ufit.core import UFitError, Result
from ufit.backends.util import update_evalpars

try:
    from minuit import Minuit
except ImportError:
    from minuit2 import Minuit2 as Minuit

__all__ = ['do_fit', 'backend_name']

backend_name = 'minuit'

#raise ImportError

def do_fit(data, fcn, params, add_kw):

    # find parameters that need to vary
    evalpars = {}
    varypars = []
    for p in params:
        if p.expr:
            evalpars[p.name] = p.expr
        else:
            varypars.append(p)

    # sadly, pyminuit insists on a function with the exact number and
    # names of the parameters in the signature, so we have to create
    # such a function dynamically

    code = 'def minuitfcn(' + ', '.join(p.name for p in varypars) + '''):
        p = {''' + ', '.join("%r: %s" % (p.name, p.name) for p in varypars) + '''}
        update_evalpars(evalpars, p)
        return ((fcn(p, data.x) - data.y)**2 / data.dy**2).sum()
    '''

    fcn_environment = locals().copy()
    fcn_environment['update_evalpars'] = update_evalpars   # it's a global
    exec code in fcn_environment

    m = Minuit(fcn_environment['minuitfcn'])
    m.up = 1.0
    for kw in add_kw:
        setattr(m, kw, add_kw[kw])
    for p in varypars:
        m.values[p.name] = p.value
        if p.pmin is not None or p.pmax is not None:
            m.limits[p.name] = (p.pmin is None and -1e8 or p.pmin,
                                p.pmax is None and +1e8 or p.pmax)
    try:
        m.migrad()
        m.hesse()
    except Exception, e:
        raise UFitError('Error while fitting: %s' % e)
    #m.minos()  -> would calculate more exact and asymmetric errors

    d = m.values.copy()
    update_evalpars(evalpars, d)
    for p in params:
        p.value = d[p.name]
        p.error = m.errors.get(p.name, 0)
        p.correl = {}

    return Result(data, fcn, params, '')
