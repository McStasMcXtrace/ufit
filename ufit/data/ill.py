#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2020, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Load routine for ILL TAS data."""

import io
import re
from os import path
from warnings import catch_warnings

from numpy import array, genfromtxt, atleast_2d, concatenate

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
        if 'EN' in colnames:
            deviations = array([(cs.max()-cs.min()) for cs in coldata.T[:4]])
        else:
            deviations = array([(cs.max()-cs.min()) for cs in coldata.T[:3]])
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
    meta = {}
    while line.strip() != 'DATA_:':
        if line.startswith('IIIIIIIIIIIIIIIIIII'):
            # D23 format
            fp.seek(0, 0)
            return read_data_d23(filename, fp)
        if line.startswith('COMND:'):
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


# format of D23 data; wildly impractical
def read_data_d23(filename, fp):
    line = fp.readline()
    meta = {'instrument': 'D23'}
    imeta = {}
    arr = []
    after_head = False
    scantype = None
    section = 0
    while True:
        if len(line) == 81 and len(set(line)) == 2:
            # heading
            after_head = True
            section += 1
        elif after_head:
            if section == 1:
                meta['filenumber'] = int(line.split()[0])
            elif section == 2:
                # experiment user
                fp.readline()
                line = fp.readline()
                meta['experiment'] = line.strip('\x00').split()[0]
            elif section == 3:
                # experiment title and "scan type" (can be empty)
                fp.readline()
                line = fp.readline()
                fields = line.split()
                meta['title'] = fields[0]
                if len(fields) > 1:
                    scantype = fields[1]
            elif section == 4:
                # integral metadata, only relevant for interpreting the rest
                nlines = int(line.split()[1])
                valnames = []
                values = []
                for _ in range(nlines):
                    valnames.extend(fp.readline().split())
                for _ in range(nlines):
                    values.extend(map(int, fp.readline().split()))
                imeta = dict(zip(valnames, values))
            elif section == 5:
                # experimental metadata, take all
                nlines = int(line.split()[1])
                valnames = []
                values = []
                for _ in range(nlines):
                    valnames.extend(x for x in re.split(
                        ' {2,}', fp.readline().strip()) if x)
                for _ in range(nlines):
                    values.extend(map(float, fp.readline().split()))
                for (k, v) in zip(valnames, values):
                    meta[k] = v
            elif section == 7:
                # data follows; must be #points * (#detvals + #angles)
                ncols = 3 + imeta['nbang']
                if int(line.split()[0]) != imeta['nkmes'] * ncols:
                    raise ValueError('invalid number of data items')
                line = fp.readline()
                data = []
                while line:
                    data.extend(map(float, line.split()))
                    line = fp.readline()
                arr = array(data).reshape((imeta['nkmes'], ncols))
                break
            after_head = False
        line = fp.readline()
        if not line:
            break

    # check if we have a supplementary .dat file to get the HKL values out
    # (the original file doesn't contain it, and we don't want to implement
    # the UB matrix to calculate it here)
    hkl = None
    if scantype != 'omega' and path.isfile(filename + '.dat'):
        hkl = []
        fp1 = io.open(filename + '.dat', 'rb')
        fp1 = io.TextIOWrapper(fp1, 'ascii', 'ignore')
        for line in fp1:
            hkl.append([float(x) for x in line.split()[:3]])
        hkl = array(hkl)
        meta['hkle'] = array([(h, k, l, 0) for (h, k, l) in hkl])
        deviations = array([(cs.max()-cs.min()) for cs in arr.T[:4]])
        meta['hkle_vary'] = ['h', 'k', 'l', 'E'][deviations.argmax()]

    # reshuffle columns to place the detector last
    arrindices = array(list(range(3, arr.shape[1])) + [1, 2, 0])
    arr = arr[:, arrindices]

    if hkl is not None:
        names = ['QH', 'QK', 'QL']
        arr = concatenate([hkl, arr], 1)
    else:
        names = []
    for i in range(1, 8):
        coltype = imeta['icdesc%d' % i]
        if coltype == 0:
            break
        names.append({
            1: 'GAMMA',
            2: 'OMEGA',
            5: 'CHI',
            -1: 'T',
            -6: 'B',
        }.get(coltype, 'COL_%d' % coltype))
    names.extend(['M1', 'M2', 'CNTS'])
    for i, n in enumerate(names):
        meta[n] = arr[:, i].mean()
    meta['environment'] = []
    if 'Temp-sample' in meta:
        meta['environment'].append('T = %.3f K' % meta['Temp-sample'])
    if 'Mag.field' in meta:
        meta['environment'].append('B = %.5f T' % meta['Mag.field'])

    if len(arr) == 0:
        raise UFitError('No data found in file %r' % filename)
    return names, arr, meta
