# data merging

from numpy import arange, ones, zeros

from ufit import UFitError


def rebin(x, y, n, binsize):
    """Simple rebinning of (x, y, n) data."""

    # calculate new x values
    halfbinsize = binsize/2.
    stops = arange(x.min() - (x.min() % binsize) - binsize,
                   x.max() - (x.max() % binsize) + 2*binsize,
                   binsize) + halfbinsize
    nbins = len(stops)

    # newarray will be the new x, y, m array
    newarray = zeros((nbins, 3))
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
            newarray[i, 2] += n[indices].sum()
            data_unused[indices] = False
        else:
            new_used[i] = False

    # are there any data points left unused?
    if data_unused.any():
        raise UFitError('merging data failed (data left over), check algorithm')

    # remove any stops without monitor data
    newarray = newarray[new_used]

    # return array
    return newarray
