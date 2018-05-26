#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Load routine for simple whitespace-separated column data files."""

import io
from os import path

from numpy import loadtxt


def guess_cols(colnames, coldata, meta):
    if len(colnames) > 2:
        dycol = colnames[2]
    else:
        dycol = None
    return colnames[0], colnames[1], dycol, None


def check_data_simple(fp, sep=None):
    line = fp.readline()
    # find the first non-comment line
    while line.startswith((b'#', b'%')):
        line = fp.readline()
    line2 = fp.readline()
    fp.seek(0, 0)
    # must be values in non-comment line, or the line after
    try:
        [float(x) for x in line.split(sep)]
    except ValueError:
        try:
            [float(x) for x in line2.split(sep)]
        except ValueError:
            return False
    return True


def check_data(fp):
    return check_data_simple(fp, None)


def read_data_simple(filename, fp, sep=None):
    fp = io.TextIOWrapper(fp, 'ascii', 'ignore')
    line1 = ''
    line2 = fp.readline()
    skiprows = 0
    # find the first non-comment line
    while line2.startswith(('#', '%')):
        line1 = line2
        line2 = fp.readline()
        skiprows += 1
    # now line2 is the first non-comment line (but may be column names)

    # if there are comments, line1 will have the comment char
    comments = '#'
    if line1.startswith(('#', '%')):
        comments = line1[0]
        line1 = line1[1:]
    try:
        [float(x) for x in line2.split()]
    except ValueError:
        # must be column names
        colnames = line2.split()
        skiprows += 1
    else:
        # line1 might have column names
        if line1:
            colnames = line1.split()
        else:
            colnames = []
    fp.seek(0, 0)
    arr = loadtxt(fp, ndmin=2, skiprows=skiprows, comments=comments)
    # if number of colnames is not correct, discard them
    if len(colnames) != arr.shape[1]:
        colnames = ['Column %d' % i for i in range(1, arr.shape[1]+1)]
    meta = {}
    meta['filedesc'] = path.basename(filename)
    return colnames, arr, meta


def read_data(filename, fp):
    return read_data_simple(filename, fp, None)
