#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

from ufit.version import get_version

__version__ = get_version()


class UFitError(Exception):
    pass


import ufit.qt
import matplotlib

if ufit.qt.QTVER == 4:
    matplotlib.use('Qt4Agg')
else:
    matplotlib.use('Qt5Agg')


from ufit.result import *
from ufit.param import *
from ufit.data import *
from ufit.models import *
from ufit.backends import *
