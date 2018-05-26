#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Fit result class."""

import copy

from numpy import array, linspace, ravel
from matplotlib import pyplot as pl

from ufit.utils import cached_property
from ufit.plotting import DataPlotter
from ufit.pycompat import iteritems

__all__ = ['Result']


class Result(object):
    def __init__(self, success, data, model, params, message, chisqr):
        self.success = success
        self.data = data
        self.model = model
        self.params = params
        self.message = message
        self.chisqr = chisqr

    def __getitem__(self, key):
        return self.paramdict[key]

    def copy(self):
        return copy.deepcopy(self)

    @cached_property
    def paramdict(self):
        """Returns a dictionary mapping parameter names to parameter objects."""
        return dict((p.name, p) for p in self.params)

    @cached_property
    def paramvalues(self):
        """Returns a dictionary mapping parameter names to values."""
        return dict((p.name, p.value) for p in self.params)

    @cached_property
    def paramerrors(self):
        """Returns a dictionary mapping parameter names to errors."""
        return dict((p.name, p.error) for p in self.params)

    @cached_property
    def values(self):
        """Returns a list with all parameter values."""
        return [p.value for p in self.params]

    @cached_property
    def errors(self):
        """Returns a list with all parameter errors."""
        return [p.error for p in self.params]

    @cached_property
    def results(self):
        """Returns a list with the parameter values, then the parameter errors
        and the chi-square value concatenated.
        """
        return self.values + self.errors + [self.chisqr]

    @cached_property
    def residuals(self):
        """Returns the array of residuals."""
        return self.model.fcn(self.paramvalues, self.data.x) - self.data.y

    @cached_property
    def xx(self):
        """Returns a fine-spaced array of X values between the minimum and maximum
        of the original data X values.
        """
        return linspace(self.data.x.min(), self.data.x.max(), 1000)

    @cached_property
    def yy(self):
        """Returns the model evaluated at self.xx."""
        return self.model.fcn(self.paramvalues, self.xx)

    def printout(self):
        """Print out a table of the fit result and the parameter values.

        The chi-square value is also included in the table.  Example output::

           Fit results for 373
           ---------------------------------------------------------------------
           bkgd            =     5.5111 +/-    0.21427
           slope           =    -1.0318 +/-    0.16187
           inc_pos         =  -0.015615 +/- 0.00066617
           inc_ampl        =     547.21 +/-     8.0482
           inc_fwhm        =    0.12656 +/-  0.0012489
           dho_center      =  -0.015615 +/-          0 (fixed: inc_pos)
           dho_pos         =    0.41689 +/-  0.0086916
           dho_ampl        =    0.36347 +/-   0.034156
           dho_gamma       =    0.22186 +/-   0.025093
           dho_tt          =         16 +/-          0 (fixed: data.T)
           chi^2/NDF       =      1.491
           =====================================================================
        """
        print('Fit results for %s' % self.data.name)
        if not self.success:
            print('FIT FAILED: ' + self.message)
        elif self.message:
            print('> %s' % self.message)
        print('-' * 80)
        for p in self.params:
            print(p)
        print('%-15s = %10.4g' % ('chi^2/NDF', self.chisqr))
        print('=' * 80)

    def plot(self, axes=None, params=True, multi=False):
        """Plot the data and model together in the current figure.

        If *params* is true, also plot parameter values as text.
        """
        plotter = DataPlotter(axes=axes)
        c = plotter.plot_data(self.data, multi=multi)
        plotter.plot_model(self.model, self.data, paramvalues=self.paramvalues,
                           labels=not multi, color=c)
        if params and not multi:
            plotter.plot_params(self.params, self.chisqr)

    def plotfull(self, axes=None, params=True):
        """Plot the data and model, including subcomponents, together in the
        current figure or the given *axes*.

        If *params* is true, also plot parameter values as text.
        """
        plotter = DataPlotter(axes=axes)
        plotter.plot_data(self.data)
        plotter.plot_model_full(self.model, self.data,
                                paramvalues=self.paramvalues)
        if params:
            plotter.plot_params(self.params, self.chisqr)


def calc_panel_size(num):
    for nx, ny in ([1, 1], [2, 1], [2, 2], [3, 2], [3, 3], [4, 3], [5, 3], [4, 4],
                   [5, 4], [6, 4], [5, 5], [6, 5], [7, 5], [6, 6], [8, 5], [7, 6],
                   [9, 5], [8, 6], [7, 7], [9, 6], [8, 7], [9, 7], [8, 8], [10, 7],
                   [9, 8], [11, 7], [9, 9], [11, 8], [10, 9], [12, 8], [11, 9], [10, 10]):
        if nx*ny >= num:
            return nx, ny
    return num//10 + 1, 10


class MultiResult(list):
    def plot(self):
        dims = calc_panel_size(len(self))
        fig, axarray = pl.subplots(dims[1], dims[0])
        for res, axes in zip(self, ravel(axarray)):
            res.plotfull(axes=axes)
        # pl.tight_layout()

    @cached_property
    def datavalues(self):
        d = dict((k, [v]) for (k, v) in iteritems(self[0].data.meta))
        for res in self[1:]:
            for k, v in iteritems(res.data.meta):
                d[k].append(v)
        return d

    @cached_property
    def paramvalues(self):
        """Return a dictionary mapping parameter names to arrays of
        parameter values, one for each result.
        """
        d = dict((p.name, [p.value]) for p in self[0].params)
        for res in self[1:]:
            for p in res.params:
                d[p.name].append(p.value)
        for k in d:
            d[k] = array(d[k])
        return d

    @cached_property
    def paramerrors(self):
        """Return a dictionary mapping parameter names to arrays of
        parameter errors, one for each result.
        """
        d = dict((p.name, [p.error]) for p in self[0].params)
        for res in self[1:]:
            for p in res.params:
                d[p.name].append(p.error)
        for k in d:
            d[k] = array(d[k])
        return d

    def printout(self):
        """Print global parameters of the fit."""
        print('OVERALL fit results')
        print('-' * 80)
        for p in self[0].params:
            if p.overall:
                print(p)
        print('=' * 80)

    def plot_param(self, xname, pname):
        pl.errorbar(self.datavalues[xname], self.paramvalues[pname],
                    self.paramerrors[pname], fmt='o-')
        pl.xlabel(xname)
        pl.ylabel(pname)
