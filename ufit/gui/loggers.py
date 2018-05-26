#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Logging utilities for ufit.

Mostly borrowed from nicos.utils.loggers.
"""

import os
import time
import traceback
from os import path
from logging import Formatter, Handler, StreamHandler, DEBUG, INFO, WARNING, \
    root, getLogger

__all__ = ['getLogger']

DATEFMT = '%H:%M:%S'

# console color utils

_codes = {}

_attrs = {
    'reset':     '39;49;00m',
    'bold':      '01m',
    'faint':     '02m',
    'standout':  '03m',
    'underline': '04m',
    'blink':     '05m',
}

for _name, _value in _attrs.items():
    _codes[_name] = '\x1b[' + _value

_colors = [
    ('black', 'darkgray'),
    ('darkred', 'red'),
    ('darkgreen', 'green'),
    ('brown', 'yellow'),
    ('darkblue', 'blue'),
    ('purple', 'fuchsia'),
    ('turquoise', 'teal'),
    ('lightgray', 'white'),
]

for _i, (_dark, _light) in enumerate(_colors):
    _codes[_dark] = '\x1b[%im' % (_i + 30)
    _codes[_light] = '\x1b[%i;01m' % (_i + 30)


def colorize(name, text):
    return _codes.get(name, '') + text + _codes.get('reset', '')


def colorcode(name):
    return _codes.get(name, '')


def nocolor():
    for key in list(_codes):
        _codes[key] = ''

if os.name == 'nt':
    try:
        # colorama provides ANSI-colored console output support under Windows
        import colorama  # pylint: disable=F0401
    except ImportError:
        nocolor()
    else:
        colorama.init()


class ConsoleFormatter(Formatter):
    """
    A lightweight formatter for the interactive console, with optional
    colored output.
    """

    def __init__(self, fmt=None, datefmt=None, colorize=None):
        Formatter.__init__(self, fmt, datefmt)
        if colorize:
            self.colorize = colorize
        else:
            self.colorize = lambda c, s: s

    def formatException(self, exc_info):
        return ''.join(traceback.format_exception(*exc_info))

    def formatTime(self, record, datefmt=None):
        return time.strftime(datefmt or DATEFMT,
                             self.converter(record.created))

    def format(self, record):
        levelno = record.levelno
        datefmt = self.colorize('lightgray', '[%(asctime)s] ')
        record.message = record.getMessage()
        if record.name == 'ufit':
            namefmt = ''
        else:
            namefmt = '%(name)s: '
        if levelno <= DEBUG:
            fmtstr = self.colorize('darkgray', '%s%%(message)s' % namefmt)
        elif levelno <= INFO:
            fmtstr = '%s%%(message)s' % namefmt
        elif levelno <= WARNING:
            fmtstr = self.colorize('fuchsia', '%s%%(levelname)s: %%(message)s'
                                   % namefmt)
        else:
            fmtstr = self.colorize('red', '%s%%(levelname)s: %%(message)s'
                                   % namefmt)
        fmtstr = datefmt + fmtstr
        record.asctime = self.formatTime(record, self.datefmt)
        s = fmtstr % record.__dict__
        if record.exc_info:
            # *not* caching exception text on the record, since it's
            # only a short version
            s += '\n' + self.formatException(record.exc_info).rstrip()
        return s


LOGFMT = '%(asctime)s : %(levelname)-7s : %(name)s: %(message)s'
DATESTAMP_FMT = '%Y-%m-%d'
SECONDS_PER_DAY = 60 * 60 * 24


class LogfileHandler(StreamHandler):
    """
    Logs to log files with a date stamp appended, and rollover on midnight.
    """

    def __init__(self, directory, filenameprefix='ufit', dayfmt=DATESTAMP_FMT):
        if not path.isdir(directory):
            os.makedirs(directory)
        self._currentsymlink = path.join(directory, 'current')
        self._pathnameprefix = path.join(directory, filenameprefix)
        self._dayfmt = dayfmt
        # today's logfile name
        basefn = self._pathnameprefix + '-' + time.strftime(dayfmt) + '.log'
        self.baseFilename = path.abspath(basefn)
        self.stream = None
        Handler.__init__(self)   # don't open file yet
        # determine time of first midnight from now on
        t = time.localtime()
        self.rollover_at = time.mktime((t[0], t[1], t[2], 0, 0, 0,
                                        t[6], t[7], t[8])) + SECONDS_PER_DAY
        self.setFormatter(Formatter(LOGFMT, DATEFMT))

    def _open(self):
        # update 'current' symlink upon open
        try:
            os.remove(self._currentsymlink)
        except OSError:
            # if the symlink does not (yet) exist, OSError is raised.
            # should happen at most once per installation....
            pass
        if hasattr(os, 'symlink'):
            os.symlink(path.basename(self.baseFilename), self._currentsymlink)
        # finally open the new logfile....
        return open(self.baseFilename, 'a')

    def emit(self, record):
        try:
            t = int(time.time())
            if t >= self.rollover_at:
                self.doRollover()
            if self.stream is None:
                self.stream = self._open()
            StreamHandler.emit(self, record)
        except Exception:
            self.handleError(record)

    def close(self):
        self.acquire()
        try:
            if self.stream:
                self.flush()
                self.stream.close()
                self.stream = None
                Handler.close(self)
        finally:
            self.release()

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        self.baseFilename = self._pathnameprefix + '-' + \
            time.strftime(self._dayfmt) + '.log'
        self.rollover_at += SECONDS_PER_DAY


handler = StreamHandler()
fmter = ConsoleFormatter(colorize=colorize)
handler.setFormatter(fmter)
root.addHandler(handler)
loghandler = LogfileHandler(path.expanduser('~/.config/ufit'))
loghandler.setLevel(WARNING)
root.addHandler(loghandler)
root.setLevel(INFO)
