# ufit parameter definitions

import re
import copy
import numpy as np

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


expr_namespace = {
    'data': None,  # replaced by the dataset's metadata dict, but in here
                   # so that no parameter can be called "data"
}
for fcn in ['pi', 'sqrt', 'sin', 'cos', 'tan', 'arcsin', 'arccos',
            'arctan', 'exp', 'log', 'radians', 'degrees', 'ceil',
            'floor', 'sinh', 'cosh', 'tanh']:
    expr_namespace[fcn] = getattr(np, fcn)

id_re = re.compile('[a-zA-Z_][a-zA-Z0-9_]*$')


class Param(object):
    def __init__(self, name, value=0, expr=None, pmin=None, pmax=None,
                 overall=False, delta=0, finalize=lambda x: x):
        if not id_re.match(name):
            raise UFitError('Parameter name %r is not a valid Python '
                            'identifier' % name)
        if name in expr_namespace:
            raise UFitError('Parameter name %r is reserved' % name)
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

    def __reduce__(self):
        return (Param, (self.name, self.value, self.expr, self.pmin,
                        self.pmax, self.overall, self.delta))

    def __str__(self):
        s = '%-15s = %10.5g +/- %10.5g' % (self.name, self.value, self.error)
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
    pd.update(expr_namespace)
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
            except (NameError, AttributeError):
                pass
            else:
                del dependent[p]
                dep_order.append((p, expr))
    #pd.pop('__builtins__', None)

    return varying, varynames, dep_order, pd


def update_params(parexprs, meta, pd):
    pd.update(expr_namespace)
    pd['data'] = meta
    for p, expr in parexprs:
        pd[p] = param_eval(expr, pd)
    #pd.pop('__builtins__', None)
