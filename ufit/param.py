# ufit parameter definitions

import copy

from ufit import UFitError


class fixed(str):
    pass

class expr(str):
    pass

class overall(object):
    def __init__(self, v):
        self.v = v

class datapar(object):
    def __init__(self, v):
        self.v = v

class limited(tuple):
    def __new__(self, min, max, v):
        return (min, max, v)


class Param(object):
    def __init__(self, name, pdef):
        self.name = name
        self.expr = None
        self.value = 0
        self.pmin = None
        self.pmax = None
        self.overall = False
        self.datapar = None
        while not isinstance(pdef, (int, long, float, str)):
            if isinstance(pdef, overall):
                self.overall = True
                pdef = pdef.v
            elif isinstance(pdef, datapar):
                self.datapar = pdef.v
                pdef = '__meta[%r]' % pdef.v
            elif isinstance(pdef, tuple) and len(pdef) == 3:
                self.pmin, self.pmax, pdef = pdef
            else:
                raise UFitError('Parameter definition %s not understood' %
                                pdef)
        if isinstance(pdef, str):
            self.expr = pdef
        else:
            self.value = pdef
        # properties set on fit result
        self.error = 0
        self.correl = {}
        # transform parameter after successful fit
        self.finalize = lambda x: x

    def copy(self, newname):
        cp = copy.copy(self)
        cp.name = newname
        return cp

    def __str__(self):
        s = '%-15s = %10.4g +/- %10.4g' % (self.name, self.value, self.error)
        if self.datapar:
            s += ' (from data: %s)' % self.datapar
        elif self.expr:
            s += ' (fixed: %s)' % self.expr
        if self.overall:
            s += ' (global)'
        return s

    def __repr__(self):
        return '<Param %s>' % self