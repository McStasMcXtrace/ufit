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
    line1 = fp.readline()
    line2 = fp.readline()
    fp.seek(0, 0)
    # must be values in second line
    try:
        values = map(float, line2.split())
    except ValueError:
        return False
    # optional header in first line
    if line1.startswith(('#', '%')):
        line1 = line1[1:]
    if len(line1.split()) != len(values):
        return False
    return True


def guess_cols(colnames, coldata, meta):
    if len(colnames) > 2:
        dycol = colnames[2]
    else:
        dycol = None
    return colnames[0], colnames[1], dycol, None


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
        colnames = None
    arr = loadtxt(fp, ndmin=2)
    if colnames is None:
        colnames = ['Column %d' % i for i in range(1, arr.shape[1]+1)]
    return colnames, arr, {}
