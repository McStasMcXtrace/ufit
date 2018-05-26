#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data loader object."""

import io

from numpy import ones, sqrt

from ufit import UFitError
from ufit.data.dataset import ScanData, ImageData, DataList, DatasetList
from ufit.pycompat import iteritems, string_types, number_types


class Loader(object):
    def __init__(self):
        self.format = 'auto'
        self.template = '%d'
        self.sets = DataList()

    def _get_reader(self, filename, fobj):
        from ufit.data import data_formats, data_formats_image
        if self.format == 'auto':
            for n, m in iteritems(data_formats):
                # check 'simple' formats last
                if not n.startswith('simple') and m.check_data(fobj):
                    return m, n in data_formats_image
            for n, m in iteritems(data_formats):
                if n.startswith('simple') and m.check_data(fobj):
                    return m, n in data_formats_image
            raise UFitError('File %r has no recognized file format' % filename)
        return data_formats[self.format], self.format in data_formats_image

    def _inner_load(self, n, xcol, ycol, dycol=None, ncol=None, nscale=1):
        try:
            filename = self.template % n
        except TypeError:
            filename = self.template
        fobj = io.open(filename, 'rb')
        rdr, isimg = self._get_reader(filename, fobj)
        if isimg:
            return self._inner_load_image(rdr, filename, fobj, n, ncol, nscale)
        return self._inner_load_scan(rdr, filename, fobj, n, xcol, ycol, dycol,
                                     ncol, nscale)

    def _inner_load_image(self, rdr, filename, fobj, n, ncol, nscale):
        arr, darr, meta = rdr.read_data(filename, fobj)
        if 'filenumber' not in meta:
            meta['filenumber'] = n
        meta['datafilename'] = filename
        if ncol == 'auto':
            ncol = rdr.guess_norm(meta)
        if ncol is not None:
            norm = meta[ncol]
        else:
            norm = 1
        dset = ImageData(meta, arr, darr, norm, nscale)
        self.sets[n] = dset
        return dset

    def _inner_load_scan(self, rdr, filename, fobj, n,
                         xcol, ycol, dycol, ncol, nscale):
        colnames, coldata, meta = rdr.read_data(filename, fobj)
        colguess = rdr.guess_cols(colnames, coldata, meta)
        if 'filenumber' not in meta:
            meta['filenumber'] = n
        meta['datafilename'] = filename
        for colname, colvalues in zip(colnames, coldata.T):
            meta['col_%s' % colname] = colvalues
        datarr = ones((len(coldata), 4))

        def colindex(col):
            if isinstance(col, string_types):
                try:
                    return colnames.index(col)
                except ValueError:
                    raise UFitError('No such data column: %s' % col)
            elif 1 <= col <= len(colnames):
                return col - 1   # 1-based indices
            else:
                raise UFitError('Data has only %d columns (but column %s is '
                                'requested)' % (len(colnames), col))
        use_hkl = False
        if xcol == 'hkl':
            xcol = 'auto'
            use_hkl = True
        if xcol == 'auto':
            xcol = colguess[0]
        datarr[:, 0] = coldata[:, colindex(xcol)]
        if ycol == 'auto':
            ycol = colguess[1]
        datarr[:, 1] = coldata[:, colindex(ycol)]
        if dycol == 'auto':
            dycol = colguess[2]
        if dycol is not None:
            datarr[:, 2] = coldata[:, colindex(dycol)]
        else:
            datarr[:, 2] = sqrt(datarr[:, 1])
        if ncol == 'auto':
            ncol = colguess[3]
        if ncol is not None:
            datarr[:, 3] = coldata[:, colindex(ncol)]
            if nscale == -1:
                nscale = int(float('%.2g' % datarr[:, 3].mean()))

        def colname(col):
            if col is None:
                return None
            elif isinstance(col, string_types):
                return col
            return colnames[col - 1]   # 1-based indices
        if use_hkl:
            meta['is_hkldata'] = True
        dset = ScanData(meta, datarr, colname(xcol), colname(ycol),
                        colname(ncol), nscale)
        if use_hkl and 'hkle' in dset.meta:  # 3-axis support
            dset.x = dset.meta['hkle']
        self.sets[n] = dset
        return dset

    def load(self, n, xcol, ycol, dycol=None, ncol=None, nscale=1):
        try:
            return self._inner_load(n, xcol, ycol, dycol, ncol, nscale)
        except Exception as e:
            raise UFitError('Could not load data file %d: %s' % (n, e))

    def guess_cols(self, n):
        try:
            filename = self.template % n
        except TypeError:
            filename = self.template
        fobj = io.open(filename, 'rb')
        rdr, isimg = self._get_reader(filename, fobj)
        if isimg:
            arr, darr, meta = rdr.read_data(filename, fobj)
            mguess = rdr.guess_norm(meta)
            if mguess:
                nmon = int(float('%.2g' % meta[mguess]))
            else:
                nmon = 1
            xguess, yguess, dyguess = None, None, None
            colnames = list(meta)
        else:
            colnames, coldata, meta = rdr.read_data(filename, fobj)
            xguess, yguess, dyguess, mguess = rdr.guess_cols(colnames, coldata, meta)
            if mguess is not None:
                # use average monitor counts for normalization, but
                # round to 2 significant digits
                moncol = coldata[:, colnames.index(mguess)]
                nmon = int(float('%.2g' % moncol.mean()))
            else:
                nmon = 0
            if yguess is None and len(colnames) > 1:
                yguess = colnames[1]
                if len(colnames) > 2:
                    dyguess = colnames[2]
        return colnames, xguess, yguess, dyguess, mguess, nmon

    def load_numors(self, nstring, binsize, xcol, ycol, dycol=None,
                    ncol=None, nscale=1, floatmerge=True):
        """Load a number of data files and merge them according to numor
        list operations:

        * ``,`` - put single files in individual data sets
        * ``-`` - put sequential files in individual data sets
        * ``+`` - merge single files
        * ``>`` - merge sequential files
        """
        if not isinstance(binsize, number_types):
            raise UFitError('binsize argument must be a number')

        def toint(a):
            try:
                return int(a)
            except ValueError:
                raise UFitError('Invalid file number: %r' % a)
        # operator "precedence": ',' has lowest, then '+',
        # then '-' and '>' (equal)
        parts1 = nstring.split(',')
        datasets = []
        for part1 in parts1:
            if '-' in part1:
                a, b = map(toint, part1.split('-'))
                datasets.extend(
                    self.load(n, xcol, ycol, dycol, ncol, nscale).merge(
                        binsize, floatmerge=floatmerge) for n in range(a, b+1))
            else:
                parts2 = part1.split('+')
                inner = []
                for part2 in parts2:
                    if '>' in part2:
                        a, b = map(toint, part2.split('>'))
                        ds = [self.load(n, xcol, ycol, dycol, ncol, nscale)
                              for n in range(a, b+1)]
                        inner.append(ds[0].merge(binsize, *ds[1:],
                                                 floatmerge=floatmerge))
                    else:
                        inner.append(
                            self.load(toint(part2), xcol, ycol, dycol,
                                      ncol, nscale))
                datasets.append(inner[0].merge(binsize, *inner[1:],
                                               floatmerge=floatmerge))
        return DatasetList(datasets)
