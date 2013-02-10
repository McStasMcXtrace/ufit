# ufit data loading/reading routines

from ufit.data.run import Run, RunList
from ufit.data.ill import read_data as read_data_ill
from ufit.data.nicos import read_data as read_data_nicos

data_formats = {
    'ill': read_data_ill,
    'nicos': read_data_nicos,
}

__all__ = ['Run', 'runs', 'set_datatemplate', 'set_dataformat', 'read_data']


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
