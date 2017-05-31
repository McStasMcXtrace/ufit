Introduction
============

ufit is a package inspired by several other fitting programs, e.g. PKfit, mfit
(both developed at ILL), and nfit2 (developed by M. Janoschek).

Its main goal is comprehensive fitting of neutron scattering data both for
noninteractive use and with the help of a GUI.


Features
--------

Free combination of models from basic models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A fitting function can be freely combined from different basic models, such as
peak forms or correction factors and background.  In combining the model
objects, they can be given names, so that every parameter gets a unique name,
which can then be referenced in constraints by other parameters.

For example, in this model::

   model = Background(bkgd=1) + Gauss('peak1', pos=97.5, ampl=100, fwhm=0.5) + \
       Gauss('peak2', pos=105, ampl=10, fwhm='peak1_fwhm')

the two Gauss peaks have different names "peak1" and "peak2", and the model
parameters are "peak1_pos", "peak2_pos", "peak1_ampl" and so forth.  The
Background model has no name of its own, so its "bkgd" parameter will also be
called "bkgd" in the final model.


Parameter constraints and limits
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parameters can have limits (if the fitting backend supports this), and can be
set to expressions involving other parameters *and* metadata from the data
files.

For example, in this model::

   model = Background(bkgd=1) + Gauss('peak1', pos=97.5, ampl=fixed(100), fwhm=0.5) + \
       Gauss('peak2', pos=105, ampl=limited(0, 20, 10), fwhm=expr('2*peak1_fwhm'))

the parameter "peak1_ampl" is fixed to a value of 100, the parameter
"peak2_ampl" has a limited range, and the parameter "peak2_fwhm" is constrained
to twice the value of "peak1_fwhm".


.. _global-fit:

Global fits
~~~~~~~~~~~

ufit can perform a so-called "global fit", i.e. a fit where multiple datasets
are used as the data points.  In the model, some parameters can be treated as
"global" (defined using :func:`.overall`), while others are specific to each
dataset.

This allows one to e.g. fit a series of spectra with a common background and
incoherent line width.

An example::

   from ufit.lab import *
   set_datatemplate('path/to/data%04d.dat')

   # read several data files
   datas = [read_data(n, 'EN', 'CNTS') for n in range(100, 110)]

   # create a model of a simple Gaussian peak with given initial guess
   model = Background(bkgd=overall(1)) + \
       Gauss('peak', pos=97.5, ampl=100, fwhm=overall(0.5))

   # fit the model, then print and plot all the results
   results = model.global_fit(datas)
   for result in results:
       result.printout()
       result.plot()
   show()

In this example, a Gaussian peak is fitted to all 10 datasets.  The background
level and peak width are defined as global parameters, while the peak position
and amplitude will be allowed to differ for each dataset.


.. _model-components:

Model components
~~~~~~~~~~~~~~~~

ufit thinks of a model as consisting of several "components".  For example, when
fitting several peaks to a spectrum, each peak is one of those components.  When
plotting a model fit, ufit can extract components from the model and plot them
separately, together with the combined model.


.. _backends:

Backends
~~~~~~~~

ufit uses other libraries to do the fitting.  For this purpose it has several
backends:

* `lmfit` -- uses the `lmfit`_ package written by Matthew Newville.

  lmfit builds upon the optimize functions available in SciPy, but adds the
  important capability to apply constraints and limits to parameters.

  By default, lmfit uses Levenberg-Marquardt least-squares, but other methods
  can be selected by a "method" keyword to the models' :meth:`.fit` method when
  using this backend.

* `minuit` -- uses the MINUIT package from CERN.

  Minuit has been the standard package for minimizing general N-dimensional
  functions in high-energy physics since its introduction in 1972.  It is the
  minimization engine used behind-the-scenes in most high-energy physics curve
  fitting applications.

  The Python bindings necessary to use this backend can be retrieved from
  `Github <iminuit>`_.  This backend supports parameter limits.

* `scipy` -- uses the `scipy.optimize.leastsq <leastsq>`_ function without any
  further wrapping.  This backend doesn't support parameter limits.

A backend is selected automatically on import, and a different one can be selected
using :func:`~ufit.set_backend`.

.. _lmfit: http://cars9.uchicago.edu/software/python/lmfit/
.. _iminuit: https://github.com/iminuit/iminuit/
.. _leastsq: http://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.leastsq.html
