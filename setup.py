import os
from distutils.core import setup

def find_packages():
    """Return a list of all ufit subpackages."""
    out = ['ufit']
    stack = [('ufit', 'ufit.')]
    while stack:
        where, prefix = stack.pop(0)
        for name in os.listdir(where):
            fn = os.path.join(where, name)
            if '.' not in name and os.path.isdir(fn) and \
                    os.path.isfile(os.path.join(fn, '__init__.py')):
                out.append(prefix + name)
                stack.append((fn, prefix + name + '.'))
    return out

def find_ui_files():
    """Find all Qt .ui files in ufit.gui subpackages."""
    res = {}
    for root, dirs, files in os.walk('ufit/gui/ui'):
        uis = [uifile for uifile in files if uifile.endswith('.ui')]
        if uis:
            res[root.replace('/', '.')] = uis
    return res

import ufit

setup(
    name = 'ufit',
    version = ufit.__version__,
    license = 'GPL',
    author = 'Georg Brandl',
    author_email = 'georg.brandl@frm2.tum.de',
    description = 'Universal scattering data fitting tool',
    url = 'https://bitbucket.org/birkenfeld/ufit/',
    packages = find_packages(),
    package_data = find_ui_files(),
    scripts = ['ufitgui'],
)
