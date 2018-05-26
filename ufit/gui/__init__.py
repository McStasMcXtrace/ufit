#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Fitting/plotting GUI for ufit."""

import sys
import time
import optparse
from os import path

t0 = time.time()

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QApplication, QSplashScreen, QPixmap, QMessageBox

from ufit.gui.loggers import getLogger
logger = getLogger('ufit')

from ufit import __version__
from ufit.gui.common import SettingGroup
from ufit.gui.fitter import start as start_fitter
from ufit.gui.dataloader import start as start_loader
from ufit.gui.main import UFitMain
from ufit.utils import extract_template

import ufit.guiresource  # register icon resources

__all__ = ['start_fitter', 'start_loader']


def main():
    app = QApplication([])
    app.setOrganizationName('ufit')
    app.setApplicationName('gui')

    pixmap = QPixmap(':/splash.png')
    splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)
    splash.showMessage(u'Loading...' + u'\xa0' * 10 + '\n\n',
                       Qt.AlignRight | Qt.AlignBottom)
    splash.show()
    time.sleep(0.1)
    with SettingGroup('main') as settings:
        if settings.value('current_version', '') != __version__:
            settings.setValue('current_version', __version__)
            # Execute here the actions to be performed only once after
            # each update (there is nothing there for now, but it could
            # be useful some day...)
            logger.info('Upgrade to version %s finished' % __version__)
    app.processEvents()


    def log_unhandled(*exc_info):
        logger.error('Unhandled exception in Qt callback', exc_info=exc_info)
    sys.excepthook = log_unhandled

    t1 = time.time()
    logger.info('Startup: import finished (%.3f s), starting GUI...' % (t1-t0))

    mainwindow = UFitMain()

    parser = optparse.OptionParser(usage='''\
    Usage: %prog [-b directory] [.ufit file | data file]
    ''')
    parser.add_option('-b', '--browse', action='store', metavar='DIR',
                      help='open browse window in specified directory')

    opts, args = parser.parse_args()

    if len(args) >= 1:
        datafile = path.abspath(args[0])
        if path.isdir(datafile):
            # directory given, treat it as -b argument (browse)
            opts.browse = datafile
        elif datafile.endswith('.ufit'):
            try:
                mainwindow.filename = datafile
                mainwindow.load_session(datafile)
            except Exception as err:
                QMessageBox.warning(mainwindow,
                                    'Error', 'Loading failed: %s' % err)
                mainwindow.filename = None
        else:
            dtempl, numor = extract_template(datafile)
            mainwindow.dloader.set_template(dtempl, numor, silent=False)
    mainwindow.show()
    if opts.browse:
        mainwindow.dloader.open_browser(opts.browse)

    t2 = time.time()
    logger.info('Startup: loading finished (%.3f s), main window opened' % (t2-t1))
    splash.deleteLater()
    app.exec_()
