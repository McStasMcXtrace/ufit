#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Plotting routines for ufit using matplotlib."""

from itertools import cycle

from numpy import array, isscalar, linspace

import matplotlib
matplotlib.rc('font', **{'sans-serif': 'Sans Serif, Arial, Helvetica, '
                     'Lucida Grande, Bitstream Vera Sans'})
matplotlib.rc('savefig', format='pdf')

from matplotlib import pyplot as pl
from matplotlib.colors import LogNorm

from ufit.param import prepare_params


def multi_linspace(start, stop, steps):
    """linspace variant that handles arrays:

    multi_linspace([0,5], [1,10], 3) gives [[0,5],[0.5,7.5],[1,10]].
    """
    if isscalar(start):
        return linspace(start, stop, steps)
    return array([linspace(start[i], stop[i], steps)
                  for i in range(len(start))]).T


class DataPlotter(object):

    markers = ['o', 's', 'v', '*', 'd', '^', '>', 'p']

    def __init__(self, canvas=None, axes=None, toolbar=None):
        if axes is None:
            axes = pl.gca()
        self.axes = axes
        self.orig_spspec = axes.get_subplotspec()
        self.canvas = canvas
        self.image = None
        self.save_layout()
        self.marker_cycle = cycle(self.markers)
        self.toolbar = toolbar
        self._limits = None
        # display options
        self.no_fits = False
        self.symbols = True
        self.lines = False
        self.grid = True
        self.legend = True
        self.imgsmoothing = True

    def draw(self):
        self.canvas.draw()

    def save_layout(self):
        self.orig_axes_position = self.axes.get_position()

    def reset(self, limits=None):
        if limits is True:
            self._limits = self.axes.get_xlim(), self.axes.get_ylim()
        else:
            self._limits = limits
        xscale, yscale = self.axes.get_xscale(), self.axes.get_yscale()
        if self.image is not None:
            self.canvas.figure.delaxes(self.image.colorbar.ax)
            self.image = None
            self.axes.set_subplotspec(self.orig_spspec)
            self.axes.set_position(self.orig_axes_position)
        self.axes.clear()
        self.axes.set_aspect('auto')
        self.axes.set_xscale(xscale)
        self.axes.set_yscale(yscale)
        self.marker_cycle = cycle(self.markers)

    def plot_data(self, data, multi=False, ms=8, offset=0, **kw):
        """Plot dataset."""
        axes = self.axes
        marker = next(self.marker_cycle) if self.symbols else ''
        ls = '-' if self.lines else ''
        if 'label' not in kw:
            kw['label'] = data.name
        if data.mask.all():
            eb = axes.errorbar(data.x_plot, data.y + offset, data.dy, ls=ls,
                               marker=marker, ms=ms, picker=5, **kw)
            color = eb[0].get_color()
        else:
            mask = data.mask
            eb = axes.errorbar(data.x_plot[mask], data.y[mask] + offset,
                               data.dy[mask], ls=ls, marker=marker, ms=ms,
                               picker=5, **kw)
            color = eb[0].get_color()
            kw['label'] = ''
            axes.errorbar(data.x_plot[~mask], data.y[~mask] + offset,
                          data.dy[~mask], ls='', marker=marker, ms=ms,
                          picker=5, mfc='white', mec=color, **kw)
        if not multi:
            if data.fitmin is not None:
                axes.axvline(data.fitmin, ls='-', color='gray')
            if data.fitmax is not None:
                axes.axvline(data.fitmax, ls='-', color='grey')
            axes.set_title('%s\n%s' % (data.title, data.subtitle))
            self.plot_finish(data.xaxis, data.yaxis)
        return color

    def plot_finish(self, xlabel=None, ylabel=None, title=None):
        axes = self.axes
        if xlabel is not None:
            axes.set_xlabel(xlabel, {'size': pl.rcParams['axes.labelsize']})
        if ylabel is not None:
            axes.set_ylabel(ylabel, {'size': pl.rcParams['axes.labelsize']})
        if title is not None:
            axes.set_title(title)
        if self.legend:
            axes.legend()
        if self.grid:
            axes.grid(True)
        if self._limits:
            axes.set_xlim(*self._limits[0])
            axes.set_ylim(*self._limits[1])
        if self.toolbar:
            self.toolbar.update()

    def _get_samples(self, model, data):
        if model.nsamples < 0:
            return len(data.x) * (-model.nsamples)
        return model.nsamples

    def plot_model_full(self, model, data, labels=True, paramvalues=None,
                        offset=0, **kw):
        if self.no_fits:
            return
        if paramvalues is None:
            paramvalues = prepare_params(model.params, data.meta)[3]
        nsamples = self._get_samples(model, data)
        imin, imax = data.x_plot.argmin(), data.x_plot.argmax()
        xx = multi_linspace(data.x[imin], data.x[imax], nsamples)
        xxp = linspace(data.x_plot[imin], data.x_plot[imax], nsamples)
        yy = model.fcn(paramvalues, xx)
        if 'label' not in kw:
            kw['label'] = labels and 'fit' or ''
        self.axes.plot(xxp, yy + offset, 'g', lw=kw.pop('kw', 2), **kw)
        for comp in model.get_components():
            if comp is model:
                continue
            yy = comp.fcn(paramvalues, xx)
            kw['label'] = labels and comp.name or ''
            self.axes.plot(xxp, yy + offset, '-.', **kw)

    def plot_model(self, model, data, labels=True, paramvalues=None,
                   offset=0, **kw):
        if self.no_fits:
            return
        if paramvalues is None:
            paramvalues = prepare_params(model.params, data.meta)[3]
        nsamples = self._get_samples(model, data)
        imin, imax = data.x_plot.argmin(), data.x_plot.argmax()
        xx = multi_linspace(data.x[imin], data.x[imax], nsamples)
        xxp = linspace(data.x_plot[imin], data.x_plot[imax], nsamples)
        yy = model.fcn(paramvalues, xx)
        if 'label' not in kw:
            kw['label'] = labels and 'fit' or ''
        self.axes.plot(xxp, yy + offset, kw.pop('fmt', 'g'),
                       lw=kw.pop('lw', 2), **kw)

    def plot_model_components(self, model, data, labels=True, paramvalues=None,
                              offset=0, **kw):
        if self.no_fits:
            return
        if paramvalues is None:
            paramvalues = prepare_params(model.params, data.meta)[3]
        nsamples = self._get_samples(model, data)
        imin, imax = data.x_plot.argmin(), data.x_plot.argmax()
        xx = multi_linspace(data.x[imin], data.x[imax], nsamples)
        xxp = linspace(data.x_plot[imin], data.x_plot[imax], nsamples)
        for comp in model.get_components():
            yy = comp.fcn(paramvalues, xx)
            kw['label'] = labels and comp.name or ''
            self.axes.plot(xxp, yy + offset, kw.pop('fmt', '-.'), **kw)

    def plot_params(self, params, chisqr):
        s = []
        for p in params:
            if p.expr:
                continue
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

    def plot_mapping(self, *args, **kwds):
        kwds['axes'] = self.axes
        kwds['figure'] = self.canvas.figure
        kwds['clear'] = False
        self.image = plot_mapping(*args, **kwds)
        if self._limits:
            self.axes.set_xlim(*self._limits[0])
            self.axes.set_ylim(*self._limits[1])

    def plot_image(self, imgdata, multi=False):
        axes = self.axes
        norm = getattr(self.canvas, 'logz', False) and LogNorm() or None
        interp = 'nearest' if not self.imgsmoothing else 'gaussian'
        axes.imshow(imgdata.arr, origin='lower', aspect='equal',
                    interpolation=interp, norm=norm)
        if not multi:
            self.plot_finish(imgdata.xaxis, imgdata.yaxis, imgdata.title)


