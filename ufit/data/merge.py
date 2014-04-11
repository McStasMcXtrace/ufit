#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2014, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data merging routines."""

from numpy import arange, ones, zeros, sqrt, array

from ufit import UFitError


def rebin(data, binsize):
    """Simple rebinning of (x, y, dy, n) data."""
    # XXX make it work with hkle 4-d x data

    if binsize == 0:
        # no merging, just concatenate
        return data

    x, y, dy, n = data.T

    # calculate new x values

    halfbinsize = binsize/2.
    stops = arange(x.min() - (x.min() % binsize) - binsize,
                   x.max() - (x.max() % binsize) + 2*binsize,
                   binsize) + halfbinsize
    nbins = len(stops)

    # newarray will be the new x, y, dy, n array
    newarray = zeros((nbins, 4))
    newarray[:,0] = stops

    # this will keep track which data values we already used
    data_unused = ones(len(x), bool)

    # this will keep track which new bins are used; unused ones are
    # left out
    new_used = ones(nbins, bool)

    for i in xrange(nbins):
        stop = newarray[i, 0]
        # get indices of all data points with x values lying below stop
        indices = x <= (stop + halfbinsize)
        # remove indices of data already used in previous bins
        indices &= data_unused
        if indices.any():
            newarray[i, 1] += y[indices].sum()
            newarray[i, 2] += sqrt((dy[indices]**2).sum())
            newarray[i, 3] += n[indices].sum()
            data_unused[indices] = False
        else:
            new_used[i] = False

    # are there any data points left unused?
    if data_unused.any():
        raise UFitError('Merging data failed (data left over), check merging '
                        'algorithm for bugs')

    # remove any stops without monitor data
    newarray = newarray[new_used]

    # return array
    return newarray

def mergeList(tomerge):
    tomerge = array(tomerge)
    merged = tomerge.sum(axis = 0)
    merged[2] = sqrt((tomerge**2).sum(axis = 0)[2])
    merged[0] = merged[0] / len(tomerge)
    return merged;

def floatmerge(data, binsize):
    """Merging data based on floating window."""

    if binsize == 0:
        # no merging, just concatenate
        return data

    # sort data
    data = data[data[:,0].argsort()]

    lastvals = None
    tomerge =  []
    newlist =  []
    for vals in data:
        if lastvals != None:
            if vals[0] > lastvals[0] + binsize:
                #merge points in list:
                newlist.append(mergeList(tomerge))
                tomerge = []
        tomerge.append(vals)
        lastvals = vals
    newlist.append(mergeList(tomerge))

    # return array
    return array(newlist)
