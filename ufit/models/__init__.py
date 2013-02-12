#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013, Georg Brandl.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Models package for ufit."""

from ufit.models.base import *
from ufit.models.peaks import *
from ufit.models.corr import *
from ufit.models.conv import *
from ufit.models.other import *


# Concrete models that can be used in the simplified GUI interface.

concrete_models = [
    Gauss,
    Lorentz,
    Voigt,
    PseudoVoigt,
    DHO,
    Background,
    SlopingBackground,
    CKI_Corr,
    Bose,
    StraightLine,
    Parabola,
    Cosine,
    ExpDecay,
    PowerLaw,
]
