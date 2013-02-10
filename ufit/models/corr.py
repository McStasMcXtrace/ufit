# models for corrections

from numpy import exp, sqrt, arcsin, tan, pi

from ufit.models import Model


class Background(Model):
    """Model for a constant background.

    Parameters:
    * bkgd - the background (forced to be nonnegative)
    """
    def __init__(self, name='', bkgd=0):
        pb, = self._init_params(name, ['bkgd'], locals())
        # background should be positive
        self.params[0].finalize = abs

        self.fcn = lambda p, x: abs(p[pb])

    def is_modifier(self):
        return True


class SlopingBackground(Model):
    """Model for a sloping background.

    Parameters:
    * bkgd - constant factor
    * slope - slope coefficient
    """
    def __init__(self, name='', bkgd=0, slope=0):
        pb, ps = self._init_params(name, ['bkgd', 'slope'], locals())
        self.fcn = lambda p, x: p[pb] + x*p[ps]

    def is_modifier(self):
        return True


class CKI_Corr(Model):
    """Model for correcting constant-ki scans.

    Parameters:
    * ki - the ki value in Ang-1
    * dval - the monochromator d-value in Ang
    """
    def __init__(self, name='', ki=None, dval='3.355'):
        pki, pdv = self._init_params(name, ['ki', 'dval'], locals())
        def fcn(p, x):
            ki = p[pki]
            kf = sqrt(ki**2 - x/2.072)
            return kf**3/ki**3 * tan(arcsin(pi/ki/p[pdv]))/tan(arcsin(pi/kf/p[pdv]))
        self.fcn = fcn

    def is_modifier(self):
        return True


class Bose(Model):
    """Model for correcting for Bose factor.

    Parameters:
    * tt - the temperature in K
    """
    def __init__(self, name='', tt=None):
        ptt, = self._init_params(name, ['tt'], locals())
        self.fcn = lambda p, x: x / (1. - exp(-11.6045*(x + 0.00001) / p[ptt]))

    def is_modifier(self):
        return True
