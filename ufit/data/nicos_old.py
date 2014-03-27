#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2014, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Load routine for OLD NICOS data."""

import re

from ufit import UFitError
from ufit.data.nicos import _nicos_common_load

meta_re = re.compile(r'^\s*([^:]*?)\s*:\s*(.*?)\s*$')

def check_data(fp):
    dtline = fp.readline()
    fp.seek(0, 0)
    # not sure if it is enough, but it is working
    return dtline.startswith('filename')

# guess_cols is the same as for new nicos format

from ufit.data.nicos import guess_cols


mapping = {
    'name:': 'title',
    '1st orientation reflection': 'orient1',
    '2nd orientation reflection': 'orient2',
    'zone axis for scattering plane': 'zoneaxis',
    'created at': 'created',
    'PSI0 (deg)': 'psi_offset',
    'Scattering sense': 'scattersense',
    'mono focussing mode': 'mono_focus',
    'ana  focussing mode': 'ana_focus',
    'TAS operation mode': 'opmode',
    'mth  (A1) (deg)': 'mth_offset',
    'mtt  (A2) (deg)': 'mtt_offset',
    'sth  (A3) (deg)': 'sth_offset',
    'stt  (A4) (deg)': 'stt_offset',
    'ath  (A5) (deg)': 'ath_offset',
    'att  (A6) (deg)': 'att_offset',
}


def read_data(filename, fp):
    meta = {}
    first_pos = fp.tell()
    dtline = fp.readline()
    fp.seek(first_pos)
    if not dtline.startswith('filename'):
        raise UFitError('%r does not appear to be an OLD NICOS data file' %
                        filename)
    for line in iter(fp.readline, ''):
        #finished, go for data
        if line.startswith('scan data'):
            break
        #skip this lines
        if line.startswith(('***', '[', 'Sample information',
                            'instrument general setup at file creation',
                            'offsets of main axes')):
            continue
        #POLARIZATION, not implemented:
        #if line.startswith('counting for switching devices'): # polarized measurements!
        #    self.pol_devices = [d.strip() for d in line.split(']')[0].split('[')[1].split(', ')]
        #    self.pol_states = []
        #    self.polarized = True
        #    for s in line.split('states ')[1][1:-1].split('], ['):
        #        s = [d.strip() for d in s.split(', ')]
        #        ts = {}
        #        for i in range(len(self.pol_devices)):
        #            ts[self.pol_devices[i]] = s[i]
        #        self.pol_states.append(ts)

        #else
        #apply mapping
        for k, v in mapping.items():
            if line.startswith(k):
                line = v + line[len(k):]

        try: # try to parse header lines
            k, v = meta_re.findall(line)[0]
            if v.strip() == v and len(v.split()) == 1:
                meta[k] = v
            elif 'filter' in k or k in ('saph', 'user', 'phone', 'fax',
                                        'orient1', 'orient2', 'zoneaxis',
                                        'responsable', 'created', 'scattersense',
                                        'samplename'): #take whole value
                meta[k] = v
            elif k in ('ss1', 'ss2'):
                for i, side in enumerate(('left', 'right', 'bottom', 'top')):
                    meta['%s_%s' % (k, side)] = float(v.split()[i])
                    meta['%s_%s_unit' % (k, side)] = v.split()[4]
                meta[k] = tuple(float(b) for b in v.split()[:4])
                meta['%s_unit' % k] = v.split()[4]
            elif k in ('a, b, c (A)', 'alpha, beta, gamma (deg)'):
                for i in range(3):
                    meta[k.split()[0].split(', ')[i]] = float(v.split(', ')[i])
                    meta['%s_unit' % k.split()[0].split(', ')[i]] = k.split()[1][1:-1]
            elif k == 'opmode':
                meta[k] = v.split()[0][1:-1]
                meta[v.split()[0][1:-1]] = v.split()[2]
            elif v.endswith(('mm', 'deg', 'A-1', 'THz', 'meV', 'T', 'K',
                             'bar', '%', 's', 'min', 'A')):
                meta[k] = v.split()[0]
                meta['%s_unit' % k] = v.split()[1]
            else:
                # device values
                if len(v.split()) == 2:
                    meta[k] = v.split()[0]
        except Exception:
            # ignore bad lines
            print 'ignored line:', line.strip()

    if 'filename' in meta:
        meta['filename'] = meta['filename'].strip("'")
        meta['filenumber'] = int(meta['filename'].split("_")[1])
    meta['filedesc'] = '%s:%s' % (meta.get('instrument', ''),
                                  meta.get('filenumber'))
    #read data
    meta['info'] = fp.readline().strip()
    colnames = fp.readline().split()
    colunits = fp.readline().split()

    return _nicos_common_load(fp, colnames, colunits, meta, '*')
