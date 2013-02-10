# ufit base models

import inspect
import operator
from numpy import concatenate, linspace
import matplotlib.pyplot as pl

from ufit import backends, UFitError, Param, Run, Result
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

    # class properties

    # if nonempty, the names of points to pick in the GUI
    pick_points = []
    # names of parameters
    param_names = []

    # set by initializers
    name = ''
    params = []
    fcn = None
    _orig_params = None

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.name)

    def _init_params(self, name, pnames, init):
        """Helper for model subclasses to quickly initialize Param objects.

        If a model name is given by the user, the parameter names are prefixed
        with "name_", so that multiple parameters with the same name can
        coexist in the same model.
        """
        self.params = []
        self.name = name
        if name:
            pnames_real = ['%s_%s' % (name, pname) for pname in pnames]
        else:
            pnames_real = pnames
        for (pname, porigname) in zip(pnames_real, pnames):
            try:
                initval = init[porigname]
                if initval is None:
                    raise KeyError
                self.params.append(Param.from_init(pname, initval))
            except KeyError:
                raise UFitError('Parameter %s needs an initializer' % pname)
        return pnames_real

    def _combine_params(self, a, b):
        """Helper for model subclasses that combine two submodels.

        self.params is initialized with a combination of params of both models,
        while an error is raised if name clash.
        """
        self.params = []
        seen = set()
        for m in [a, b]:
            for p in m.params:
                if p.name in seen:
                    raise UFitError('Parameter name clash: %s' % p.name)
                seen.add(p.name)
                self.params.append(p)

    def __add__(self, other):
        if not isinstance(other, Model):
            return NotImplemented
        return CombinedModel(self, other, '+')

    def __sub__(self, other):
        if not isinstance(other, Model):
            return NotImplemented
        return CombinedModel(self, other, '-')

    def __mul__(self, other):
        if not isinstance(other, Model):
            return NotImplemented
        return CombinedModel(self, other, '*')

    def __div__(self, other):
        if not isinstance(other, Model):
            return NotImplemented
        return CombinedModel(self, other, '/')

    @property
    def original_params(self):
        if self._orig_params is None:
            return self.params
        return self._orig_params

    def fit(self, data, xmin=None, xmax=None, **kw):
        if self._orig_params is None:
            self._orig_params = [p.copy() for p in self.params]
        success, msg, chi2 = backends.backend.do_fit(data, self.fcn, self.params,
                                                     (xmin, xmax), kw)
        for p in self.params:
            p.value = p.finalize(p.value)
        return Result(success, data, self, self.params, msg, chi2)

    def reset(self):
        if self._orig_params is not None:
            self.params = [p.copy() for p in self._orig_params]

    def plot(self, data, title=None, xlabel=None, ylabel=None, _pdict=None, _axes=None):
        if _pdict is None:
            _pdict = prepare_params(self.params, data.meta)[3]
        xx = linspace(data.x[0], data.x[-1], 1000)
        yy = self.fcn(_pdict, xx)
        if _axes is None:
            pl.figure()
            _axes = pl.gca()
        _axes.errorbar(data.x, data.y, data.dy, fmt='o', ms=8, label=data.name)
        _axes.plot(xx, yy, lw=2, label='fit')
        if title:
            _axes.set_title(title)
        _axes.set_xlabel(xlabel or data.xcol)
        _axes.set_ylabel(ylabel or data.ycol)
        _axes.legend()

    def plot_components(self, data, _pdict=None, _axes=None):
        if _pdict is None:
            _pdict = prepare_params(self.params, data.meta)[3]
        if _axes is None:
            _axes = pl.gca()
        xx = linspace(data.x[0], data.x[-1], 1000)
        for comp in self.get_components():
            yy = comp.fcn(_pdict, xx)
            _axes.plot(xx, yy, '--', label=comp.name)
        _axes.legend()

    def global_fit(self, datas, **kw):
        new_model = GlobalModel(self, datas)
        cumulative_data = Run.from_arrays('cumulative data',
                                          concatenate([d.x for d in datas]),
                                          concatenate([d.y for d in datas]),
                                          concatenate([d.dy for d in datas]))
        res = new_model.fit(cumulative_data, **kw)
        return new_model.generate_results(res)

    def add_params(self, **p):
        for pname, initval in p.iteritems():
            self.params.append(Param.from_init(pname, initval))

    def get_components(self):
        """Return a list of invidual non-modifier components.

        Modifiers are applied to the components as appropriate.
        """
        return [self]

    def is_modifier(self):
        """Return true if the model is a "modifier", i.e. not a component that
        should be plotted as a separate component.
        """
        return False

    def get_description(self):
        """Get a human-readable description of the model."""
        if self.name:
            return '%s[%s]' % (self.__class__.__name__, self.name)
        return self.__class__.__name__

    def get_pick_points(self):
        """Get a list of point names that should be picked for initial guess."""
        if self.name:
            return ['%s: %s' % (self.name, pn) for pn in self.pick_points]
        return self.pick_points

    def convert_pick(self, *args):
        """Convert pick point coordinates (x,y) to parameter initial guesses."""
        return {}

    def apply_pick(self, points):
        initial_values = self.convert_pick(*points)
        for p in self.params:
            if p.name in initial_values:
                p.value = initial_values[p.name]


