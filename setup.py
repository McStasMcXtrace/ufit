import os
from os import path

from setuptools import setup


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

ns = {'__file__': path.abspath(path.join(
    path.dirname(__file__), 'ufit', 'version.py'))}
exec(open("ufit/version.py").read(), ns)
version = ns['get_version']()

pkg_data = find_ui_files()
pkg_data.setdefault('ufit', []).append('RELEASE-VERSION')

setup(
    name = 'ufit',
    version = version,
    license = 'GPL',
    author = 'Georg Brandl',
    author_email = 'georg.brandl@frm2.tum.de',
    description = 'Universal scattering data fitting tool',
    url = 'https://bitbucket.org/birkenfeld/ufit/',
    packages = find_packages(),
    package_data = pkg_data,
    entry_points = {
        'gui_scripts': [
            'ufitgui=ufit.gui:main',
        ],
    },
)
