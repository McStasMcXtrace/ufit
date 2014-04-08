#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2014, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Logging utilities for ufit."""

import os
import time
import traceback
from logging import Formatter, StreamHandler, DEBUG, INFO, WARNING, root, \
    getLogger

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
        if record.name == 'nicos':
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

handler = StreamHandler()
fmter = ConsoleFormatter(colorize=colorize)
handler.setFormatter(fmter)
root.addHandler(handler)
root.setLevel(INFO)
