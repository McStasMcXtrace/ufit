#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2014, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Load routine for simple whitespace-separated column data files."""

from os import path

from numpy import loadtxt


def guess_cols(colnames, coldata, meta):
    if len(colnames) > 2:
        dycol = colnames[2]
    else:
        dycol = None
    return colnames[0], colnames[1], dycol, None


def check_data_simple(fp, sep=None):
    line1 = fp.readline()
    line2 = fp.readline()
    # find the first non-comment line
    while line2.startswith(('#', '%')):
        line1 = line2
        line2 = fp.readline()
    fp.seek(0, 0)
    # must be values in second line
    try:
        values = map(float, line2.split(sep))
    except ValueError:
        return False
    # optional header in first line
    if line1.startswith(('#', '%')):
        line1 = line1[1:]
    if len(line1.split(sep)) != len(values):
        return False
    return True

def check_data(fp):
    return check_data_simple(fp, None)


def read_data_simple(filename, fp, sep=None):
    line1 = fp.readline()
    line2 = fp.readline()
    # find the first non-comment line
    while line2.startswith(('#', '%')):
        line1 = line2
        line2 = fp.readline()
    # now line2 is definitely a data line and line1 *may* be headers
    comments = '#'
    try:
        if line1.startswith(('#', '%')):
            comments = line1[0]
            line1 = line1[1:]
        map(float, line1.split())
    except ValueError:
        # must be headers...
        colnames = line1.split()
    fp.seek(0, 0)
    arr = loadtxt(fp, ndmin=2, comments=comments)
    if colnames is None:
        colnames = ['Column %d' % i for i in range(1, arr.shape[1]+1)]
    else:
        # clip to actual number of columns
        colnames = colnames[:arr.shape[1]]
    meta = {}
    meta['filedesc'] = path.basename(filename)
    return colnames, arr, meta

def read_data(filename, fp):
    return read_data_simple(filename, fp, None)
