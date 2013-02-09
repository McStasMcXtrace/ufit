# ufit ILL data reader

from numpy import loadtxt

from ufit.data.run import Run


def read_data(fnum, filename):
    try:
        fp = open(filename)
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
        arr = loadtxt(fp, ndmin=2)
        if len(arr) == 0:
            print 'No data in', filename
            return None
        return Run(str(fnum), names, arr, x=xcol, meta=meta)
    except Exception, e:
        print 'Error reading', filename, '-', e
        return None
