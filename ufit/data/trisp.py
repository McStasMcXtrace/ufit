#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Load routine for TRISP spin-echo data."""

from numpy import loadtxt

from ufit import UFitError


def check_data(fp):
    dtline = fp.readline()
    fp.seek(0, 0)
    return dtline.startswith('pnt  ')


def good_ycol(c):
    return c == 'c1'


def read_data(filename, fp):
    line = ''
    xcol = None
    meta = {}
    infofp = open(filename[:-4] + '.log', 'rb')
    # first line in scan info
    line = infofp.readline()
    meta['info'] = ' '.join(line.lower().split())
    meta['title'] = ''  # nothing here
    meta['instrument'] = 'trisp'
    meta['experiment'] = ''
    while not line.startswith('Limits'):
        line = infofp.readline()
        if '-----' in line:
            continue
        parts = line.split()
        if len(parts) != 2:
            continue
        try:
            meta[parts[0]] = float(parts[1])
        except ValueError:
            pass
    names = fp.readline().split()
    # XXX make error message style consistent
    if not names:
        raise UFitError('No columns in file')
    usecols = range(len(names))
    if names[0] == 'pnt':
        usecols = range(1, len(names))
        names = names[1:]
    arr = loadtxt(fp, ndmin=2, usecols=usecols)
    for i, n in enumerate(names):
        meta[n] = arr[:,i].mean()
    meta['environment'] = []
    if 'TTA' in meta:
        meta['environment'].append('T = %.3f K' % meta['TTA'])
    if len(arr) == 0:
        raise UFitError('No data in file')
    return names, arr, meta
