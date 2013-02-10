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
            meta['info'] = ' '.join(line[7:].rstrip().lower().split())
        elif line.startswith('TITLE:'):
            meta['title'] = line[6:].strip()
        elif line.startswith('PARAM:'):
            parts = line[6:].strip().rstrip(',').split(',')
            for part in parts:
                k, s = part.split('=')
                meta[k.strip()] = float(s.strip())
        elif line.startswith('INSTR:'):
            meta['instrument'] = line[6:].strip().lower()
        elif line.startswith('EXPNO:'):
            meta['experiment'] = line[6:].strip().lower()
        line = fp.readline()
        if not line:
            break
    names = fp.readline().split()
    usecols = range(len(names))
    if names[0] == 'PNT':
        usecols = range(1, len(names))
        names = names[1:]
    # Berlin implementation adds "Finished ..." in the last line,
    # pretend that it is a comment
    arr = loadtxt(fp, ndmin=2, usecols=usecols, comments='F')
    if len(arr) == 0:
        raise UFitError('No data in %s' % filename)
    return names, arr, meta
