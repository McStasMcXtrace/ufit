#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Utility functions and classes."""

import re
from os import path


def get_chisqr(fcn, x, y, dy, params):
    paramvalues = dict((p.name, p.value) for p in params)
    sum_sqr = ((fcn(paramvalues, x) - y)**2 / dy**2).sum()
    nfree = len(y) - sum(1 for p in params if not p.expr)
    return sum_sqr / nfree


class attrdict(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(key)


_missing = object()


class cached_property(object):
    """A decorator that converts a function into a lazy property.  The
    function wrapped is called the first time to retrieve the result
    and then that calculated result is used the next time you access
    the value.
    """

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value


numor_re = re.compile(r'\d+')


def extract_template(fn):
    bn = path.basename(fn)
    dn = path.dirname(fn)
    m = list(numor_re.finditer(bn))
    if not m:
        dtempl = fn
        numor = 0
    else:
        b, e = m[-1].span()
        dtempl = path.join(dn, bn[:b] + '%%0%dd' % (e-b) + bn[e:])
        numor = int(m[-1].group())
    return dtempl, numor
