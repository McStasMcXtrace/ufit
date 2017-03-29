import numpy as np
from sympy import symbols, init_printing, simplify

from ufit.pycompat import iteritems

#simple BZ symbolic calculations
#standalone script
a, c, pi = symbols('a c pi')

#primitive lattice in real space
a1 = [-a/2,  a/2,  c/2]
a2 = [ a/2, -a/2,  c/2]
a3 = [ a/2,  a/2, -c/2]

#convert to reciprocal space:
b1 = 2 * pi * np.cross(a2, a3) / np.dot(a1, np.cross(a2, a3))
b2 = 2 * pi * np.cross(a3, a1) / np.dot(a2, np.cross(a3, a1))
b3 = 2 * pi * np.cross(a1, a2) / np.dot(a3, np.cross(a1, a2))


zeta = a*a / (2*c*c)
eta = (1 + a*a/(c*c))/4


sympoints = {  "Gamma": [0,0,0],
         "X": [0  ,  0, 0.5],
         "N": [0  ,0.5,   0],
         "Z": [0.5,0.5,-0.5],
         "P": [0.25,0.25, 0.25],
         "Y": [-zeta, zeta, 0.5],
         "Y1": [0.5, 0.5, -zeta],
         "Sigma": [-eta, eta, eta],
         "Sigma1": [eta, 1-eta, -eta],
        }

init_printing()
def mult(x,a,b,c): return x[0] * a + x[1] * b + x[2] * c
print(b1, b2, b3)
print()
init_printing()

for n, sp in iteritems(sympoints):
    h = simplify(mult(sp, b1, b2, b3)[0] * a/2/pi)
    k = simplify(mult(sp, b1, b2, b3)[1] * a/2/pi)
    l = simplify(mult(sp, b1, b2, b3)[2] * c/2/pi)

    print("%s\t%s\t%s\t%s" % (n, h, k, l))
