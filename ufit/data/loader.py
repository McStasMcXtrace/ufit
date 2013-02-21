#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data loader object."""

from os import path
from numpy import array, ones, sqrt

from ufit import UFitError
from ufit.data.dataset import Dataset, DataList, DatasetList


class Loader(object):
    def __init__(self):
        self.format = 'auto'
        self.template = '%d'
        self.sets = DataList()

    def _get_reader(self, filename, fobj):
        from ufit.data import data_formats
        if self.format == 'auto':
            for n, m in data_formats.iteritems():
                if m.check_data(fobj):
                    return m
            raise UFitError('File %s not recognized' % filename)
        return data_formats[self.format]

    def load(self, n, xcol, ycol, dycol=None, ncol=None, nscale=1):
        try:
            filename = self.template % n
            default_filedesc = str(n)
        except TypeError:
            filename = self.template
            default_filedesc = path.basename(self.template)
        fobj = open(filename, 'rb')
        colnames, coldata, meta = \
            self._get_reader(filename, fobj).read_data(filename, fobj)
        if 'filenumber' not in meta:
            meta['filenumber'] = n
        if 'filedesc' not in meta:
            meta['filedesc'] = default_filedesc
        if 'environment' not in meta:
            meta['environment'] = []
        meta['datafilename'] = filename
        datarr = ones((len(coldata), 4))

        def colindex(col):
            if isinstance(col, str):
                try:
                    return colnames.index(col)
                except ValueError:
                    raise UFitError('no such data column: %s' % col)
            elif 1 <= col <= len(colnames):
                return col - 1   # 1-based indices
            else:
                raise UFitError('data has only %d columns' % len(colnames))
        datarr[:,0] = coldata[:,colindex(xcol)]
        datarr[:,1] = coldata[:,colindex(ycol)]
        if dycol is not None:
            datarr[:,2] = coldata[:,colindex(dycol)]
        else:
            datarr[:,2] = sqrt(datarr[:,1])
        if ncol is not None:
            datarr[:,3] = coldata[:,colindex(ncol)]

        def colname(col):
            if col is None:
                return None
            elif isinstance(col, str):
                return col
            return colnames[col - 1]   # 1-based indices
        dset = Dataset(meta, datarr, colname(xcol), colname(ycol),
                       colname(ncol), nscale)
        self.sets[n] = dset
        return dset

    def guess_cols(self, n):
        try:
            filename = self.template % n
        except TypeError:
            filename = self.template
        fobj = open(filename, 'rb')
        rdr = self._get_reader(filename, fobj)
        colnames, coldata, meta = rdr.read_data(filename, fobj)
        xguess, yguess, dyguess, mguess = None, None, None, None
        if colnames[0].lower() in ('h', 'qh'):
            deviations = array([(cs.max()-cs.min()) for cs in coldata.T[:4]])
            xguess = colnames[deviations.argmax()]
        else:
            xguess = colnames[0]
        maxcts = 0
        maxmon = 0
        nmon = 0
        for i, colname in enumerate(colnames):
            if rdr.good_ycol(colname):
                if coldata[:,i].sum() > maxcts:
                    yguess = colname
                    maxcts = coldata[:,i].sum()
            if colname.startswith('mon') or colname.startswith('M'):
                if coldata[:,i].sum() > maxmon:
                    mguess = colname
                    maxmon = coldata[:,i].sum()
                    # use average monitor counts for normalization, but
                    # round to 2 significant digits
                    nmon = int(float('%.2g' % coldata[:,i].mean()))
        if yguess is None and len(colnames) > 1:
            yguess = colnames[1]
            if len(colnames) > 2:
                dyguess = colnames[2]
        return colnames, xguess, yguess, dyguess, mguess, nmon

    def load_numors(self, nstring, binsize, xcol, ycol, dycol=None,
                    ncol=None, nscale=1):
        """Load a number of data files and merge them according to numor
        list operations:

        * ``,`` - put single files in individual data sets
        * ``-`` - put sequential files in individual data sets
        * ``+`` - merge single files
        * ``>`` - merge sequential files
        """
        def toint(a):
            try:
                return int(a)
            except ValueError:
                raise UFitError('invalid file number: %r' % a)
        # operator "precedence": ',' has lowest, then '+',
        # then '-' and '>' (equal)
        parts1 = nstring.split(',')
        datasets = []
        for part1 in parts1:
            if '-' in part1:
                a, b = map(toint, part1.split('-'))
                datasets.extend(self.load(n, xcol, ycol, dycol, ncol, nscale)
                                for n in range(a, b+1))
            else:
                parts2 = part1.split('+')
                inner = []
                for part2 in parts2:
                    if '>' in part2:
                        a, b = map(toint, part2.split('>'))
                        ds = [self.load(n, xcol, ycol, dycol, ncol, nscale)
                              for n in range(a, b+1)]
                        inner.append(ds[0].merge(binsize, *ds[1:]))
                    else:
                        inner.append(
                            self.load(toint(part2), xcol, ycol, dycol,
                                      ncol, nscale))
                datasets.append(inner[0].merge(binsize, *inner[1:]))
        return DatasetList(datasets)
