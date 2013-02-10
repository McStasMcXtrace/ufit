# ufit data loading/reading routines

from numpy import ones

from ufit import UFitError
from ufit.data.run import Run, RunList
from ufit.data.ill import read_data as read_data_ill
from ufit.data.nicos import read_data as read_data_nicos

data_formats = {
    'ill': read_data_ill,
    'nicos': read_data_nicos,
}

__all__ = ['Data', 'runs', 'set_datatemplate', 'set_dataformat', 'read_data']


class Data(object):
    def __init__(self, x, y, dy, name, meta, xcol, ycol):
        self.name = name
        self.x = x
        self.y = y
        self.meta = meta
        if dy is None:
            self.dy = ones(len(x))
        else:
            self.dy = dy
        if not (len(x) == len(y) == len(self.dy)):
            raise UFitError('X, Y and DY must be of same length')
        self.xcol = xcol
        self.ycol = ycol

    def __repr__(self):
        return '<Data %s (%d points)>' % (self.name, len(self.x))


runs = RunList()

dtempl = '%d'
reader = data_formats['nicos']

def set_datatemplate(s):
    global dtempl
    dtempl = s

def set_dataformat(s):
    global reader
    reader = data_formats[s]

def read_data(n, xcol, ycol, mcol=None, mscale=1):
    colnames, coldata, meta = reader(n, dtempl % n)
    run = Run(str(n), colnames, coldata, meta, xcol, ycol, mcol, mscale)
    runs[n] = run
    return run
