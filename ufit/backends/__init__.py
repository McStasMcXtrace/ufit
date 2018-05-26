#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Backend modules for different fitting packages/algorithms."""

from ufit import UFitError

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

try:
    from ufit.backends import unifit
except ImportError:
    raise
    unifit = None
else:
    available.append(unifit)


def set_backend(which):
    """Select a new backend for fitting."""
    global backend
    backend = globals()[which]
    if backend is None:
        raise UFitError('Backend %r is not available' % which)
    print('ufit using %s backend' % backend.backend_name)
