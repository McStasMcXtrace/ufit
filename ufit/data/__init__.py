# ufit data loading/reading routines

from numpy import array

from ufit import UFitError
from ufit.data import ill, nicos
from ufit.data.run import Run, RunList

data_formats = {
    'ill': ill,
    'nicos': nicos,
}

__all__ = ['Run', 'runs', 'set_datatemplate', 'set_dataformat', 'read_data']


# XXX standardize column names (or select a few to standardize)

class Loader(object):
    def __init__(self):
        self.format = 'auto'
        self.template = '%d'
        self.runs = RunList()

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
        run = Run(str(n), colnames, coldata, meta, xcol, ycol, mcol, mscale)
        self.runs[n] = run
        return run

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
        for i, colname in enumerate(colnames):
            if colname.lower().startswith(('ctr', 'cnts')):
                if coldata[:,i].sum() > maxcts:
                    yguess = colname
                    maxcts = coldata[:,i].sum()
            if colname.startswith('mon') or colname.startswith('M'):
                if coldata[:,i].sum() > maxmon:
                    mguess = colname
                    maxmon = coldata[:,i].sum()
        return colnames, xguess, yguess, mguess


# simplified interface for usage in noninteractive scripts

global_loader = Loader()
runs = global_loader.runs

def set_datatemplate(s):
    global_loader.template = s

def set_dataformat(s):
    if s not in data_formats:
        raise UFitError('Unknown data format %r' % s)
    global_loader.format = s

def read_data(*args):
    return global_loader.load(*args)

def as_data(x, y, dy, name=''):
    return Run.from_array(name, x, y, dy)
