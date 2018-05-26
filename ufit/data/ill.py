#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Load routine for ILL TAS data."""

import io
from warnings import catch_warnings

from numpy import array, genfromtxt, atleast_2d

from ufit import UFitError


def check_data(fp):
    dtline = fp.readline()
    fp.seek(0, 0)
    return dtline.startswith(b'RRRRRRRRRRRR')


def guess_cols(colnames, coldata, meta):
    xg, yg, mg = None, None, None
    if 'CNTS' in colnames:
        yg = 'CNTS'
    if colnames[0] == 'QH':
        deviations = array([(cs.max()-cs.min()) for cs in coldata.T[:4]])
        xg = colnames[deviations.argmax()]
    else:
        xg = colnames[0]
    maxmon = 0
    for i, colname in enumerate(colnames):
        if colname.startswith('M') and colname[1:].isdigit():
            if coldata[:, i].sum() > maxmon:
                maxmon = coldata[:, i].sum()
                mg = colname
    return xg, yg, None, mg


def read_data(filename, fp):
    fp = io.TextIOWrapper(fp, 'ascii', 'ignore')
    line = ''
    xcol = None
    meta = {}
    while line.strip() != 'DATA_:':
        if line.startswith('STEPS:'):
            parts = line[6:].strip().rstrip(',').split(', ')
            for part in parts:
                k, s = part.split('=')
                if float(s.strip()) != 0 or xcol is None:
                    xcol = k[1:]
        elif line.startswith('COMND:'):
            meta['subtitle'] = ' '.join(line[7:].rstrip().lower().split())
        elif line.startswith('TITLE:'):
            meta['title'] = line[6:].strip()
        elif line.startswith('FILE_:'):
            meta['filenumber'] = int(line[6:].strip())
        elif line.startswith('PARAM:'):
            parts = line[6:].strip().rstrip(',').split(',')
            for part in parts:
                k, s = part.split('=')
                meta[k.strip()] = float(s.strip())
        elif line.startswith('INSTR:'):
            meta['instrument'] = line[6:].strip().lower()
        elif line.startswith('EXPNO:'):
            meta['experiment'] = line[6:].strip().lower()
        line = fp.readline()
        if not line:
            break
    all_names = fp.readline().split()
    if not all_names:
        raise UFitError('No data columns found in in file %r' % filename)
    usecols = []
    names = []
    for i, name in enumerate(all_names):
        # XXX have to do flipper handling right
        if name in ('PNT', 'F1', 'F2'):
            continue
        names.append(name)
        usecols.append(i)
    # Berlin implementation adds "Finished ..." in the last line,
    # pretend that it is a comment
    with catch_warnings(record=True) as warnings:
        arr = atleast_2d(genfromtxt(iter(lambda: fp.readline().encode(), b''),
                                    usecols=usecols, comments='F',
                                    invalid_raise=False))
    for warning in warnings:
        print('!!! %s' % warning.message)
    for i, n in enumerate(names):
        meta[n] = arr[:, i].mean()
    meta['environment'] = []
    if 'TT' in meta:
        meta['environment'].append('T = %.3f K' % meta['TT'])
    if 'MAG' in meta:
        meta['environment'].append('B = %.5f T' % meta['MAG'])
    if names[3] == 'EN':
        meta['hkle'] = arr[:, :4]
        deviations = array([(cs.max()-cs.min()) for cs in arr.T[:4]])
        meta['hkle_vary'] = ['h', 'k', 'l', 'E'][deviations.argmax()]
    elif names[0] == 'QH':  # 2-axis mode
        meta['hkle'] = arr[:, :3]
        meta['hkle'] = array([(h, k, l, 0) for (h, k, l) in meta['hkle']])
        deviations = array([(cs.max()-cs.min()) for cs in arr.T[:4]])
        meta['hkle_vary'] = ['h', 'k', 'l', 'E'][deviations.argmax()]
    if len(arr) == 0:
        raise UFitError('No data found in file %r' % filename)
    return names, arr, meta
