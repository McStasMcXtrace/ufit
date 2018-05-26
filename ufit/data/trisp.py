#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Load routine for TRISP spin-echo data."""

import io

from numpy import array, loadtxt, zeros

from ufit import UFitError


def check_data(fp):
    dtline = fp.readline()
    fp.seek(0, 0)
    return dtline.startswith(b'pnt  ')


def guess_cols(colnames, coldata, meta):
    xg, yg, dvg, mg = None, 'c1', None, 'mon'
    if 'QH' in colnames:
        qhindex = colnames.index('QH')
        deviations = array([(cs.max()-cs.min())
                            for cs in coldata.T[qhindex:qhindex+4]])
        xg = colnames[qhindex + deviations.argmax()]
    elif colnames[0] == 'TC1' and colnames[1] == 'TC4':
        xg = 'TC4'
    else:
        xg = colnames[0]
    if 'c1_1' in colnames:
        mg = 'mon_1'
        yg = 'c1_1'
    return xg, yg, None, mg


def good_ycol(c):
    return c == 'c1'


def read_data(filename, fp):
    fp = io.TextIOWrapper(fp, 'ascii', 'ignore')
    line = ''
    meta = {}
    infofp = io.open(filename[:-4] + '.log', 'r',
                     encoding='ascii', errors='ignore')
    # first line in scan info
    line = infofp.readline()
    meta['subtitle'] = ' '.join(line.lower().split())
    meta['title'] = ''  # nothing here
    meta['instrument'] = 'trisp'
    while not line.startswith('Limits'):
        line = infofp.readline()
        if '-----' in line:
            continue
        parts = line.split()
        try:
            if len(parts) == 2:
                meta[parts[0]] = float(parts[1])
            elif len(parts) == 3:  # encoder target, value: so take value
                meta[parts[0]] = float(parts[2])
        except ValueError:
            pass
    names = fp.readline().split()
    pal = 'pal' in names
    # file with polarization analysis?
    if not names:
        raise UFitError('No data columns found in file %r' % filename)
    usecols = list(range(len(names)))
    if names[0] == 'pnt':
        usecols = list(range(1, len(names)))
        names = names[1:]
    arr = loadtxt(fp, ndmin=2, usecols=usecols)
    for i, n in enumerate(names):
        meta[n] = arr[:, i].mean()
    meta['environment'] = []
    if 'TTA' in meta:
        meta['environment'].append('T = %.3f K' % meta['TTA'])
    if len(arr) == 0:
        raise UFitError('No data found in file %r' % filename)
    if pal:
        if 'QH' not in names:
            raise UFitError('Polarization data without QHKLE not supported')
        nfixed = names.index('E')  # fixed columns (same for all PA points)
        pal_values = set(arr[:, 0])
        npal = len(pal_values)  # number of PA points
        names_new = names[1:nfixed+1]
        nvary = arr.shape[1] - nfixed - 1  # without pal and fixed columns
        arr_new = zeros((arr.shape[0]//npal, nfixed + nvary*npal))
        for pal_value in sorted(pal_values):
            for name in names[nfixed+1:]:
                names_new.append(name + '_%d' % pal_value)
            arr_new[:, nfixed+(pal_value-1)*nvary:nfixed+pal_value*nvary] = \
                arr[pal_value-1::npal, nfixed+1:]
        # take fixed points from first PA point
        arr_new[:, :nfixed] = arr[::npal, 1:nfixed+1]
        names = names_new
        arr = arr_new
    if names[0] == 'QH':
        meta['hkle'] = arr[:, :4]
        deviations = array([(cs.max()-cs.min()) for cs in arr.T[:4]])
        meta['hkle_vary'] = ['h', 'k', 'l', 'E'][deviations.argmax()]
    return names, arr, meta
