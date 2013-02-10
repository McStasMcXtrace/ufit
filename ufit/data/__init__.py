# ufit data loading/reading routines

from numpy import array

from ufit.data.run import Run, RunList
from ufit.data.ill import read_data as read_data_ill
from ufit.data.nicos import read_data as read_data_nicos

data_formats = {
    'ill': read_data_ill,
    'nicos': read_data_nicos,
}

__all__ = ['Run', 'runs', 'set_datatemplate', 'set_dataformat', 'read_data']


runs = RunList()

global_dtempl = '%d'
global_reader = data_formats['nicos']

def set_datatemplate(s):
    global global_dtempl
    global_dtempl = s

def set_dataformat(s):
    global global_reader
    global_reader = data_formats[s]

def read_data(n, xcol, ycol, mcol=None, mscale=1, reader=None, dtempl=None):
    colnames, coldata, meta = \
        (reader or global_reader)(n, (dtempl or global_dtempl) % n)
    run = Run(str(n), colnames, coldata, meta, xcol, ycol, mcol, mscale)
    runs[n] = run
    return run

# XXX standardize column names (or select a few to standardize)

def guess_cols(n, reader=None, dtempl=None):
    colnames, coldata, meta = \
        (reader or global_reader)(n, (dtempl or global_dtempl) % n)
    xguess, yguess, mguess = None, None, None
    if colnames[0].lower() in ('h', 'qh'):
        deviations = array([(cs.max()-cs.min()) for cs in coldata.T[:4]])
        xguess = colnames[deviations.argmax()]
    else:
        xguess = colnames[0]
    for colname in colnames:
        if colname.lower().startswith(('ctr', 'cnts')):
            yguess = colname
        if colname.startswith('mon') or colname.startswith('M'):
            mguess = colname
    return colnames, xguess, yguess, mguess
