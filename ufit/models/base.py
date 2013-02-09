# ufit base models

import inspect
import operator
from numpy import array, concatenate, sqrt, linspace
import matplotlib.pyplot as pl

from ufit import backends
from ufit.core import UFitError, Param, Data, Result
from ufit.data.run import Run
from ufit.backends.util import prepare_params


class Model(object):
    """Base class for Model functions.

    Important APIs:

    * fit() - fit data with the model
    * add_params() - add parameters that are referenced in parameter
      expressions but not given by a parameter of one of the models yet
    * get_components() - return a list of Model instances that represent
      individual components of the complete model
    * is_modifier() - return bool whether the specific model is a "modifier"
      (i.e. not a component)
    """
    name = ''
    params = []
    fcn = None

    def _init_params(self, mname, pnames, init):
        self.params = []
        self.name = mname
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

    def _combine_params(self, a, b):
        self.params = []
        seen = set()
        for m in [a, b]:
            for p in m.params:
                if p.name in seen:
                    raise UFitError('Parameter name clash: %s' % p.name)
                self.params.append(p)

    def _as_data(self, data):
        if isinstance(data, Data):
            return data
        if isinstance(data, Run):
            return Data(data.x, data.y/data.n, sqrt(data.y)/data.n,
                        data.name, data.meta, data.xcol, data.ycol)
        raise UFitError('cannot handle data %r' % data)

    def __add__(self, other):
        if not isinstance(other, Model):
            return NotImplemented
        return CombinedModel(self, other, operator.add, '+')

    def __sub__(self, other):
        if not isinstance(other, Model):
            return NotImplemented
        return CombinedModel(self, other, operator.sub, '-')

    def __mul__(self, other):
        if not isinstance(other, Model):
            return NotImplemented
        return CombinedModel(self, other, operator.mul, '*')

    def __div__(self, other):
        if not isinstance(other, Model):
            return NotImplemented
        return CombinedModel(self, other, operator.div, '/')

    def fit(self, data, **kw):
        data = self._as_data(data)
        msg = backends.backend.do_fit(data, self.fcn, self.params, kw)
        for p in self.params:
            p.value = p.finalize(p.value)
        return Result(data, self, self.params, msg)

    def plot(self, data, title=None, xlabel=None, ylabel=None, _pdict=None):
        data = self._as_data(data)
        if _pdict is None:
            _pdict = prepare_params(self.params, data)[3]
        xx = linspace(data.x[0], data.x[-1], 1000)
        yy = self.fcn(_pdict, xx)
        pl.figure()
        pl.errorbar(data.x, data.y, data.dy, fmt='o', label=data.name)
        pl.plot(xx, yy, label='fit')
        if title:
            pl.title(title)
        pl.xlabel(xlabel or data.xcol)
        pl.ylabel(ylabel or data.ycol)
        pl.legend()

    def plot_components(self, data, _pdict=None):
        if _pdict is None:
            _pdict = prepare_params(self.params, data)[3]
        xx = linspace(data.x[0], data.x[-1], 1000)
        for comp in self.get_components():
            yy = comp.fcn(_pdict, xx)
            pl.plot(xx, yy, '--', label=comp.name)
        pl.legend()

    def global_fit(self, datas, **kw):
        datas = map(self._as_data, datas)
        new_model = GlobalModel(self, datas)
        cumulative_data = Data(concatenate([d.x for d in datas]),
                               concatenate([d.y for d in datas]),
                               concatenate([d.dy for d in datas]),
                               'cumulative data', None)
        res = new_model.fit(cumulative_data, **kw)
        return new_model.generate_results(res)

    def add_params(self, **p):
        for pname, initval in p.iteritems():
            self.params.append(Param(pname, initval))

    def get_components(self):
        return [self]

    def is_modifier(self):
        return False

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.name)


class CombinedModel(Model):
    """Models an arithmetic combination of two sub-models.

    Parameters are combined from both; their names may not clash.
    """

    def __init__(self, a, b, op, opstr=''):
        self.params = []
        self._a = a
        self._b = b
        self._op = op
        self._opstr = opstr
        if a.name and b.name:
            self.name = a.name + opstr + b.name
        else:
            self.name = a.name or b.name
        self._combine_params(a, b)

        self.fcn = lambda p, x: op(a.fcn(p, x), b.fcn(p, x))

    def get_components(self):
        if self._a.is_modifier():
            if self._b.is_modifier():
                # apparently nothing worthy of plotting
                return []
            return [CombinedModel(self._a, c, self._op, self._opstr)
                    for c in self._b.get_components()]
        elif self._b.is_modifier():
            return [CombinedModel(c, self._b, self._op, self._opstr)
                    for c in self._a.get_components()]
        else:
            # no modifiers
            return self._a.get_components() + self._b.get_components()


class Function(Model):
    """Model using a function provided by the user.

    Parameters are extracted from the function's arguments and passed
    positionally.
    """
    def __init__(self, fcn, name='', **init):
        self._real_fcn = fcn
        pvs = self._init_params(name, inspect.getargspec(fcn)[0][1:], init)

        self.fcn = lambda p, x: \
            self._real_fcn(x, *(p[pv] for pv in pvs))


class GlobalModel(Model):
    """Model for a global fit with some parameters varied."""

    def __init__(self, model, datas):
        self._model = model
        self._datas = datas
        ndata = len(datas)

        self.params = []
        overall_params = self._overall_params = []
        diff_params = self._diff_params = [[] for i in range(ndata)]
        for p in model.params:
            if p.overall:
                self.params.append(p)
                overall_params.append(p.name)
            else:
                for i in range(ndata):
                    new_param = p.copy(p.name + '__' + str(i))
                    self.params.append(new_param)
                    diff_params[i].append((p.name, new_param.name))

        def new_fcn(p, x):
            res = []
            for i, data in enumerate(datas):
                dpd = dict((pn, p[pn]) for pn in overall_params)
                dpd.update((opn, p[pn]) for (opn, pn) in diff_params[i])
                res.extend(model.fcn(dpd, data.x))
            return array(res)
        self.fcn = new_fcn

    def generate_results(self, overall_res):
        reslist = []
        for i, data in enumerate(self._datas):
            suffix = '__%d' % i
            paramlist = []
            for p in self.params:
                if p.overall:
                    paramlist.append(p)
                elif p.name.endswith(suffix):
                    paramlist.append(p.copy(p.name[:-len(suffix)])) # XXX
            reslist.append(Result(data, self._model, paramlist,
                                  overall_res.message))
        return reslist
