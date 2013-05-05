#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Load routine for ILL TAS data."""

from numpy import array, loadtxt

from ufit import UFitError


def check_data(fp):
    dtline = fp.readline()
    fp.seek(0, 0)
    return dtline.startswith('RRRRRRRRRRRR')


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
            if coldata[:,i].sum() > maxmon:
                maxmon = coldata[:,i].sum()
                mg = colname
    return xg, yg, None, mg


def read_data(filename, fp):
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
            meta['info'] = ' '.join(line[7:].rstrip().lower().split())
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
    meta['filedesc'] = '%s:%s:%s' % (meta.get('instrument', ''),
                                     meta.get('experiment', ''),
                                     meta.get('filenumber'))
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
    arr = loadtxt(fp, ndmin=2, usecols=usecols, comments='F')
    for i, n in enumerate(names):
        meta[n] = arr[:,i].mean()
    meta['environment'] = []
    if 'TT' in meta:
        meta['environment'].append('T = %.3f K' % meta['TT'])
    if names[3] == 'EN':
        meta['hkle'] = arr[:,:4]
    if len(arr) == 0:
        raise UFitError('No data found in file %r' % filename)
    return names, arr, meta
