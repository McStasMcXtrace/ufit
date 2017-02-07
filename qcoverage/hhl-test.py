import matplotlib.pyplot as plt
import bzplot as bp
import numpy as np


# Example of simple plotting of the BCT2 cuts in hhl plane:

# define gamma points around which to plot:
gpts = np.array([[0, 0], [1, 0], [2, 0], [0, 2], [1, 2], [2, 2]])
# create bz with lattice parameters a = 4 and c = 10 and plane perpendicular to vector 1 1 0
bzc = bp.BZCreator(gpts, 4.0, 10.0, [1, 1, 0])
# do the plotting
bzc.doPlot(plt.axes(), alph = 1, showLabels = False, lw = 1)
# show plot
plt.show()
