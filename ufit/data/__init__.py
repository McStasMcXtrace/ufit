#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data loading and treatment for ufit."""

from ufit import UFitError
from ufit.data import ill, nicos, simple
from ufit.data.loader import Loader
from ufit.data.dataset import Dataset

data_formats = {
    'ill': ill,
    'nicos': nicos,
    'simple': simple,
}

__all__ = ['Dataset', 'sets', 'set_datatemplate', 'set_dataformat',
           'read_data', 'as_data']


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
    * ``'nicos'`` - NICOS data format
    * ``'simple'`` - simple whitespace-separated multi-column files
    """
    if format not in data_formats:
        raise UFitError('Unknown data format %r' % format)
    global_loader.format = format

def read_data(n, xcol, ycol, dycol=None, ncol=None, nscale=1):
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
