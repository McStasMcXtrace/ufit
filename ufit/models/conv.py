# ufit convolution model

from numpy import convolve, exp, log, linspace

from ufit.param import Param
from ufit.models.base import Model

__all__ = ['GaussianConvolution']


class GaussianConvolution(Model):
    """Models a 1-D convolution with a Gaussian kernel.

    Parameters:

    * `width` - FWHM of Gaussian kernel
    """

    def __init__(self, model, width=1):
        self._model = model
        if model.name:
            self.name = '%s_conv' % model.name
        else:
            self.name = 'conv'
        self.params = model.params[:]
        pname = self.name + '_width'
        self.params.append(Param.from_init(pname, width))

        def convfcn(p, x):
            data = model.fcn(p, x)
            # construct Gaussian filter
            N = len(x)   # number of data points
            M = 2*N - 1  # number of filter points
            # "valid" convolution mode now returns M - N + 1 == N points
            binwidth = (x.max() - x.min()) / len(x)
            filtx = linspace(-N*binwidth, N*binwidth, M)
            filt = exp(-filtx**2 / p[pname]**2 * 4*log(2))
            # normalize filter
            filt /= filt.sum()
            return convolve(data, filt, mode='valid')
        self.fcn = convfcn
