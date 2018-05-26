#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Loader for cascade image data."""

import io

from numpy import frombuffer, sqrt


def check_data(fp):
    fp.read(128*128*4)  # cannot decide anything from the pixel data
    footerid = fp.read(18)
    fp.seek(0, 0)
    return footerid == b'\n### NICOS Cascade'


def guess_norm(meta):
    maxmon = 0
    mg = None
    for k in meta:
        if k.startswith('mon') and k[3:].isdigit():
            if meta[k] > maxmon:
                maxmon = meta[k]
                mg = k
    return mg


def read_data(filename, fp):
    meta = {}

    arr = frombuffer(fp.read(128*128*4), '<I4').reshape((128, 128)).astype(float)
    darr = sqrt(arr)

    # now read metadata
    remark = ''
    fp = io.TextIOWrapper(fp)
    for line in fp:
        if line.startswith('#'):
            continue
        items = line.strip().split(None, 2)
        try:
            oval, unit = items[2].split(None, 1)
            val = float(oval)
        except (IndexError, ValueError):
            try:
                oval = items[2]
                val = float(oval)
            except ValueError:
                val = items[2]
            except IndexError:
                continue
        key = items[0]
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

    return arr, darr, meta
