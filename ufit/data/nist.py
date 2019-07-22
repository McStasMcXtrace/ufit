#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2019, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Load routine for NIST data files."""

import io
import re
import shlex

from numpy import loadtxt, array, concatenate, ones


def guess_cols(colnames, coldata, meta):
    mg = 'Mon'
    if 'hkle' in meta:
        xg = {'h': 'Q(x)', 'k': 'Q(y)', 'l': 'Q(z)', 'E': 'E'}[meta['hkle_vary']]
    else:
        xg = colnames[0]
    yg = None
    if 'Counts' in colnames:
        yg = 'Counts'
    elif 'COUNTS' in colnames:
        yg = 'COUNTS'
    return xg, yg, None, mg


def check_data(fp):
    fp.readline()
    line = fp.readline()
    fp.seek(0, 0)
    # on the first line is always name filename, on the second line
    # the description for it
    return line.startswith(b'  Filename')


def _maybe_float(text):
    try:
        return float(text)
    except ValueError:
        return text


def _read_meta(fp):
    # Read a single line of metadata, with the field names below
    values = shlex.split(fp.readline())
    fp.readline()
    return values


def read_data(filename, fp):
    fp = io.TextIOWrapper(fp, 'ascii', 'ignore')

    meta = {}
    meta['instrument'] = 'NIST'

    # metadata lines
    meta1 = _read_meta(fp)
    m = re.match(r'^(\D+)(\d+)', meta1[0])
    meta['experiment'] = m.group(1)
    meta['filenumber'] = int(m.group(2))
    meta['timestamp'] = meta1[1]
    meta['scantype'] = meta1[2]
    meta['title'] = fp.readline()

    meta2 = _read_meta(fp)
    meta['collimation'] = '-'.join(meta2[:4])
    meta['mosaic'] = '-'.join(meta2[4:7])
    meta['orientation'] = ' '.join(meta2[7:])

    meta3 = _read_meta(fp)
    meta['lattice'] = ' '.join(meta3[:3])
    meta['angles'] = ' '.join(meta3[3:])

    meta4 = _read_meta(fp)
    meta['temp'] = float(meta4[5])
    meta['delta_temp'] = float(meta4[6])

    meta5 = _read_meta(fp)
    meta['field'] = float(meta5[6])

    # principal axes
    if meta1[2] == 'B':
        mon = float(meta1[3])
        for ax in range(1, 7):
            meta['A%d' % ax] = float(fp.readline().split()[1])
        fp.readline()  # unimportant
    elif meta1[2] == 'Q':
        mon = float(meta1[3])
    else:
        raise Exception('unknown scan type %r' % meta1[2])

    colnames = fp.readline().split()
    arr = loadtxt(fp, ndmin=2)
    # if number of colnames is not correct, discard them
    if len(colnames) != arr.shape[1]:
        colnames = ['Column %d' % i for i in range(1, arr.shape[1]+1)]

    # synthesize monitor column
    colnames += ['Mon']
    arr = concatenate((arr, ones((len(arr), 1)) * mon), 1)

    cols = dict((name, arr[:, i]) for (i, name) in enumerate(colnames))
    meta['environment'] = []
    if 'Q(x)' in colnames:
        meta['hkle'] = arr[:, (0, 1, 2, 3)]
        deviations = array([(cs.max()-cs.min()) for cs in meta['hkle'].T])
        meta['hkle_vary'] = ['h', 'k', 'l', 'E'][deviations.argmax()]
    for col in cols:
        meta[col] = cols[col].mean()
    for tcol in ['TEMP', 'T-act']:
        if tcol in cols:
            meta['environment'].append('T = %.3f K' % meta[tcol])
            break

    return colnames, arr, meta
