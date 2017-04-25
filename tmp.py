
from ufit.lab import *

d = as_data(array([ 1.9977,  2.1034,  2.2055,  2.2992,  2.4078,  2.4985,  2.6092,
        2.7063,  2.8043,  2.9082,  3.008 ,  3.1036,  3.2051,  3.3024,
        3.4057,  3.5047,  3.6046,  3.6947,  3.8015,  3.8985,  3.9963,
        4.1003,  4.1998,  4.3   ,  4.4011,  4.4973,  4.5943,  4.6979,
        4.7965,  4.8958,  4.9959,  5.1029,  5.2046,  5.3073,  5.4046,
        5.5026,  5.6014,  5.701 ,  5.795 ,  5.896 ,  5.9979,  6.1133,
        6.2103,  6.3015,  6.4064,  6.4989,  6.592 ,  6.6992,  6.7937,
        6.8956,  6.9983,  7.0948,  7.192 ,  7.3039,  7.4167,  7.509 ,
        7.6091,  7.7099,  7.8041,  7.9062,  8.0017,  8.1053,  8.1946,
        8.2995,  8.3975,  8.4962,  8.5956,  8.6956,  8.7963,  8.8899,
        8.9919,  9.0945,  9.1979,  9.2939,  9.3905,  9.4959,  9.5937,
        9.6922,  9.7913,  9.891 ,  9.9914]), array([  53.,   46.,   50.,   45.,   43.,   39.,   42.,   47.,   51.,
         68.,   53.,   59.,   63.,   81.,   74.,  126.,  126.,  172.,
        242.,  300.,  380.,  435.,  495.,  568.,  694.,  687.,  756.,
        732.,  733.,  697.,  607.,  633.,  514.,  491.,  397.,  363.,
        316.,  286.,  234.,  208.,  151.,  160.,  152.,  127.,  158.,
        169.,  188.,  190.,  219.,  219.,  238.,  301.,  280.,  296.,
        366.,  330.,  296.,  314.,  320.,  292.,  268.,  231.,  212.,
        195.,  158.,  111.,  119.,  102.,   84.,   83.,   77.,   64.,
         75.,   65.,   78.,   81.,   71.,   74.,   82.,   70.,   74.]), array([  7.28010989,   6.78232998,   7.07106781,   6.70820393,
         6.55743852,   6.244998  ,   6.4807407 ,   6.8556546 ,
         7.14142843,   8.24621125,   7.28010989,   7.68114575,
         7.93725393,   9.        ,   8.60232527,  11.22497216,
        11.22497216,  13.11487705,  15.55634919,  17.32050808,
        19.49358869,  20.85665361,  22.24859546,  23.83275058,
        26.34387974,  26.21068484,  27.49545417,  27.05549852,
        27.07397274,  26.40075756,  24.63736999,  25.15949125,
        22.6715681 ,  22.15851981,  19.92485885,  19.05255888,
        17.77638883,  16.91153453,  15.29705854,  14.4222051 ,
        12.28820573,  12.64911064,  12.32882801,  11.26942767,
        12.56980509,  13.        ,  13.7113092 ,  13.78404875,
        14.79864859,  14.79864859,  15.42724862,  17.34935157,
        16.73320053,  17.20465053,  19.13112647,  18.16590212,
        17.20465053,  17.72004515,  17.88854382,  17.08800749,
        16.37070554,  15.19868415,  14.56021978,  13.96424004,
        12.56980509,  10.53565375,  10.90871211,  10.09950494,
         9.16515139,   9.11043358,   8.77496439,   8.        ,
         8.66025404,   8.06225775,   8.83176087,   9.        ,
         8.42614977,   8.60232527,   9.05538514,   8.36660027,   8.60232527]), '20110')

d.meta['p1'] = 4.5; d.meta['p2'] = 7.5;

#This is working
#model = SlopingBackground('bg',slope=overall(0),bkgd=overall(100)) \
#      + Gauss('p1', pos=datapar('p1'), ampl=700, fwhm=0.5) \
#      + Gauss('p2', pos=datapar('p2'), ampl=700, fwhm=0.5)
#This is not working:
model = SlopingBackground('bg',slope=overall(0),bkgd=overall(100)) \
      + Gauss('p1', pos=datainit('p1'), ampl=700, fwhm=0.5) \
      + Gauss('p2', pos=datainit('p2'), ampl=700, fwhm=0.5)
        
ds = [d]
results = model.global_fit(ds)
for result in results:
    result.printout()
    result.plot()
    show()