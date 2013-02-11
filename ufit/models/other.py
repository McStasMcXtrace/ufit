# ufit other models

from numpy import cos, exp, pi

from ufit.models.base import Model


class Cosine(Model):
    """Cosine

    Parameters:
    * ampl - amplitude
    * freq - frequency (omega or k)
    * phase - phase in radians
    """
    param_names = ['ampl', 'freq', 'phase']

    def __init__(self, name='', ampl=None, freq=None, phase=0):
        pa, pf, pp = self._init_params(name, self.param_names, locals())
        self.fcn = lambda p, x: p[pa] * cos(p[pf]*x + p[pp])

    pick_points = ['a maximum', 'next minimum']

    def convert_pick(self, pmax, pmin):
        freq = pi/abs(pmin[0] - pmax[0])
        return {
            self.params[0].name: pmax[1] - pmin[1],           # amplitude
            self.params[1].name: freq,                        # frequency
            self.params[2].name: (- freq*pmax[0]) % (2*pi), # phase
        }
