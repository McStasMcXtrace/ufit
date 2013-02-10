# ufit ILL data reader

from numpy import loadtxt

from ufit import UFitError


def check_data(fp):
    dtline = fp.readline()
    fp.seek(0, 0)
    return dtline.startswith('RRRRRRRRRRRR')


def read_data(filename, fp):
    line = ''
    xcol = None
    meta = {}
    while line.strip() != 'DATA_:':
        if line.startswith('STEPS:'):
            parts = line[6:].strip().rstrip(',').split(', ')
            for part in parts:
                k, s = part.split('=')
                if float(s.strip()) != 0 or xcol is None:
                    xcol = k[1:]
        elif line.startswith('COMND:'):
            meta['CMND'] = line[7:].rstrip()
        elif line.startswith('PARAM:'):
            pass
            #if 'TT=' in line:
            #    parts = line[6:].strip().rstrip(',').split(', ')
            #    for part in parts:
            #        k, s = part.split('=')
            #        if k == 'TT':
            #            meta['TT'] = float(s)
        line = fp.readline()
        if not line:
            break
    names = fp.readline().split()
    usecols = range(len(names))
    if names[0] == 'PNT':
        usecols = range(1, len(names))
        names = names[1:]
    arr = loadtxt(fp, ndmin=2, usecols=usecols)
    if len(arr) == 0:
        raise UFitError('No data in %s' % filename)
    return names, arr, meta
