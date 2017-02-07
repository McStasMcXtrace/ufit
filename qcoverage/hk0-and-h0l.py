import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import bzplot as bp
import numpy as np
import matplotlib as mpl

# more advanced example of the two cuts plotted together and aligned
f = plt.figure()
gs = gridspec.GridSpec(2, 1, height_ratios=[1, 1.8])
ax1 = f.add_subplot(gs[1])
ax2 = f.add_subplot(gs[0], sharex=ax1)

gpts = np.array([[0, 0], [0, 2], [1, 1], [2, 0], [2, 2], [3, 1]])
bzc = bp.BZCreator(gpts, a = 4.33148, c = 10.83387, plane = [0, 0, 1])
bzc.doPlot(ax1, alph = 1, showLabels = False, lw = 1)
ax1.set_ylim(0.2, 2.0)

gpts2 = np.array([[0, 0], [0, 2], [1, 1], [2, 0], [2, 2], [0, 4], [1, 3], [2, 4]])
bzc2 = bp.BZCreator(gpts, a = 4.33148, c = 10.83387, plane = [0, 1, 0])
bzc2.doPlot(ax2, alph = 1, showLabels = False, lw = 1)

ax2.set_ylim(0.0, 2.4)

plt.setp(ax2.get_xticklabels(), visible=False)
ax2.set_xlabel("")

f.subplots_adjust(hspace=0.05)

mpl.rcParams.update({'font.size': 22})
mpl.rcParams.update({'font.sans-serif': 'Verdana'})
mpl.rcParams.update({'font.family': 'sans-serif'})

ax1.yaxis.set_ticks(np.arange(0, 4, 0.5))
ax2.yaxis.set_ticks(np.arange(0, 4, 1))
for a in [ax1, ax2]:
    a.xaxis.set_ticks(np.arange(0, 4, 0.5))
    a.set_xlim(-0.3, 2.3)
    a.xaxis.set_tick_params(width=2, length=6)
    a.yaxis.set_tick_params(width=2, length=6)
    for axis in ['top', 'bottom', 'left', 'right']:
        a.spines[axis].set_linewidth(2)

plt.show()
