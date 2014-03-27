#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Load routine for OLD NICOS data."""

import time
import re
from numpy import array, loadtxt

from ufit import UFitError


def check_data(fp):
    dtline = fp.readline()
    fp.seek(0, 0)
    return dtline.startswith('filename')  #not sure if it is enough, but it is working


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
        if colname.startswith(('det', 'ctr', 'psd.roi')):
            if coldata[:,i].sum() > maxcts:
                maxcts = coldata[:,i].sum()
                yg = colname
    if yg is None:
        yg = colnames[1]
    return xg, yg, None, mg


def read_data(filename, fp):

    mapping = {'name:':'title',
                '1st orientation reflection':'orient1',
                '2nd orientation reflection':'orient2',
                'zone axis for scattering plane':'zoneaxis',
                'created at':'created',
                'PSI0 (deg)':'psi_offset',
                'Scattering sense':'scattersense',
                'mono focussing mode':'mono_focus',
                'ana  focussing mode':'ana_focus',
                'TAS operation mode':'opmode',
                'mth  (A1) (deg)':'mth_offset',
                'mtt  (A2) (deg)':'mtt_offset',
                'sth  (A3) (deg)':'sth_offset',
                'stt  (A4) (deg)':'stt_offset',
                'ath  (A5) (deg)':'ath_offset',
                'att  (A6) (deg)':'att_offset',
                }


    meta = {}
    first_pos = fp.tell()
    dtline = fp.readline()
    fp.seek(first_pos)
    if not dtline.startswith('filename'):
        raise UFitError('%r does not appear to be an OLD NICOS data file' %
                        filename)
    #ctime = time.mktime(time.strptime(
    #    dtline[len('### NICOS data file, created at '):].strip(),
    #    '%Y-%m-%d %H:%M:%S'))
    #meta['created'] = ctime
    remark = ''
    for line in iter(fp.readline, ''):
        #finished, go for data
        if line.startswith('scan data'):
            break
        #skip this lines
        if line.startswith(('***', 'Sample information',
                                        'instrument general setup at file creation',
                                        'offsets of main axes')):
            continue
        #POLARIZATION, not implemented:
        #if line.startswith('counting for switching devices'):	# polarized measurements!
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
            k, v = re.compile(r'^\s*([^:]*?)\s*:\s*(.*?)\s*$').findall(line)[0]
            if v.strip() == v and len(v.split()) == 1:
                meta[k] = v
                #self.__dict__[k] = v
                #~ print "SIMPLE", k, v
            elif k.find('filter') > -1 or k in ('saph', 'user', 'phone', 'fax', 'orient1', 'orient2',
                                                'zoneaxis', 'responsable', 'created', 'scattersense',
                                                'samplename'): #take whole value
                meta[k] = v
                #self.__dict__[k] = v
                #~ print "FILTER", k, v
            elif k in ('ss1', 'ss2'):
                for i in range(4):
                    meta['%s_%s' % (k, ('left', 'right', 'bottom', 'top')[i])] = float(v.split()[i])
                    meta['%s_%s_unit' % (k, ('left', 'right', 'bottom', 'top')[i])] = v.split()[4]
                meta[k] = tuple([float(b) for b in v.split()[:4]])
                meta['%s_unit' % k] = v.split()[4]
                #~ print "SLIT", k, v
            elif k in ('a, b, c (A)', 'alpha, beta, gamma (deg)'):
                for i in range(3):
                    meta[(k.split()[0].split(', '))[i]] = float(v.split(', ')[i])
                    meta['%s_unit' % (k.split()[0].split(', '))[i]] = k.split()[1][1:-1]
                #~ print "LATTICE", k, v
            elif k == 'opmode':
                meta[k] = v.split()[0][1:-1]
                meta[v.split()[0][1:-1]] = v.split()[2]
                #~ print "OPMODE", k, v.split()[0][1:-1], v.split()[2]
            elif v.endswith(('mm', 'deg', 'A-1', 'THz', 'meV', 'T', 'K', 'bar', '%', 's', 'min', 'A')):
                meta[k] = v.split()[0]
                meta['%s_unit' % k] = v.split()[1]
                #~ print "UNITS", k, v.split()
            else: 
                print "X: ", k, v.split()
        except Exception, e:
            print e
            #~ pass #ignore bad lines.....

    if remark and 'title' in meta:
        meta['title'] += ', ' + remark
    if 'filename' in meta:
        meta['filename'] = meta['filename'].strip("'")
        meta['filenumber'] = int(meta['filename'].split("_")[1])
    meta['filedesc'] = '%s:%s' % (meta.get('instrument', ''),
                                     meta.get('filenumber'))
    #read data
    meta['info'] = fp.readline().strip()

    colnames = fp.readline().split()
    colunits = fp.readline().split()
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
    coldata = loadtxt(fp, converters=cvdict, usecols=usecols, ndmin=2, comments="*")
    if not coldata.size:
        raise UFitError('empty data file')
    cols = dict((name, coldata[:,i]) for (i, name) in enumerate(colnames))
    meta['environment'] = []
    for col in cols:
        meta[col] = cols[col].mean()
    for tcol in ['Ts', 'sT', 'T_ccr5_A', 'T_ccr5_B']:
        if tcol in cols:
            meta['environment'].append('T = %.3f K' % meta[tcol])
            break
    if 'B' in cols:
        meta['environment'].append('B = %.3f K' % meta['B'])
    if len(colnames) >= 4 and colnames[3] == 'E':
        meta['hkle'] = coldata[:,:4]
        deviations = array([(cs.max()-cs.min()) for cs in coldata.T[:4]])
        xg = colnames[deviations.argmax()]
        meta['hkle_vary'] = xg
    return colnames, coldata, meta
