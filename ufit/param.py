# ufit parameter definitions

import copy

from ufit import UFitError


class fixed(str):
    pass

class expr(str):
    pass

class overall(object):
    def __init__(self, v):
        self.v = v

class datapar(object):
    def __init__(self, v):
        self.v = v

class limited(tuple):
    def __new__(self, min, max, v):
        return (min, max, v)


class Param(object):
    def __init__(self, name, value=0, expr=None, pmin=None, pmax=None,
                 overall=False, finalize=lambda x: x, delta=0):
        self.name = name
        self.value = value
        self.expr = expr
        self.pmin = pmin
        self.pmax = pmax
        # true if a global parameter for a global fit
        self.overall = overall
        # transform parameter after successful fit
        self.finalize = finalize
        # for backends that support setting parameter increments
        self.delta = delta
        # properties set on fit result
        self.error = 0
        self.correl = {}

    @classmethod
    def from_init(cls, name, pdef):
        if isinstance(pdef, cls):
            return pdef
        self = cls(name)
        while not isinstance(pdef, (int, long, float, str)):
            if isinstance(pdef, overall):
                self.overall = True
                pdef = pdef.v
            elif isinstance(pdef, datapar):
                self.expr = 'data.' + pdef.v
                pdef = 0
            elif isinstance(pdef, tuple) and len(pdef) == 3:
                self.pmin, self.pmax, pdef = pdef
            else:
                raise UFitError('Parameter definition %s not understood' %
                                pdef)
        if isinstance(pdef, str):
            self.expr = pdef
        else:
            self.value = pdef
        return self

    def copy(self, newname=None):
        cp = copy.copy(self)
        cp.name = newname or self.name
        return cp

    def __str__(self):
        s = '%-15s = %10.4g +/- %10.4g' % (self.name, self.value, self.error)
        if self.expr:
            s += ' (fixed: %s)' % self.expr
        if self.overall:
            s += ' (global)'
        return s

    def __repr__(self):
        return '<Param %s>' % self


# XXX replace by something more safe later
param_eval = eval

def prepare_params(params, meta):
    # find parameters that need to vary
    dependent = {}
    varying = []
    varynames = []
    for p in params:
        if p.expr:
            dependent[p.name] = p.expr
        else:
            varying.append(p)
            varynames.append(p.name)

    pd = dict((p.name, p.value) for p in varying)
    pd['data'] = meta

    # poor man's dependency tracking of parameter expressions
    dep_order = []
    maxit = len(dependent) + 1
    while dependent:
        maxit -= 1
        if maxit == 0:
            raise UFitError('detected unresolved parameter dependencies '
                            'among %s' % dependent.keys())
        for p, expr in dependent.items():
            try:
                pd[p] = param_eval(expr, pd)
            except NameError:
                pass
            else:
                del dependent[p]
                dep_order.append((p, expr))
    #pd.pop('__builtins__', None)

    return varying, varynames, dep_order, pd


def update_params(parexprs, meta, pd):
    pd['data'] = meta
    for p, expr in parexprs:
        pd[p] = param_eval(expr, pd)
    #pd.pop('__builtins__', None)
