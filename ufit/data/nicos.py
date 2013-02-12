#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Load routine for NICOS2 data."""

import time
from numpy import loadtxt

from ufit import UFitError


def check_data(fp):
    dtline = fp.readline()
    fp.seek(0, 0)
    return dtline.startswith('### NICOS data file')


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
            meta[key] = val
    colnames = fp.readline()[1:].split()
    colunits = fp.readline()[1:].split()
    def convert_value(s):
        try:
            return float(s)
        except ValueError:
            return 0.0  # XXX care for string columns?!
    cvdict = dict((i, convert_value) for i in range(len(colnames))
                  if colnames[i] != ';')
    colnames = [name for name in colnames if name != ';']
    colunits = [unit for unit in colunits if unit != ';']
    usecols = cvdict.keys()
    coldata = loadtxt(fp, converters=cvdict, usecols=usecols)
    if 'Ts' in colnames:
        tindex = colnames.index('Ts')
        meta['temperature'] = coldata[:,tindex].mean()
    if 'sT' in colnames:
        tindex = colnames.index('sT')
        meta['temperature'] = coldata[:,tindex].mean()
    if 'B' in colnames:
        tindex = colnames.index('B')
        meta['magfield'] = coldata[:,tindex].mean()
    return colnames, coldata, meta
