# models for corrections

from numpy import exp, sqrt, arcsin, tan, pi

from ufit.models import Model


class Background(Model):
    """Model for a constant background.

    Parameters:
    * bkgd - the background
    """
    def __init__(self, name='', bkgd=0):
        pb, = self._init_params(name, ['bkgd'], locals())
        # background should be positive (XXX makes lmfit fail)
        ##if self.params[0].pmin is None:
        ##    self.params[0].pmin = 0

        self.fcn = lambda p, x: p[pb]


class SlopingBackground(Model):
    """Model for a sloping background.

    Parameters:
    * bkgd - constant factor
    * slope - slope coefficient
    """
    def __init__(self, name='', bkgd=0, slope=0):
        pb, ps = self._init_params(name, ['bkgd', 'slope'], locals())
        self.fcn = lambda p, x: p[pb] + x*p[ps]


class CKI_Corr(Model):
    """Model for correcting constant-ki scans.

    Parameters:
    * ki - the ki value in Ang-1
    * dval - the monochromator d-value in Ang
    """
    def __init__(self, name='', ki=None, dval='3.355'):
        pki, pdv = self._init_params(name, ['ki', 'dval'], locals())
        def fcn(p, x):
            kf = sqrt(p[pki]**2 - x/2.072)
            return kf**3/tan(arcsin(pi/kf/p[pdv]))
        self.fcn = fcn


class Bose(Model):
    """Model for correcting for Bose factor.

    Parameters:
    * tt - the temperature in K
    """
    def __init__(self, name='', tt=None):
        ptt, = self._init_params(name, ['tt'], locals())
        self.fcn = lambda p, x: 1 / (1. - exp(-11.6045*x / p[ptt]))
