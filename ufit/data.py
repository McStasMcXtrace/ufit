# ufit, data loading routines

import time
import numpy

from ufit.core import Data

def read_file(filename):
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
    coldata = numpy.loadtxt(fp, converters=cvdict,
                            usecols=usecols, unpack=True)
    # optional:
    for (name, unit, data) in zip(colnames, colunits, coldata):
        entries[name] = data
    return entries

dtempl = '%d'

def set_datatemplate(s):
    global dtempl
    dtempl = s

def read_data(n, xcol='E'):
    d = read_file(dtempl % n)
    return Data(d[xcol], d['ctr1'], numpy.sqrt(d['ctr1']), str(n), d)
