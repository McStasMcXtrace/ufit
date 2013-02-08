# ufit models package

import inspect
import operator

from ufit import backends
from ufit.core import UFitError, Data, Param


class Model(object):
    """Base class for Model functions.  Arithmetic combinations of Model
    instances again yield model instances (via CombinedModel).
    """
    name = ''
    params = []
    fcn = None

    def fit(self, data, **kw):
        data = self._as_data(data)
        return backends.backend.do_fit(data, self.fcn, self.params, kw)

    def global_params(self, **p):
        for pname, initval in p.iteritems():
            self.params.append(Param(pname, initval))

    def _init_params(self, mname, pnames, init):
        self.params = []
        if mname:
            pnames_real = ['%s_%s' % (mname, pname) for pname in pnames]
        else:
            pnames_real = pnames
        for (pname, porigname) in zip(pnames_real, pnames):
            try:
                initval = init[porigname]
                if initval is None:
                    raise KeyError
                self.params.append(Param(pname, initval))
            except KeyError:
                raise UFitError('Parameter %s needs an initializer' % pname)
        return pnames_real

    def _as_data(self, data):
        if isinstance(data, Data):
            return data
        elif isinstance(data, tuple):
            return Data(*data)
        raise UFitError('cannot handle data %r' % data)

    def __add__(self, other):
        if not isinstance(other, Model):
            return NotImplemented
        return CombinedModel(self, other, operator.add)

    def __sub__(self, other):
        if not isinstance(other, Model):
            return NotImplemented
        return CombinedModel(self, other, operator.sub)

    def __mul__(self, other):
        if not isinstance(other, Model):
            return NotImplemented
        return CombinedModel(self, other, operator.mul)

    def __div__(self, other):
        if not isinstance(other, Model):
            return NotImplemented
        return CombinedModel(self, other, operator.div)


class CombinedModel(Model):

    def __init__(self, a, b, op):
        self.params = []
        seen = set()
        for m in [a, b]:
            for p in m.params:
                if p.name in seen:
                    raise UFitError('Parameter name clash: %s' % p.name)
                self.params.append(p)

        self.fcn = lambda p, x: op(a.fcn(p, x), b.fcn(p, x))


class Function(Model):
    def __init__(self, fcn, name='', **init):
        self._real_fcn = fcn
        pvs = self._init_params(name, inspect.getargspec(fcn)[0][1:], init)

        self.fcn = lambda p, x: \
            self._real_fcn(x, *(p[pv] for pv in pvs))


class Background(Model):
    def __init__(self, name='', bkgd=None):
        pb, = self._init_params(name, ['bkgd'], locals())
        # background should be positive (XXX makes lmfit fail)
        ##if self.params[0].pmin is None:
        ##    self.params[0].pmin = 0

        self.fcn = lambda p, x: p[pb]


from ufit.models.peaks import *
from ufit.models.corr import *
