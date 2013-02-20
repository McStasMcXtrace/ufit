#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Fit result class."""

from numpy import linspace

from ufit.plotting import DataPlotter

__all__ = ['Result']


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
        # XXX make a property
        self.residuals = model.fcn(self.paramvalues, data.x) - data.y

    # XXX make lazy
    @property
    def xx(self):
        return linspace(self.data.x[0], self.data.x[-1], 1000)

    @property
    def yy(self):
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

    def plot(self, axes=None, params=True):
        """Plot the data and model together in the current figure."""
        # XXX plot parameters in here
        plotter = DataPlotter(axes)
        plotter.plot_data(self.data)
        plotter.plot_model(self.model, self.data)
        if params:
            plotter.plot_params(self.params)

    def plotfull(self, axes=None, params=True):
        """Plot the data and model, including subcomponents, together in the
        current figure.
        """
        plotter = DataPlotter(axes)
        plotter.plot_data(self.data)
        plotter.plot_model_full(self.model, self.data)
        if params:
            plotter.plot_params(self.params)
