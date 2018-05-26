#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

import sys

import numpy as np

import ufit.lab as uf


class QReader(object):
    """Read and parse the datafiles"""

    def __init__(self, template, numors, tolerance = 0.01):
        """ The reader.
        template, numors - used by ufit read_numors for reading the data
        tolerance - maximum distance of points from plane to be included in reading
        """
        uf.set_datatemplate(template)
        try:
            self.datas = uf.read_numors(numors, 0)
        except:
            print("Unexpected error:", sys.exc_info()[1])
            self.datas = []

        self.tolerance = tolerance

    def get_points(self, v1, v2):
        """It will find points in read scan files which has hkle values
        These is then converted to (v1, v2) basis and calculated distance from it.
        Only inplane points are processed.
        """

        v = np.array([v1, v2, np.cross(v1, v2)]).transpose()
        pts = []
        for d in self.datas:
            # is it q-scan?
            if 'hkle' in d.meta:
                hkle = d.meta['hkle']
            else:
                print("File %s does not have hkle values for each point, skipping." % d.name)
                continue

            for h, k, l, E in hkle:
                # transform coordinates to v1 and v2 basis
                mycoords = np.linalg.solve(v, [h, k, l])
                if (abs(mycoords[2]) < self.tolerance):
                    pts.append([mycoords[0], mycoords[1], E])
                # else:
                #     print "out of plane reflection:", h, k, l

        return pts
