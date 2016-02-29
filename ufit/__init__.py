#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2014, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

__version__ = '1.0.1'


def debug(str):
    if __debug__:
        print str

class UFitError(Exception):
    pass

from ufit.result import *
from ufit.param import *
from ufit.data import *
from ufit.models import *
from ufit.backends import *
