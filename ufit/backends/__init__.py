#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Backend modules for different fitting packages/algorithms."""

from ufit import debug, UFitError

__all__ = ['set_backend', 'backend']

backend = None
available = []

try:
    from ufit.backends import scipy
except ImportError:
    scipy = None
else:
    backend = scipy
    available.append(scipy)

try:
    from ufit.backends import minuit
except ImportError:
    minuit = None
else:
    backend = minuit
    available.append(minuit)

try:
    from ufit.backends import lmfit
except ImportError:
    lmfit = None
else:
    backend = lmfit
    available.append(lmfit)


def set_backend(which):
    global backend
    backend = globals()[which]
    if backend is None:
        raise UFitError('backend %r not available' % which)
    debug('ufit using %s backend' % backend.backend_name)