def plot_mapping(x, y, mapdata, figure=None, axes=None, clear=True, mode=0,
                 colors=None, title=None, dots=True, minmax=None):
    """

    modes: 0 = image
           1 = contour filled
           2 = contour lines
    """
    if figure is None:
        figure = pl.gcf()
    if clear:
        figure.clf()
    if axes is None:
        axes = figure.gca()
    xss, yss, xi, yi, zi = mapdata
    if mode == 0:
        im = axes.imshow(zi.T, origin='lower', aspect='auto',
                         interpolation='nearest',
                         vmin=minmax[0] if minmax is not None else None,
                         vmax=minmax[1] if minmax is not None else None,
                         extent=(xi[0][0], xi[-1][-1], yi[0][0], yi[-1][-1]))
    else:
        fcn = axes.contourf if mode == 1 else axes.contour
        kwds = {}
        if colors:
            kwds = {'colors': colors}
        im = fcn(xi, yi, zi, 20,
                 extent=(xi[0][0], xi[-1][-1], yi[0][0], yi[-1][-1]),
                 **kwds)
    axes.set_xlabel(x)
    axes.set_ylabel(y)
    if title is not None:
        axes.set_title(title)
    figure.colorbar(im, ax=axes, fraction=0.05)
    if dots:
        axes.scatter(xss, yss, 0.1)
    return im


def mapping(x, y, runs, minmax=None, mode=0, log=False, dots=True,
            xscale=1, yscale=1, interpolate=100, usemask=True, figure=None,
            clear=True, colors=None, axes=None, title=None):
    from ufit.data.mapping import bin_mapping
    mapdata = bin_mapping(
        x, y, runs, usemask=usemask, log=log, xscale=xscale, yscale=yscale,
        interpolate=interpolate, minmax=minmax)
    return plot_mapping(
        x, y, mapdata, figure=figure, axes=axes, clear=clear, mode=mode,
        minmax=minmax, dots=dots, colors=colors, title=title)
