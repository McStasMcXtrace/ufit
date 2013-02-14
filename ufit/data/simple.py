#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Load routine for simple whitespace-separated column data files."""

from numpy import loadtxt


def check_data(fp):
    dtline = fp.readline()
    try:
        map(float, dtline.split())
    except ValueError:
        fp.seek(0, 0)
        return False
    fp.seek(0, 0)
    return True


def read_data(filename, fp):
    dtline = fp.readline()
    try:
        if dtline.startswith(('#', '%')):
            dtline = dtline[1:]
        map(float, dtline.split())
    except ValueError:
        # must be headers...
        colnames = dtline.split()
    else:
        fp.seek(0, 0)
    arr = loadtxt(fp, ndmin=2)
    return colnames, arr, {}
