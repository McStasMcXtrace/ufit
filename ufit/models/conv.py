# ufit convolution model

from numpy import convolve

from ufit.models.base import Model

__all__ = ['Convolution']


class Convolution(Model):
    """Models a 1-D convolution of two models."""

    def __init__(self, a, b):
        self._a = a
        self._b = b
        if a.name and b.name:
            self.name = 'conv(%s, %s)' % (a.name, b.name)
        else:
            self.name = a.name or b.name
        self._combine_params(a, b)

        self.fcn = lambda p, x: convolve(a.fcn(p, x), b.fcn(p, x), mode='same')
