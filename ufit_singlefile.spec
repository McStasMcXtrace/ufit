# -*- mode: python -*-

options = [ ('v', None, 'OPTION') ]

a = Analysis(['ufitgui'],
             pathex=['.'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=['rthook_pyqt4.py'])

ui = Tree('ufit/gui/ui', 'ufit/gui/ui')

data = Tree('ufit/data', 'ufit/data', excludes=['*.pyc'])

backends = Tree('ufit/backends', 'ufit/backends', excludes=['*.pyc'])

models = Tree('ufit/models', 'ufit/models', excludes=['*.pyc'])

gui = Tree('ufit/gui', 'ufit/gui', excludes=['*.pyc'])

pyz = PYZ(a.pure)

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
          name='Ufit.exe',
          debug=False,
          strip=None,
          upx=False,
          console=True )       