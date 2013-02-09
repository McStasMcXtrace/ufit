# ufit backend using minuit2

from __future__ import absolute_import
from ufit.core import UFitError
from ufit.backends.util import prepare_params, update_params

try:
    from minuit import Minuit
except ImportError:
    ## minuit2 crashes with GIL problems here
    #from minuit2 import Minuit2 as Minuit
    raise

__all__ = ['do_fit', 'backend_name']

backend_name = 'minuit'

def do_fit(data, fcn, params, add_kw):
    varying, varynames, dependent = prepare_params(params)

    # sadly, pyminuit insists on a function with the exact number and
    # names of the parameters in the signature, so we have to create
    # such a function dynamically

    code = 'def minuitfcn(' + ', '.join(varynames) + '''):
        pd = {''' + ', '.join("%r: %s" % (pn, pn) for pn in varynames) + '''}
        update_params(dependent, data, pd)
        return ((fcn(pd, data.x) - data.y)**2 / data.dy**2).sum()
    '''

    fcn_environment = {'data': data, 'fcn': fcn, 'dependent': dependent}
    fcn_environment['update_params'] = update_params   # it's a global
    exec code in fcn_environment

    m = Minuit(fcn_environment['minuitfcn'])
    m.up = 1.0
    for kw in add_kw:
        setattr(m, kw, add_kw[kw])
    for p in varying:
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

    pd = m.values.copy()
    update_params(dependent, data, pd)
    for p in params:
        p.value = pd[p.name]
        p.error = m.errors.get(p.name, 0)
        p.correl = {}  # XXX

    return ''
