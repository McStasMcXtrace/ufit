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

options = [('v', None, 'OPTION')]

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
          ui,
          data,
          backends,
          models,
          gui,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='Ufit',
          debug=False,
          strip=None,
          upx=False,
          console=True)
