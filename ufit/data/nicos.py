# ufit NICOS data reader

import time
from numpy import loadtxt


def read_data(fnum, filename):
    entries = {}
    fp = open(filename, 'rb')
    dtline = fp.readline()
    if not dtline.startswith('### NICOS data file'):
        raise ValueError('%r does not appear to be a NICOS data file' %
                         filename)
    ctime = time.mktime(time.strptime(
        dtline[len('### NICOS data file, created at '):].strip(),
        '%Y-%m-%d %H:%M:%S'))
    entries['created'] = ctime
    for line in iter(fp.readline, ''):
        if line.startswith('### Scan data'):
            break
        if line.startswith('# '):
            items = line.strip().split(None, 3)
            try:
                val, unit = items[3].split(None, 1)
                val = float(val)
            except (IndexError, ValueError):
                try:
                    val = float(items[3])
                except ValueError:
                    val = items[3]
                except IndexError:
                    continue
                unit = None
            key = items[1]
            if key.endswith('_value'):
                key = key[:-6]
            entries[key] = val
    if 'filename' in entries:
        entries['__name__'] = entries['filename']
    colnames = fp.readline()[1:].split()
    colunits = fp.readline()[1:].split()
    def convert_value(s):
        try:
            return float(s)
        except ValueError:
            return 0.0  # XXX care for string columns?!
    cvdict = dict((i, convert_value) for i in range(len(colnames))
                  if colnames[i] != ';')
    colnames = [name for name in colnames if name != ';']
    colunits = [unit for unit in colunits if unit != ';']
    usecols = cvdict.keys()
    coldata = loadtxt(fp, converters=cvdict, usecols=usecols)
    if 'Ts' in colnames:
        tindex = colnames.index('Ts')
        entries['Ts'] = coldata[:,tindex].mean()
    if 'B' in colnames:
        tindex = colnames.index('B')
        entries['B'] = coldata[:,tindex].mean()
    return colnames, coldata, entries
