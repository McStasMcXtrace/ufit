# -*- mode: python -*-

import os
import sys
import subprocess
from os import path

rootdir = path.abspath('..')

# Make sure to generate the version file.
os.environ['PYTHONPATH'] = os.environ.get('PYTHONPATH', '') + path.pathsep + rootdir
subprocess.check_call([sys.executable,
                       path.join(rootdir, 'ufit', 'version.py')])

options = []

a = Analysis(['../ufitgui'],
             pathex=['..'],
             datas=[(path.join(rootdir, 'ufit', 'RELEASE-VERSION'), 'ufit')],
             hiddenimports=['scipy.interpolate', 'iminuit',
                            'ufit.gui.datawidgets', 'ipykernel.datapub'],
             hookspath=None,
             runtime_hooks=[])

ui = Tree('../ufit/gui/ui', 'ufit/gui/ui')

data = Tree('../ufit/data', 'ufit/data', excludes=['*.pyc'])

backends = Tree('../ufit/backends', 'ufit/backends', excludes=['*.pyc'])

models = Tree('../ufit/models', 'ufit/models', excludes=['*.pyc'])

gui = Tree('../ufit/gui', 'ufit/gui', excludes=['*.pyc'])

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(pyz,
          a.scripts,
          name='Ufit',
          debug=False,
          strip=None,
          upx=False,
          exclude_binaries=True,
          console=True)

coll = COLLECT(exe,
               ui,
               data,
               backends,
               models,
               gui,
               a.binaries,
               a.zipfiles,
               a.datas,
               name='Ufit',
               strip=None,
               upx=False)
