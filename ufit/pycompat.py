#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Python 2/3 utility functions and classes."""

import six

# For consistency import everything from "six" here.
from six.moves import builtins, cPickle, queue
from six import reraise, exec_, add_metaclass, BytesIO, StringIO
from six import string_types, integer_types, text_type, binary_type
from six import iteritems, itervalues, iterkeys, PY2

if six.PY2:
    listitems = dict.items
    listvalues = dict.values
else:
    def listitems(d):
        return list(d.items())
    def listvalues(d):
        return list(d.values())

# all builtin number types (useful for isinstance checks)
number_types = integer_types + (float,)

# missing str/bytes helpers

if six.PY2:
    # encode str/unicode (Py2) or str (Py3) to bytes, using selected encoding
    def from_encoding(s, encoding, errors='strict'):
        if isinstance(s, unicode):
            return s
        return s.decode(encoding, errors)
    def srepr(u):
        """repr() without 'u' prefix for Unicode strings."""
        if isinstance(u, unicode):
            return repr(u.encode('unicode-escape'))
        return repr(u)
else:
    # on Py3, UTF-8 is the default encoding already
    def from_encoding(s, encoding, errors='strict'):
        if isinstance(s, str):
            return s
        return s.decode(encoding, errors)
    srepr = repr