class CombinedModel(Model):
    """Models an arithmetic combination of two sub-models.

    Parameters are combined from both; their names may not clash.
    """

    op_prio = {
        '+': 0,
        '-': 0,
        '*': 1,
        '/': 1,
    }

    op_fcn = {
        '+': operator.add,
        '-': operator.sub,
        '*': operator.mul,
        '/': operator.div,
    }

    def __init__(self, a, b, opstr):
        self.params = []
        self._a = a
        self._b = b
        self._op = op = self.op_fcn[opstr]
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
            return [CombinedModel(self._a, c, self._opstr)
                    for c in self._b.get_components()]
        elif self._b.is_modifier():
            return [CombinedModel(c, self._b, self._opstr)
                    for c in self._a.get_components()]
        else:
            # no modifiers
            return self._a.get_components() + self._b.get_components()

    def get_description(self):
        s = ''
        if isinstance(self._a, CombinedModel) and \
            self.op_prio[self._a._opstr] < self.op_prio[self._opstr]:
            s += '(%s)' % self._a.get_description()
        else:
            s += self._a.get_description()
        s += ' ' + self._opstr + ' '
        if isinstance(self._b, CombinedModel) and \
            self.op_prio[self._b._opstr] < self.op_prio[self._opstr]:
            s += '(%s)' % self._b.get_description()
        else:
            s += self._b.get_description()
        return s

    def get_pick_points(self):
        """Get a list of point names that should be picked for initial guess."""
        return self._a.get_pick_points() + self._b.get_pick_points()

    def convert_pick(self, *args):
        """Convert pick point coordinates (x,y) to parameter initial guesses."""
        npp = len(self._a.get_pick_points())
        d = self._a.convert_pick(*args[:npp])
        d.update(self._b.convert_pick(*args[npp:]))
        return d


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

    def get_description(self):
        return 'Function[%s, %s]' % (self.name, self._real_fcn.func_name)


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
                self.params.append(p.copy())
                overall_params.append(p.name)
            else:
                for i in range(ndata):
                    new_param = p.copy(p.name + '__' + str(i))
                    self.params.append(new_param)
                    diff_params[i].append((p.name, new_param.name))

        def new_fcn(p, x):
            results = []
            dpd = dict((pn, p[pn]) for pn in overall_params)
            for i, data in enumerate(datas):
                dpd.update((opn, p[pn]) for (opn, pn) in diff_params[i])
                results.append(model.fcn(dpd, data.x))
            return concatenate(results)
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
            reslist.append(Result(overall_res.success, data, self._model,
                                  paramlist, overall_res.message))
        return reslist
