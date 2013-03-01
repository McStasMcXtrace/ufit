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
        try:
            if len(parts) == 2:
                meta[parts[0]] = float(parts[1])
            elif len(parts) == 3:  # encoder target, value
                                   # so take value
                meta[parts[0]] = float(parts[2])
        except ValueError:
            pass
    names = fp.readline().split()
    if not names:
        raise UFitError('No data columns found in file %r' % filename)
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
        raise UFitError('No data found in file %r' % filename)
    return names, arr, meta
