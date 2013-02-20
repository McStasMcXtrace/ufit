# ufit base models

import re
import inspect
import operator
import cPickle as pickle
from numpy import concatenate

from ufit import param, backends, UFitError, Param, Dataset
from ufit.result import Result, GlobalResult
from ufit.utils import get_chisqr, cached_property
from ufit.plotting import DataPlotter

__all__ = ['Model', 'CombinedModel', 'Function', 'eval_model']


data_re = re.compile(r'\bdata\b')

def eval_model(modeldef, paramdef=None):
    from ufit import models
    d = models.__dict__.copy()
    d.update(param.expr_namespace)
    d.update(param.__dict__)
    model = eval(modeldef, d)
    model.python_code = modeldef
    if paramdef:
        model.params = paramdef
    return model


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

    # can be set if the model is generated by eval()
    python_code = None

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
                # not raising an exception allows the GUI to omit irrelevant
                # initializers
                self.params.append(Param.from_init(pname, 0))
                #raise UFitError('Parameter %s needs an initializer' % pname)
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

    @cached_property
    def paramdict(self):
        return dict((p.name, p) for p in self.params)

    def __getitem__(self, key):
        return self.paramdict[key]

    def __add__(self, other):
        if isinstance(other, (int, long, float)):
            other = Constant(other)
        elif not isinstance(other, Model):
            return NotImplemented
        return CombinedModel(self, other, '+')

    def __radd__(self, other):
        if isinstance(other, (int, long, float)):
            return CombinedModel(Constant(other), self, '+')
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, (int, long, float)):
            other = Constant(other)
        elif not isinstance(other, Model):
            return NotImplemented
        return CombinedModel(self, other, '-')

    def __rsub__(self, other):
        if isinstance(other, (int, long, float)):
            return CombinedModel(Constant(other), self, '-')
        return NotImplemented

    def __mul__(self, other):
        if isinstance(other, (int, long, float)):
            other = Constant(other)
        elif not isinstance(other, Model):
            return NotImplemented
        return CombinedModel(self, other, '*')

    def __rmul__(self, other):
        if isinstance(other, (int, long, float)):
            return CombinedModel(Constant(other), self, '*')
        return NotImplemented

    def __div__(self, other):
        if isinstance(other, (int, long, float)):
            other = Constant(other)
        elif not isinstance(other, Model):
            return NotImplemented
        return CombinedModel(self, other, '/')

    def __rdiv__(self, other):
        if isinstance(other, (int, long, float)):
            return CombinedModel(Constant(other), self, '/')
        return NotImplemented

    def __pow__(self, other):
        if isinstance(other, (int, long, float)):
            other = Constant(other)
        elif not isinstance(other, Model):
            return NotImplemented
        return CombinedModel(self, other, '**')

    @property
    def original_params(self):
        if self._orig_params is None:
            return self.params
        return self._orig_params

    def fit(self, data, **kw):
        """Fit the model to the data.  *data* must be a :class:`Dataset` object.

        Any keywords will be passed to the raw fitting routine of the backend.
        """
        if self._orig_params is None:
            self._orig_params = [p.copy() for p in self.params]
        # keeping the attribute chain like this allows the backend to
        # be changed on the fly
        success, msg, chi2 = backends.backend.do_fit(data, self.fcn,
                                                     self.params, kw)
        for p in self.params:
            p.value = p.finalize(p.value)
        return Result(success, data, self, self.params, msg, chi2)

    def global_fit(self, datas, **kw):
        """Fit the model to multiple datasets, given as a list by *datas*.

        Any keywords will be passed to the raw fitting routine of the backend.
        """
        return GlobalModel(self, datas).fit(datas, **kw)

    def reset(self):
        if self._orig_params is not None:
            self.params = [p.copy() for p in self._orig_params]

    def plot(self, data, axes=None, labels=True, pdict=None):
        """Plot the model and the data in the current figure."""
        DataPlotter(axes=axes).plot_model(self, data, labels, pdict)

    def plot_components(self, data, axes=None, labels=True, pdict=None):
        """Plot subcomponents of the model in the current figure."""
        DataPlotter(axes=axes).plot_model_components(self, data, labels, pdict)

    def add_params(self, **params):
        """Add parameters that referenced by expressions in other parameters.

        For example, in this model ::

           m = Gauss('p1', pos='delta', ampl=5, fwhm=0.5) + \\
               Gauss('p2', pos='-delta', ampl='p1_ampl', fwhm='p1_fwhm')

        the parameter "delta" is referenced by two parameter expressions, but
        does not appear as a parameter of any of the model functions.  This
        parameter must be made known to the model by calling e.g. ::

           m.add_params(delta=0)
        """
        for pname, initval in params.iteritems():
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
        """Get a Python description of the model (no parameters)."""
        if self.python_code:
            return self.python_code
        if self.name:
            return '%s(%r)' % (self.__class__.__name__, self.name)
        return '%s()' % self.__class__.__name__

    def __reduce__(self):
        """Pickling support: reconstruct the object from a constructor call."""
        if self.python_code:
            return (eval_model, (self.python_code, self.params))
        return (self.__class__, (self.name,) + tuple(self.params))

    def copy(self):
        if self.python_code:
            return eval_model(self.python_code, [p.copy() for p in self.params])
        return pickle.loads(pickle.dumps(self))

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
        '**': 2,
    }

    op_fcn = {
        '+':  operator.add,
        '-':  operator.sub,
        '*':  operator.mul,
        '/':  operator.div,
        '**': operator.pow,
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

        # cache this!
        self._components = None

    def __repr__(self):
        return '<%s %r %s %r>' % (self.__class__.__name__,
                                  self._a, self._opstr, self._b)

    def __reduce__(self):
        """Pickling support: reconstruct the object from a constructor call."""
        if self.python_code:
            return (eval_model, (self.python_code, self.params))
        return (self.__class__, (self._a, self._b, self._opstr))

    def get_components(self):
        if self._components is not None:
            return self._components
        if self._opstr in ('+', '*'):
            modifiers = []
            components = []
            first = self
            while isinstance(first, CombinedModel) and \
                first._opstr == self._opstr:
                second = first._b
                first = first._a
                if second.is_modifier():
                    modifiers.append(second)
                else:
                    components.append(second)
            if first.is_modifier():
                modifiers.append(first)
            else:
                components.append(first)
            ret = sum((c.get_components() for c in components), [])
            if modifiers:
                all_mods = reduce(lambda a, b: CombinedModel(a, b, self._opstr),
                                  modifiers)
                ret = [CombinedModel(all_mods, c, self._opstr) for c in ret]
        elif self._a.is_modifier():
            if self._b.is_modifier():
                # apparently nothing worthy of plotting
                ret = []
            else:
                ret = [CombinedModel(self._a, c, self._opstr)
                       for c in self._b.get_components()]
        elif self._b.is_modifier():
            ret = [CombinedModel(c, self._b, self._opstr)
                   for c in self._a.get_components()]
        else:
            # no modifiers
            ret = self._a.get_components() + self._b.get_components()
        self._components = ret
        return ret

    def get_description(self):
        if self.python_code:
            return self.python_code
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


class Constant(Model):
    """Constant function - no parameters.

    Used for math operations between models and numbers.  Not to be confused
    with the Const model from models.other.
    """
    def __init__(self, const):
        self.const = const
        self.fcn = lambda p, x: const

    def __reduce__(self):
        """Pickling support: reconstruct the object from a constructor call."""
        if self.python_code:
            return (eval_model, (self.python_code, self.params))
        return (self.__class__, (self.const,))

    def is_modifier(self):
        return True


class Function(Model):
    """Model using a function provided by the user.

    Parameters are extracted from the function's arguments and passed
    positionally.
    """
    def __init__(self, fcn, name=None, **init):
        self._real_fcn = fcn
        if name is None:
            if fcn.__name__ != '<lambda>':
                name = fcn.__name__
            else:
                name = ''
        pvs = self._init_params(name, inspect.getargspec(fcn)[0][1:], init)

        self.fcn = lambda p, x: \
            self._real_fcn(x, *(p[pv] for pv in pvs))

    def get_description(self):
        if self.python_code:
            return self.python_code
        return 'Function(%s, %s)' % (self.name, self._real_fcn.func_name)


class GlobalModel(Model):
    """Model for a global fit for multiple datasets.

    Parameters can be global ("overall" parameters) or local to each dataset.
    Global parameters can be referenced in expressions from local parameters,
    but no the other way around.
    """

    def __init__(self, model, datas):
        self._model = model
        self._datas = datas
        ndata = len(datas)

        # generate a new parameter list with the model's original parameters
        # duplicated N times for N datasets, except for overall parameters;
        # the duplicates get named oldname__i where i is the data index

        self.params = []
        overall_params = []
        diff_params = [[] for i in range(ndata)]
        for p in model.params:
            if p.overall:
                self.params.append(p.copy())
                overall_params.append(p.name)
            else:
                for i in range(ndata):
                    new_param = p.copy(p.name + '__' + str(i))
                    self.params.append(new_param)
                    diff_params[i].append((p.name, new_param))

        # rewrite expressions to refer to the new parameter names (__i suffix)
        # and new data meta dictionaries (data.di)

        for i, dplist in enumerate(diff_params):
            for oldname, param in dplist:
                param._orig_expr = param.expr
                if not param.expr:
                    continue
                for oldname0, p0 in dplist:
                    param.expr = param.expr.replace(oldname0, p0.name)
                param.expr = data_re.sub('data.d%d' % i, param.expr)

        # global fitting function: call model function once for each dataset
        # with the original data, with the parameter values taken from the
        # duplicated params

        def new_fcn(p, x):
            results = []
            dpd = dict((pn, p[pn]) for pn in overall_params)
            for i, data in enumerate(datas):
                dpd.update((opn, p[pn.name]) for (opn, pn) in diff_params[i])
                results.append(model.fcn(dpd, data.x))
            return concatenate(results)
        self.fcn = new_fcn

    def fit(self, datas, **kw):

        # fit a cumulative data set consisting of a concatenation of all data
        fitcols = [d.fit_columns for d in datas]

        cumulative_data = Dataset.from_arrays(
            'cumulative data',
            concatenate([cols[0] for cols in fitcols]),
            concatenate([cols[1] for cols in fitcols]),
            concatenate([cols[2] for cols in fitcols]),
            dict(('d%d' % i, d.meta) for (i, d) in enumerate(datas)),
        )
        overall_res = Model.fit(self, cumulative_data, **kw)

        # generate a list of results for each dataset with the original
        # parameter names and expressions

        reslist = []
        for i, data in enumerate(datas):
            suffix = '__%d' % i
            paramlist = []
            for p in self.params:
                if p.overall:
                    paramlist.append(p)
                elif p.name.endswith(suffix):
                    clone_param = p.copy(p.name[:-len(suffix)])
                    clone_param.expr = p._orig_expr
                    paramlist.append(clone_param)
            chi2 = get_chisqr(self._model.fcn, data.x, data.y, data.dy, paramlist)
            reslist.append(Result(overall_res.success, data, self._model,
                                  paramlist, overall_res.message, chi2))
        return GlobalResult(reslist)
