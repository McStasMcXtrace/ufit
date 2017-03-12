#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2017, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Fitting GUI windows for ufit."""

from ufit.gui.loggers import getLogger
logger = getLogger('ufit')

from ufit.gui.fitter import start as start_fitter
from ufit.gui.dataloader import start as start_loader

import ufit.guiresource  # register icon resources

__all__ = ['start_fitter', 'start_loader']
