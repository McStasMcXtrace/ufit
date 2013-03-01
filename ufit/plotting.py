#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Plotting routines for ufit using matplotlib."""

from itertools import cycle

import matplotlib
matplotlib.rc('font', family='Helvetica')

import numpy as np
from numpy import array, mgrid, clip, linspace
from matplotlib import pyplot as pl
from matplotlib.cbook import flatten
from scipy.interpolate import griddata as griddata_sp

from ufit.param import prepare_params


class DataPlotter(object):

    markers = ['o', 's', 'v', '*', 'd', '^', '>', 'p']

    def __init__(self, canvas=None, axes=None, toolbar=None):
        if axes is None:
            axes = pl.gca()
        self.axes = axes
        self.canvas = canvas
        self.marker_cycle = cycle(self.markers)
        self.toolbar = toolbar
        self._limits = None
        self.symbols = True
        self.lines = False

    def draw(self):
        self.canvas.draw()

    def reset(self, limits=None):
        if limits is True:
            self._limits = self.axes.get_xlim(), self.axes.get_ylim()
        else:
            self._limits = limits
        self.axes.clear()
        self.marker_cycle = cycle(self.markers)

    def plot_data(self, data, multi=False):
        """Plot dataset."""
        axes = self.axes
        marker = self.marker_cycle.next() if self.symbols else ''
        ls = '-' if self.lines else ''
        if data.mask.all():
            eb = axes.errorbar(data.x, data.y, data.dy, ls=ls, marker=marker,
                               ms=8, label=data.name, picker=5)
            color = eb[0].get_color()
        else:
            mask = data.mask
            eb = axes.errorbar(data.x[mask], data.y[mask], data.dy[mask], ls=ls,
                               marker=marker, ms=8, label=data.name, picker=5)
            color = eb[0].get_color()
            axes.errorbar(data.x[~mask], data.y[~mask], data.dy[~mask], ls='',
                          marker=marker, ms=8, picker=5, mfc='white', mec=color,
                          label='')
        if not multi:
            if data.fitmin is not None:
                axes.axvline(data.fitmin, ls='-', color='gray')
            if data.fitmax is not None:
                axes.axvline(data.fitmax, ls='-', color='grey')
        axes.set_title('%s\n%s' % (data.meta.get('title', ''),
                                   data.meta.get('info', '')),
                       size='medium')
        axes.set_xlabel(data.xaxis)
        axes.set_ylabel(data.yaxis)
        axes.legend(prop={'size': 'small'})
        axes.grid(True)
        if self._limits:
            axes.set_xlim(*self._limits[0])
            axes.set_ylim(*self._limits[1])
        if self.toolbar:
            self.toolbar.update()
        return color

    def plot_model_full(self, model, data, labels=True, paramvalues=None, **kw):
        if paramvalues is None:
            paramvalues = prepare_params(model.params, data.meta)[3]
        xx = linspace(data.x[0], data.x[-1], 1000)
        yy = model.fcn(paramvalues, xx)
        self.axes.plot(xx, yy, 'g', lw=2, label=labels and 'fit' or '', **kw)
        for comp in model.get_components():
            yy = comp.fcn(paramvalues, xx)
            self.axes.plot(xx, yy, '-.', label=labels and comp.name or '',
                           **kw)

    def plot_model(self, model, data, labels=True, paramvalues=None, **kw):
        if paramvalues is None:
            paramvalues = prepare_params(model.params, data.meta)[3]
        xx = linspace(data.x[0], data.x[-1], 1000)
        yy = model.fcn(paramvalues, xx)
        self.axes.plot(xx, yy, 'g', lw=2, label=labels and 'fit' or '', **kw)

    def plot_model_components(self, model, data, labels=True, paramvalues=None,
                              **kw):
        if paramvalues is None:
            paramvalues = prepare_params(model.params, data.meta)[3]
        xx = linspace(data.x[0], data.x[-1], 1000)
        for comp in model.get_components():
            yy = comp.fcn(paramvalues, xx)
            self.axes.plot(xx, yy, '-.', label=labels and comp.name or '',
                           **kw)

    def plot_params(self, params, chisqr):
        s = []
        for p in params:
            s.append(u'%-12s = %9.4g ± %9.4g' % (p.name, p.value, p.error))
            if p.expr:
                s[-1] += ' (fixed)'
            if p.overall:
                s[-1] += ' (global)'
        s.append(u'%-12s = %9.3f' % (u'chi²/NDF', chisqr))
        s = '\n'.join(s)
        self.axes.text(0.02, 0.98, s, horizontalalignment='left',
                       verticalalignment='top', size='x-small',
                       transform=self.axes.transAxes, family='Monospace')


def mapping(x, y, runs, minmax=None, mat=False, log=False):
    pl.clf()
    xss = list(flatten(run[x] for run in runs))
    yss = list(flatten(run[y] for run in runs))
    if log:
        zss = list(flatten(np.log(run.y) for run in runs))
    else:
        zss = list(flatten(run.y for run in runs))
    if minmax is not None:
        zss = clip(zss, minmax[0]/100000., minmax[1]/100000.)
    xi, yi = mgrid[min(xss):max(xss):100j,
                   min(yss):max(yss):100j]
    zi = griddata_sp(array((xss, yss)).T, zss, (xi, yi))
    if mat:
        pl.imshow(zi.T, origin='lower', aspect='auto',
                  extent=(xi[0][0], xi[-1][-1], yi[-1][-1], yi[0][0]))
    else:
        pl.contourf(xi, yi, zi, 20)
    pl.colorbar()
