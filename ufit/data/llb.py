#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Load routine for LLB TAS data (binary format)."""

import struct
from time import mktime

from numpy import array, sqrt

# format of the first 10 bytes of the header
DATEFMT = struct.Struct('<hhhhh')

# names the header floats starting at position 92; None means unmapped
# CAUTION: some of these names are only correct for 1T
FIELDS = \
    ['dm', 'da', 'etam', 'etaa', 'zme', 'zea', 'zad', 'he', 've', 'hd', 'vd'] + \
    [None] * 12 + \
    ['h0', 'h1', 'h2', 'h3', 'v0', 'v1', 'v2', 'v3', 'eta1', 'eta2', 'eta3'] + \
    [None] * 12 + \
    ['ax', 'ay', 'az', 'alfa', 'beta', 'gama', 'etas'] + \
    [None] * 18 + \
    ['ze1', 'ze2', 'za1', 'za2'] + \
    [None] * 4 + \
    ['zgi', 'zgs', None, 'zca']

# format of a single point (92 bytes long)
POINTFMT = struct.Struct('<hffffffffffffffhffffffff')
POINTFIELDS = ['qh', 'qk', 'ql', 'en', 'ki', 'm1', 'm2',
               'e1', 'e2', 'a1', 'a2', 'time', 'mon', 'counts', 'xx', 'T']

# format for 4F with double monochromator
POINTFMT_alt = struct.Struct('<hffffffffffffffffhffffff')
POINTFIELDS_alt = ['qh', 'qk', 'ql', 'en', 'ki', 'm1', 'm2', 'm3', 'm4',
                   'e1', 'e2', 'a1', 'a2', 'time', 'mon', 'counts', 'xx', 'T']


def check_data(fp):
    # the first 10 bytes are a packed date; check that for plausibility
    dates = fp.read(10)
    fp.seek(0, 0)
    if len(dates) < 10:
        return False
    d, m, y, hh, mm = DATEFMT.unpack(dates)
    return (1900 < y < 2100) and (1 <= m <= 12) and (1 <= d <= 31)


def guess_cols(colnames, coldata, meta):
    return meta['hkle_vary'], 'counts', None, 'mon'


def _float_fmt(x):
    if x == 0:
        return '0'
    else:
        return '%.3f' % x


def read_data(filename, fp):
    meta = {}
    dates = fp.read(10)
    d, m, y, hh, mm = DATEFMT.unpack(dates)
    meta['created'] = mktime((y, m, d, hh, mm, 0, 0, 0, 0))
    titre = fp.read(80).strip()
    fp.read(2)  # skip null bytes
    meta['title'] = titre.decode('ascii', 'ignore')
    headerfields = struct.unpack('<115f', fp.read(460))
    for i, name in enumerate(FIELDS):
        if name is None:
            continue
        meta[name] = headerfields[i]
    # reconstruct run command from header fields
    meta['subtitle'] = 'run q=(%s %s %s %s) dq=(%s %s %s %s) ' % \
                       tuple(map(_float_fmt, headerfields[92:100]))
    meta['subtitle'] += 'np=%d m=%d ' % headerfields[100:102]
    if headerfields[102] == 1:
        # const ki
        meta['subtitle'] += 'ki=%.3f' % headerfields[103]
    else:
        meta['subtitle'] += 'kf=%.3f' % headerfields[103]
    parr = []
    pointfmt = POINTFMT
    pointfields = POINTFIELDS
    for i, point in enumerate(iter(lambda: fp.read(POINTFMT.size), b'')):
        if i == 0:
            unp = pointfmt.unpack(point)
            if unp[15] != 1:
                pointfmt = POINTFMT_alt
                pointfields = POINTFIELDS_alt
        coords = pointfmt.unpack(point)[:len(pointfields) + 1]
        parr.append(coords + (coords[1] + 0.5*coords[2],
                              0.5*sqrt(3)*coords[2]))
    parr = array(parr)[:, 1:]
    for i, name in enumerate(pointfields):
        meta[name] = parr[:, i].mean()
    meta['environment'] = ['T = %.3f K' % meta['T']]
    meta['hkle'] = parr[:, 0:4]
    deviations = array([cs.max() - cs.min() for cs in parr.T[0:4]])
    xg = pointfields[deviations.argmax()]
    meta['hkle_vary'] = xg
    return pointfields + ['qx', 'qy'], parr, meta
