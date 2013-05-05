#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Load routine for NICOS2 data."""

import time
from numpy import array, loadtxt

from ufit import UFitError


def check_data(fp):
    dtline = fp.readline()
    fp.seek(0, 0)
    return dtline.startswith('### NICOS data file')


def guess_cols(colnames, coldata, meta):
    xg, yg, mg = None, None, None
    if colnames[0] == 'h':
        deviations = array([(cs.max()-cs.min()) for cs in coldata.T[:4]])
        xg = colnames[deviations.argmax()]
    else:
        xg = colnames[0]
    maxmon = 0
    maxcts = 0
    for i, colname in enumerate(colnames):
        if colname.startswith('mon'):
            if coldata[:,i].sum() > maxmon:
                maxmon = coldata[:,i].sum()
                mg = colname
        if colname.startswith(('det', 'ctr', 'psd.total')):
            if coldata[:,i].sum() > maxcts:
                maxcts = coldata[:,i].sum()
                yg = colname
    if yg is None:
        yg = colnames[1]
    return xg, yg, None, mg


def read_data(filename, fp):
    meta = {}
    dtline = fp.readline()
    if not dtline.startswith('### NICOS data file'):
        raise UFitError('%r does not appear to be a NICOS data file' %
                        filename)
    ctime = time.mktime(time.strptime(
        dtline[len('### NICOS data file, created at '):].strip(),
        '%Y-%m-%d %H:%M:%S'))
    meta['created'] = ctime
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
            elif key.endswith('_proposal'):
                meta['experiment'] = oval.lower()
            elif key.endswith('_samplename'):
                meta['title'] = oval
            elif key == 'number':
                meta['filenumber'] = int(oval)
            # 'info' key already has the right name
            meta[key] = val
    meta['filedesc'] = '%s:%s:%s' % (meta.get('instrument', ''),
                                     meta.get('experiment', ''),
                                     meta.get('filenumber'))
    colnames = fp.readline()[1:].split()
    colunits = fp.readline()[1:].split()
    def convert_value(s):
        try:
            return float(s)
        except ValueError:
            return 0.0
    cvdict = dict((i, convert_value) for i in range(len(colnames))
                  if colnames[i] != ';')
    colnames = [name for name in colnames if name != ';']
    colunits = [unit for unit in colunits if unit != ';']
    usecols = cvdict.keys()
    coldata = loadtxt(fp, converters=cvdict, usecols=usecols, ndmin=2)
    cols = dict((name, coldata[:,i]) for (i, name) in enumerate(colnames))
    meta['environment'] = []
    for col in cols:
        meta[col] = cols[col].mean()
    if 'Ts' in cols:
        meta['environment'].append('T = %.3f K' % meta['Ts'])
    elif 'sT' in cols:
        meta['environment'].append('T = %.3f K' % meta['sT'])
    if 'B' in cols:
        meta['environment'].append('B = %.3f K' % meta['B'])
    if colnames[3] == 'E':
        meta['hkle'] = coldata[:,:4]
    return colnames, coldata, meta
