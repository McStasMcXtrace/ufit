#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Load routine for NICOS2 data."""

import io
import time

from numpy import array, loadtxt

from ufit import UFitError


def check_data(fp):
    dtline = fp.readline()
    fp.seek(0, 0)
    return dtline.startswith(b'### NICOS data file')


def _hkle_index(colnames):
    # find the index of the "h" column or -1 if it's not a qscan
    # NOTE: don't support "h" in a position other than 0 since this would
    # recognize all scans as Q scans even if the HKL device is just added
    # for monitoring purposes.
    # if 'h' in colnames:
    if colnames and colnames[0] == 'h':
        qhindex = 0  # colnames.index('h')
        if qhindex < len(colnames) - 3 and colnames[qhindex+3] == 'E':
            return qhindex
    return -1


def guess_cols(colnames, coldata, meta):
    xg, yg, mg = None, None, None
    qhindex = _hkle_index(colnames)
    if qhindex > -1:
        deviations = array([cs.max() - cs.min()
                            for cs in coldata.T[qhindex:qhindex+4]])
        xg = colnames[qhindex + deviations.argmax()]
    else:
        xg = colnames[0]
    maxmon = 0
    maxcts = 0
    for i, colname in enumerate(colnames):
        if colname.startswith('mon'):
            if coldata[:, i].sum() > maxmon:
                maxmon = coldata[:, i].sum()
                mg = colname
        if colname.startswith(('det', 'ctr', 'psd.roi')):
            if coldata[:, i].sum() > maxcts:
                maxcts = coldata[:, i].sum()
                yg = colname
    if yg is None:
        yg = colnames[1]
    return xg, yg, None, mg


def read_data(filename, fp):
    fp = io.TextIOWrapper(fp, 'ascii', 'ignore')
    meta = {}
    dtline = fp.readline()
    if not dtline.startswith('### NICOS data file'):
        raise UFitError('%r does not appear to be a NICOS data file' %
                        filename)
    ctime = time.mktime(time.strptime(
        dtline[len('### NICOS data file, created at '):].strip(),
        '%Y-%m-%d %H:%M:%S'))
    meta['created'] = ctime
    remark = ''
    for line in iter(fp.readline, ''):
        if line.startswith('### Scan data'):
            break
        if line.startswith('# '):
            items = line.strip().split(None, 3)
            try:
                oval, unit = items[3].split(None, 1)
                val = float(oval)
            except (IndexError, ValueError):
                try:
                    oval = items[3]
                    val = float(oval)
                except ValueError:
                    val = items[3]
                except IndexError:
                    continue
                unit = None
            key = items[1]
            if key.endswith(('_offset', '_precision')):
                # we don't need these for fitting
                continue
            if key.endswith('_value'):
                key = key[:-6]
            if key.endswith('_instrument'):
                meta['instrument'] = oval.lower()
                continue
            elif key.endswith('_proposal'):
                meta['experiment'] = oval.lower()
            elif key.endswith('_samplename'):
                meta['title'] = oval
            elif key.endswith('_remark'):
                remark = oval
            elif key == 'number':
                meta['filenumber'] = int(oval)
                continue
            elif key == 'info':
                meta['subtitle'] = val
                continue
            meta[key] = val
    if remark and 'title' in meta:
        meta['title'] += ', ' + remark
    colnames = fp.readline()[1:].split()
    colunits = fp.readline()[1:].split()
    return _nicos_common_load(fp, colnames, colunits, meta, '#')


def _nicos_common_load(fp, colnames, colunits, meta, comments):
    def convert_value(s):
        try:
            return float(s)
        except ValueError:
            return 0.0
    cvdict = dict((i, convert_value) for i in range(len(colnames))
                  if colnames[i] != ';')
    colnames = [name for name in colnames if name != ';']
    colunits = [unit for unit in colunits if unit != ';']
    usecols = list(cvdict)
    coldata = loadtxt(fp, converters=cvdict, usecols=usecols, ndmin=2,
                      comments=comments)
    if not coldata.size:
        raise UFitError('empty data file')
    cols = dict((name, coldata[:, i]) for (i, name) in enumerate(colnames))
    meta['environment'] = []
    for col in cols:
        meta[col] = cols[col].mean()
    for tcol in ['Ts', 'sT', 'T_ccr5_A', 'T_ccr5_B', 'sensor1']:
        if tcol in cols:
            meta['environment'].append('T = %.3f K' % meta[tcol])
            break
    if 'B' in cols:
        meta['environment'].append('B = %.3f K' % meta['B'])
    qhindex = _hkle_index(colnames)
    if qhindex > -1:
        meta['hkle'] = coldata[:, qhindex:qhindex+4]
        deviations = array([cs.max() - cs.min()
                            for cs in coldata.T[qhindex:qhindex+4]])
        xg = colnames[qhindex + deviations.argmax()]
        meta['hkle_vary'] = xg
    return colnames, coldata, meta
