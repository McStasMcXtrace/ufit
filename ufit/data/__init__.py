#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data loading and treatment for ufit."""

from ufit import UFitError
from ufit.data import ill, nicos
from ufit.data.loader import Loader
from ufit.data.dataset import Dataset

data_formats = {
    'ill': ill,
    'nicos': nicos,
}

__all__ = ['Dataset', 'sets', 'set_datatemplate', 'set_dataformat',
           'read_data', 'as_data']


# simplified interface for usage in noninteractive scripts

global_loader = Loader()
sets = global_loader.sets

def set_datatemplate(s):
    global_loader.template = s

def set_dataformat(s):
    if s not in data_formats:
        raise UFitError('Unknown data format %r' % s)
    global_loader.format = s

def read_data(*args):
    return global_loader.load(*args)

def as_data(x, y, dy, name=''):
    return Dataset.from_arrays(name or 'data', x, y, dy)
