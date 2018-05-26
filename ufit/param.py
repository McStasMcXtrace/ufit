#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Parameter definition class and helper functions for evaluating parameters."""

import re
import copy
import numpy as np
import scipy

from ufit import UFitError
from ufit.pycompat import iteritems, listitems, number_types, string_types

__all__ = ['fixed', 'expr', 'overall', 'datapar', 'datainit', 'limited',
           'delta', 'Param', 'expr_namespace']


class fixed(str):
    """Mark the parameter value as fixed.

    The ``fixed()`` wrapper can also be omitted; any string means that a
    parameter as a fixed value that can include references to other parameters.
    """
    def __init__(self, p):
        str.__init__(self, p)


class expr(str):
    """Mark the parameter value as an expression.

    The ``expr()`` wrapper can also be omitted; any string means that a
    parameter as a fixed value that can include references to other parameters.
    """
    def __init__(self, e):
        str.__init__(self, e)


class overall(object):
    """Mark the parameter as an "overall" (global) parameter in a global fit.

    The argument can be another parameter definition, e.g. ``overall(limited(0,
    10, 2))``.
    """
    def __init__(self, v):
        self.v = v


class datapar(object):
    """Mark the parameter as coming from the data file's metadata.

    ``datapar('foo')`` is equivalent to ``expr('data.foo')``.
    """
    def __init__(self, v):
        self.v = v


class datainit(object):
    """Mark the parameter as initially coming from the data file, but free
    for fitting.
    """
    def __init__(self, v):
        self.v = v


class limited(tuple):
    """Give parameter limits together with the initial value.

    Example use::

       Gauss('peak', pos=0, ampl=limited(0, 100, 50), fwhm=1)
    """
    def __new__(self, min, max, v):
        return (min, max, v)


class delta(object):
    """Give parameter delta together with initial value."""
    def __init__(self, delta, v):
        self.delta = delta
        self.v = v


expr_namespace = {
    'data': None,  # replaced by the dataset's metadata dict, but in here
                   # so that no parameter can be called "data"
    'numpy': np,
    'scipy': scipy,
}
for fcn in ['pi', 'sqrt', 'sin', 'cos', 'tan', 'arcsin', 'arccos',
            'arctan', 'exp', 'log', 'radians', 'degrees', 'ceil',
            'floor', 'sinh', 'cosh', 'tanh']:
    expr_namespace[fcn] = getattr(np, fcn)

id_re = re.compile('[a-zA-Z_][a-zA-Z0-9_]*$')


class Param(object):
    def __init__(self, name, value=0, expr=None, pmin=None, pmax=None,
                 overall=False, delta=0, error=0, correl=None, initexpr=None,
                 finalize=lambda x: x):
        if not id_re.match(name):
            raise UFitError('Parameter name %r is not a valid Python '
                            'identifier' % name)
        if name in expr_namespace:
            raise UFitError('Parameter name %r is reserved' % name)
        self.name = name
        self.value = value
        self.expr = expr
        self.initexpr = initexpr
        self.pmin = pmin
        self.pmax = pmax
        # true if a global parameter for a global fit
        self.overall = overall
        # transform parameter after successful fit
        self.finalize = finalize
        # for backends that support setting parameter increments
        self.delta = delta
        # properties set on fit result
        self.error = error
        self.correl = correl or {}

    @classmethod
    def from_init(cls, name, pdef):
        if isinstance(pdef, cls):
            return pdef
        self = cls(name)
        while not isinstance(pdef, (number_types, string_types)):
            if isinstance(pdef, overall):
                self.overall = True
                pdef = pdef.v
            elif isinstance(pdef, datapar):
                self.expr = 'data.' + pdef.v
                pdef = 0
            elif isinstance(pdef, datainit):
                self.initexpr = 'data.' + pdef.v
                pdef = 0
            elif isinstance(pdef, delta):
                self.delta = pdef.delta
                pdef = pdef.v
            elif isinstance(pdef, tuple) and len(pdef) == 3:
                self.pmin, self.pmax, pdef = pdef
            else:
                raise UFitError('Parameter definition %s not understood' %
                                pdef)
        if isinstance(pdef, string_types):
            self.expr = pdef
        else:
            self.value = pdef
        return self

    def copy(self, newname=None):
        cp = copy.copy(self)
        cp.name = newname or self.name
        cp.finalize = self.finalize
        return cp

    def fix(self):
        self.expr = str(self.value)

    def unfix(self):
        self.expr = None

    def __reduce__(self):
        return (Param, (self.name, self.value, self.expr, self.pmin,
                        self.pmax, self.overall, self.delta, self.error,
                        self.correl, self.initexpr))

    def __str__(self):
        s = '%-15s = %10.5g +/- %10.5g' % (self.name, self.value, self.error)
        if self.expr:
            s += ' (fixed: %s)' % self.expr
        if self.overall:
            s += ' (global)'
        return s

    def __repr__(self):
        if self.expr:
            return '<Param %s = %.5g (expr: %s)>' % (
                self.name, self.value, self.expr)
        return '<Param %s = %.5g +/- %s>' % (
            self.name, self.value, self.error)

    def set_props(self, value, error, expr, pmin, pmax, delta):
        self.value = value
        self.error = error
        self.expr = expr
        self.pmin = pmin
        self.pmax = pmax
        self.delta = delta


# XXX replace by something more safe later
param_eval = eval


def prepare_params(params, meta):
    # find parameters that need to vary
    dependent = {}
    varying = []
    varynames = []
    for p in params:
        if p.initexpr:
            try:
                p.value = param_eval(p.initexpr, {'data': meta})
            except Exception:
                pass  # can happen for heterogeneous data collections
        if p.expr:
            dependent[p.name] = [p.expr, None]
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
            s = '\n'.join('   %s: %s' % (k, v[1]) for (k, v)
                          in iteritems(dependent))
            raise UFitError('Detected unresolved parameter dependencies:\n' + s)
        for p, (expr, _) in listitems(dependent):  # dictionary will change
            try:
                pd[p] = param_eval(expr, pd)
            except NameError as e:
                dependent[p][1] = str(e)
            except AttributeError as e:
                dependent[p][1] = 'depends on data.' + str(e)
            else:
                del dependent[p]
                dep_order.append((p, expr))
    # pd.pop('__builtins__', None)

    return varying, varynames, dep_order, pd


def update_params(parexprs, meta, pd):
    pd.update(expr_namespace)
    pd['data'] = meta
    for p, expr in parexprs:
        pd[p] = param_eval(expr, pd)
    # pd.pop('__builtins__', None)
