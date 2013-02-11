# ufit data loading/reading routines

from numpy import array

from ufit import UFitError
from ufit.data import ill, nicos
from ufit.data.dataset import Dataset, DataList

data_formats = {
    'ill': ill,
    'nicos': nicos,
}

__all__ = ['Dataset', 'sets', 'set_datatemplate', 'set_dataformat',
           'read_data', 'as_data']


# XXX standardize column names (or select a few to standardize)

class Loader(object):
    def __init__(self):
        self.format = 'auto'
        self.template = '%d'
        self.sets = DataList()

    def _get_reader(self, filename, fobj):
        if self.format == 'auto':
            for n, m in data_formats.iteritems():
                if m.check_data(fobj):
                    return m
            raise UFitError('File %s not recognized')
        return data_formats[self.format]

    def load(self, n, xcol, ycol, mcol=None, mscale=1):
        filename = self.template % n
        fobj = open(filename, 'rb')
        colnames, coldata, meta = \
            self._get_reader(filename, fobj).read_data(filename, fobj)
        dset = Dataset(colnames, coldata, meta, xcol, ycol, mcol, mscale)
        self.sets[n] = dset
        return dset

    def guess_cols(self, n):
        filename = self.template % n
        fobj = open(filename, 'rb')
        colnames, coldata, meta = \
            self._get_reader(filename, fobj).read_data(filename, fobj)
        xguess, yguess, mguess = None, None, None
        if colnames[0].lower() in ('h', 'qh'):
            deviations = array([(cs.max()-cs.min()) for cs in coldata.T[:4]])
            xguess = colnames[deviations.argmax()]
        else:
            xguess = colnames[0]
        maxcts = 0
        maxmon = 0
        nmon = 0
        for i, colname in enumerate(colnames):
            if colname.lower().startswith(('ctr', 'cnts', 'det')):
                if coldata[:,i].sum() > maxcts:
                    yguess = colname
                    maxcts = coldata[:,i].sum()
            if colname.startswith('mon') or colname.startswith('M'):
                if coldata[:,i].sum() > maxmon:
                    mguess = colname
                    maxmon = coldata[:,i].sum()
                    # use average monitor counts for normalization, but
                    # round to 2 significant digits
                    nmon = int(float('%.2g' % coldata[:,i].mean()))
        return colnames, xguess, yguess, mguess, nmon


# simplified interface for usage in noninteractive scripts

global_loader = Loader()
sets = global_loader.sets

def set_datatemplate(s):
    global_loader.template = s

def set_dataformat(s):
    if s not in data_formats:
        raise UFitError('Unknown data format %r' % s)
    global_loader.format = s

def read_data(*args):
    return global_loader.load(*args)

def as_data(x, y, dy, name=''):
    return Dataset.from_arrays(name or 'data', x, y, dy)
