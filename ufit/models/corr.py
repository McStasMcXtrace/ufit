# models for corrections

from numpy import exp, sqrt, arcsin, tan, pi

from ufit.models import Model

class CKI_Corr(Model):
    def __init__(self, name='', ki=None, dval='3.355'):
        pki, pdv = self._init_params(name, ['ki', 'dval'], locals())
        def fcn(p, x):
            kf = sqrt(p[pki]**2 - x/2.072)
            return kf**3/tan(arcsin(pi/kf/p[pdv]))
        self.fcn = fcn


class Bose(Model):
    def __init__(self, name='', tt=None):
        ptt, = self._init_params(name, ['tt'], locals())
        self.fcn = lambda p, x: x / (1. - exp(-11.6045*x / p[ptt]))
