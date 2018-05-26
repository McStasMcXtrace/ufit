#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Load routine for OLD NICOS data."""

import io
import time

from ufit import UFitError
from ufit.data.nicos import _nicos_common_load

# guess_cols is the same as for new nicos format

from ufit.data.nicos import guess_cols


def check_data(fp):
    dtline = fp.readline()
    fp.seek(0, 0)
    # not sure if it is enough, but it is working
    return dtline.startswith(b'filename')


mapping = {
    'name': 'title',
    '1st orientation reflection': 'Sample_orient1',
    '2nd orientation reflection': 'Sample_orient2',
    'zone axis for scattering plane': 'Sample_zoneaxis',
    'created at': 'created',
    'PSI0 (deg)': 'Sample_psi0',
    'psi0 (deg)': 'Sample_psi0',
    'a,b,c (A)': 'Sample_lattice',
    'alpha,beta,gamma (deg)': 'Sample_angles',
    'Scattering sense': 'scatteringsense',
    'mono focussing mode': 'mono_focus',
    'ana  focussing mode': 'ana_focus',
    'TAS operation mode': 'opmode',
}

blacklist = set([
    'installation', 'sourcetype', 'sourcepower', 'moderator',
    'moderator temperature', 'beamtube', 'white flux@monochr.',
    'beam tube width', 'beam tube height', 'responsable',
    'phone', 'fax', 'mth  (A1) (deg)', 'mtt  (A2) (deg)',
    'psi  (A3) (deg)', 'phi  (A4) (deg)', 'ath  (A5) (deg)',
    'att  (A6) (deg)', 'sth  (A3) (deg)', 'stt  (A4) (deg)',
])


def read_data(filename, fp):
    fp = io.TextIOWrapper(fp, 'ascii', 'ignore')
    meta = {}
    first_pos = fp.tell()
    dtline = fp.readline()
    fp.seek(first_pos)
    if not dtline.startswith('filename'):
        raise UFitError('%r does not appear to be an old NICOS data file' % filename)
    for line in iter(fp.readline, ''):
        # finished, go for data
        if line.startswith('scan data'):
            break
        # skip these lines
        if line.startswith(('***', '[', 'Sample information',
                            'instrument general setup at file creation',
                            'offsets of main axes')):
            continue
        # POLARIZATION, not implemented:
        # if line.startswith('counting for switching devices'): # polarized measurements!
        #    self.pol_devices = [d.strip() for d in line.split(']')[0].split('[')[1].split(', ')]
        #    self.pol_states = []
        #    self.polarized = True
        #    for s in line.split('states ')[1][1:-1].split('], ['):
        #        s = [d.strip() for d in s.split(', ')]
        #        ts = {}
        #        for i in range(len(self.pol_devices)):
        #            ts[self.pol_devices[i]] = s[i]
        #        self.pol_states.append(ts)

        try:
            key, value = line.split(':', 1)
        except ValueError:
            print('ignored line: %r' % line)
            continue
        key = key.strip()
        value = value.strip()

        # some values are not important
        if key in blacklist:
            continue

        # some value names should be mapped
        if key in mapping:
            key = mapping[key]

        parts = value.split()
        if not parts:
            continue
        if key in ('ss1', 'ss2'):
            try:
                for i, side in enumerate(('left', 'right', 'bottom', 'top')):
                    meta['%s_%s' % (key, side)] = float(parts[i])
                meta[key] = tuple(float(b) for b in parts[:4])
            except Exception:
                continue
        elif value.endswith(('mm', 'deg', 'deg.', 'A-1', 'THz', 'meV', 'T', 'K',
                             'bar', '%', 's', 'min', 'min.', 'A')):
            try:
                meta[key] = float(parts[0])
            except ValueError:
                meta[key] = parts[0]
        else:
            meta[key] = value

    # convert some values
    if 'created' in meta:
        meta['created'] = time.mktime(time.strptime(meta['created'], '%m/%d/%Y %H:%M:%S'))
    if 'filename' in meta:
        meta['filename'] = meta['filename'].strip("'")
        meta['filenumber'] = int(meta['filename'].split("_")[1])

    # read data
    meta['subtitle'] = fp.readline().strip()
    colnames = fp.readline().split()
    colunits = fp.readline().split()

    return _nicos_common_load(fp, colnames, colunits, meta, '*')
