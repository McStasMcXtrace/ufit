#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data loading and treatment for ufit."""

from ufit import UFitError
from ufit.data import ill, nicos, nicos_old, simple, simple_csv, trisp, \
    llb, cascade, taipan
from ufit.data.loader import Loader
from ufit.data.dataset import Dataset, ScanData, ImageData, DatasetList
from ufit.plotting import mapping
from ufit.pycompat import listitems

data_formats_scan = {
    'ill': ill,
    'nicos': nicos,
    'old nicos': nicos_old,
    'simple': simple,
    'simple comma-separated': simple_csv,
    'trisp': trisp,
    'llb': llb,
    'taipan': taipan,
}

data_formats_image = {
    'cascade': cascade,
}

data_formats = dict(listitems(data_formats_scan) +
                    listitems(data_formats_image))

__all__ = ['Dataset', 'DatasetList', 'ScanData', 'ImageData', 'sets',
           'set_datatemplate', 'set_dataformat', 'read_data', 'as_data',
           'read_numors', 'do_mapping']


# simplified interface for usage in noninteractive scripts

global_loader = Loader()
sets = global_loader.sets


def set_datatemplate(template):
    """Set a new template for data file names.

    Normally, data file names consist of a fixed part and a sequential number.
    Therefore ufit constructs file names from a data template, which should
    contain a placeholder like ``%06d`` (for a 6-digit sequential number), and
    the actual file number given in the :func:`read_data` function.

    An example::

       set_datatemplate('/data/exp/data2012n%06d.dat')
       d1 = read_data(100)
       d2 = read_data(101)
       # etc.
    """
    global_loader.template = template


def set_dataformat(format):
    """Set the input data format.

    Normally ufit autodetects file formats, but this can be overridden using
    this function.  Data formats are:

    * ``'ill'`` - ILL TAS data format
    * ``'llb'`` - LLB binary TAS data format (known working for data from 1T and
      4F unpolarized)
    * ``'nicos'`` - NICOS data format
    * ``'old nicos'`` - NICOS 1.0 data format
    * ``'trisp'`` - FRM-II TRISP data format
    * ``'taipan'`` - ANSTO Taipan data format
    * ``'simple'`` - simple whitespace-separated multi-column files
    * ``'simple comma-separated'`` - simple comma-separated multi-column files
    """
    if format not in data_formats:
        raise UFitError('Unknown data format: %r, available formats are %s'
                        % (format, ', '.join(data_formats)))
    global_loader.format = format


def read_data(n, xcol='auto', ycol='auto', dycol=None, ncol=None, nscale=1):
    """Read a data file.  Returns a :class:`Dataset` object.

    :param xcol: X column name (or 1-based index)
    :param ycol: Y column name (or 1-based index)
    :param ycol: Y errors column name (or 1-based index); the default is to take
        the square root of the Y column as appropriate for counts
    :param ncol: normalization column name (or 1-based index); typically a beam
        monitor column
    :param nscale: scale for the normalization column; the Y data is determined
        as ``y[i] = y_raw[i] / ncol[i] * nscale``
    """
    return global_loader.load(n, xcol, ycol, dycol, ncol, nscale)


def as_data(x, y, dy, name=''):
    """Quickly construct a :class:`Dataset` object from three numpy arrays."""
    return Dataset.from_arrays(name or 'data', x, y, dy)


def read_numors(nstring, binsize, xcol='auto', ycol='auto',
                dycol=None, ncol=None, nscale=1, floatmerge=True):
    """Read a number of data files.  Returns a list of :class:`Dataset`\s.

    :param nstring: A string that gives file numbers, with the operators given
        below.
    :param binsize: Bin size when files need to be merged according to
        *nstring*.
    :param floatmerge: If to use float merging instead of binning. Default true.

    Other parameters as in :func:`read_data`.

    *nstring* can contain these operators:

    * ``,`` -- loads multiple files
    * ``-`` -- loads multiple sequential files
    * ``+`` -- merges multiple files
    * ``>`` -- merges multiple sequential files

    For example:

    * ``'10-15,23'`` loads files 10 through 15 and 23 in 7 separate datasets.
    * ``'10+11,23+24'`` loads two datasets consisting of files 10 and 11 merged
      into one set, as well as files 23 and 24.
    * ``'10>15+23'`` merges files 10 through 15 and 23 into one single dataset.
    * ``'10,11,12+13,14'`` loads four sets.
    """
    return global_loader.load_numors(nstring, binsize, xcol, ycol,
                                     dycol, ncol, nscale, floatmerge)


def do_mapping(x, y, runs, minmax=None, mode=0, log=False, dots=True,
               xscale=1, yscale=1, interpolate=100, usemask=True, figure=None,
               clear=True, colors=None, axes=None, title=None):
    """Create a 2D map from several datasets.

    An example::

        mapping("h", "E", datas)

    :param minmax: tuple of minimum and maximum value for z-scale
    :param mode: 0 = image, 1 = contour filled, 2 = contour lines
    :param log: True if the z-scale should be logarithmic
    :param dots: whether to show dots on position of datapoints
    :param xscale, yscale: to define scale between x and y axis
    :param interpolate: number of points to interpolate in between points
    :param usemask: True if masked out points should be removed
    :param figure: where to plot, default is current figure (``pl.gcf()``)
    :param clear: whether to do ``figure.clf()`` before plotting
    :param colors: when using mode > 1, optional list of colors for plotting
    :param axes: axes where to plot, default is figure.gca()
    :param title: title of the plot
    """
    return mapping(x, y, runs, minmax, mode, log, dots,
                   xscale, yscale, interpolate, usemask, figure,
                   clear, colors, axes, title)
