# ufit other models

from numpy import cos, exp, pi, log

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


class ExpDecay(Model):
    """Exponential decay

    Parameters:
    * y0  - value at x = 0
    * tau - decay constant: exp(-x/tau)
    * y1  - value at x -> infinity
    """
    param_names = ['y0', 'tau', 'y1']

    def __init__(self, name='', y0=1, tau=None, y1=0):
        p0, pt, p1 = self._init_params(name, self.param_names, locals())
        self.fcn = lambda p, x: p[p1] + (p[p0]-p[p1])*exp(-x/p[pt])

    pick_points = ['maximum value', 'minimum value', 'half maximum']

    def convert_pick(self, pmax, pmin, phalf):
        return {
            self.params[0].name: pmax[1],
            self.params[1].name: phalf[0]/log(2),
            self.params[2].name: pmin[1],
        }
