# ufit, universal fitting package


def debug(str):
    if __debug__:
        print str

class UFitError(Exception):
    pass

from ufit.result import *
from ufit.param import *
from ufit.data import *
from ufit.models import *
from ufit.backends import *
