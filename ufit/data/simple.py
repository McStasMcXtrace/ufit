#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Load routine for simple three-column data files."""

from numpy import loadtxt, sqrt

from ufit import UFitError


def check_data(fp):
    dtline = fp.readline()
    try:
        x, y, dy = map(float, dtline.split())
    except (ValueError, TypeError):
        return False
    fp.seek(0, 0)
    return True


def read_data(filename, fp):
    colnames = ['x', 'y', 'dy']
    arr = loadtxt(fp, ndmin=2)
    return colnames, arr, {}
