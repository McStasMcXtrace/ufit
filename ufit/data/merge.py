#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Data merging routines."""

from numpy import arange, ones, zeros, sqrt, array, append, reshape

from ufit import UFitError


def rebin(data, binsize, meta=[]):
    """Simple rebinning of (x, y, dy, n) data and col_ meta."""

    if binsize == 0:
        # no merging, just concatenate
        return data

    x, y, dy, n = data.T
    # copy meta
    new_meta = meta.copy()
    # identify columns
    metanames = []
    if meta != []:
        for col in meta:
            if not col.startswith('col_'):
                continue
            # add column to data
            metanames.append(col)

    # calculate new x values

    halfbinsize = binsize/2.
    stops = arange(x.min() - (x.min() % binsize) - binsize,
                   x.max() - (x.max() % binsize) + 2*binsize,
                   binsize) + halfbinsize
    nbins = len(stops)

    # newarray will be the new x, y, dy, n and meta columns array
    newarray = zeros((nbins, 4 + len(metanames)))
    newarray[:, 0] = stops

    # this will keep track which data values we already used
    data_unused = ones(len(x), bool)

    # this will keep track which new bins are used; unused ones are
    # left out
    new_used = ones(nbins, bool)

    for i in range(nbins):
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
            for j, m in enumerate(metanames):
                newarray[i, 4 + j] += meta[m][indices].sum() / sum(indices)
        else:
            new_used[i] = False
    # are there any data points left unused?
    if data_unused.any():
        raise UFitError('Merging data failed (data left over), check merging '
                        'algorithm for bugs')

    # remove any stops without monitor data
    newarray = newarray[new_used]

    # extract merged meta information
    for i, m in enumerate(metanames):
        new_meta[m] = array(newarray[:,4 + i])
    # return arrays
    return array(newarray[:,:4]), new_meta


def mergeList(tomerge):
    tomerge = array(tomerge)
    merged = tomerge.sum(axis = 0)
    merged[2] = sqrt((tomerge**2).sum(axis = 0)[2])
    merged[0] = merged[0] / len(tomerge)
    # average meta
    merged[4:] = [x / len(tomerge) for x in merged[4:]]
    return merged


def floatmerge(data, binsize, meta = []):
    """Merging data based on floating window."""

    if binsize == 0:
        # no merging, just concatenate
        return data

    # sort data
    sortorder = data[:, 0].argsort()
    data = data[sortorder]
    # sort meta and empty new meta columns
    new_meta = meta.copy()
    metanames = []
    if meta:
        for col in meta:
            if not col.startswith('col_'):
                continue
            # add column to data
            metanames.append(col)
            data = append(data, reshape(meta.get(col, [])[sortorder], (-1, 1)),
                          axis=1)

    lastvals = []
    tomerge = []
    newlist = []

    for vals in data:
        if lastvals != []:  # no "if lastvals", could be an array
            if vals[0] > lastvals[0] + binsize:
                # merge points in list:
                newlist.append(mergeList(tomerge))
                tomerge = []
        tomerge.append(vals)
        lastvals = vals
    newlist.append(mergeList(tomerge))

    newlist = array(newlist)
    # extract merged meta information
    for i, m in enumerate(metanames):
        new_meta[m] = array(newlist[:, 4 + i])
    # return arrays
    return array(newlist[:, :4]), new_meta
