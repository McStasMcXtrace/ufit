#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Fit result class."""

from numpy import linspace


class Result(object):
    def __init__(self, success, data, model, params, message, chisqr):
        self.success = success
        self.data = data
        self.model = model
        self.params = params
        self.message = message
        self.chisqr = chisqr
        self.paramdict = dict((p.name, p) for p in params)
        self.paramvalues = dict((p.name, p.value) for p in params)

    @property
    def xx(self):
        return linspace(self.data.x[0], self.data.x[-1], 1000)

    @property
    def yy(self):
        return self.model.fcn(self.paramvalues, self.xx)

    def printout(self):
        print 'Fit results for %s' % self.data.name
        if not self.success:
            print 'FIT FAILED: ' + self.message
        elif self.message:
            print '>', self.message
        print '-' * 80
        for p in self.params:
            print p
        print '%-15s = %10.4g' % ('chi^2/NDF', self.chisqr)
        print '=' * 80

    def plot(self, **kw):
        self.data.plot(**kw)
        self.model.plot(self.data, _pdict=self.paramvalues, **kw)

    def plot_components(self, **kw):
        self.model.plot_components(self.data, _pdict=self.paramvalues, **kw)
