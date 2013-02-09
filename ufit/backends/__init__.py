# ufit backends

from ufit.core import debug, UFitError

__all__ = ['set_backend', 'backend']

backend = None

try:
    from ufit.backends import scipy
except ImportError:
    scipy = None
else:
    backend = scipy

try:
    from ufit.backends import minuit
except ImportError:
    minuit = None
else:
    backend = minuit

try:
    from ufit.backends import lmfit
except ImportError:
    lmfit = None
else:
    backend = lmfit

def set_backend(which):
    global backend
    backend = globals()[which]
    if backend is None:
        raise UFitError('backend %r not available' % which)
    debug('ufit using %s backend' % backend.backend_name)
