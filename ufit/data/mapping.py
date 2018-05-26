#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Routine for creating data mappings."""

import numpy as np
from numpy import array, mgrid, clip

from matplotlib.cbook import flatten


def bin_mapping(x, y, runs, usemask=True, log=False, xscale=1, yscale=1,
                interpolate=100, minmax=None):
    from scipy.interpolate import griddata as griddata_sp
    if usemask:
        xss = array(list(flatten(run['col_'+x][run.mask] for run in runs))) * xscale
        yss = array(list(flatten(run['col_'+y][run.mask] for run in runs))) * yscale
        if log:
            zss = list(flatten(np.log10(run.y)[run.mask] for run in runs))
        else:
            zss = list(flatten(run.y[run.mask] for run in runs))
    else:
        # XXX duplication
        xss = array(list(flatten(run['col_'+x] for run in runs))) * xscale
        yss = array(list(flatten(run['col_'+y] for run in runs))) * yscale
        if log:
            zss = list(flatten(np.log10(run.y) for run in runs))
        else:
            zss = list(flatten(run.y for run in runs))
    if minmax is not None:
        if log:
            minmax = list(map(np.log10, minmax))
        zss = clip(zss, minmax[0], minmax[1])
    interpolate = interpolate * 1j
    xi, yi = mgrid[min(xss):max(xss):interpolate,
                   min(yss):max(yss):interpolate]
    zi = griddata_sp(array((xss, yss)).T, zss, (xi, yi))
    return xss/xscale, yss/yscale, xi/xscale, yi/yscale, zi
