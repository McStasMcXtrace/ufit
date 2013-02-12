#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Utility functions and classes."""


def prepare_data(data, limits):
    if limits == (None, None):
        return data.x, data.y, data.dy
    if limits[0] is None:
        indices = data.x <= limits[1]
    elif limits[1] is None:
        indices = data.x >= limits[0]
    else:
        indices = (data.x >= limits[0]) & (data.x <= limits[1])
    return data.x[indices], data.y[indices], data.dy[indices]


def get_chisqr(fcn, x, y, dy, params):
    paramdict = dict((p.name, p.value) for p in params)
    sum_sqr = ((fcn(paramdict, x) - y)**2 / dy**2).sum()
    nfree = len(y) - sum(1 for p in params if not p.expr)
    return sum_sqr / nfree


class attrdict(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError
