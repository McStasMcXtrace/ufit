Using ufit as a library
=======================

.. module:: ufit

Full noninteractive usage
-------------------------

The ``ufit.lab`` module
~~~~~~~~~~~~~~~~~~~~~~~

.. module:: ufit.lab

This module is a combination of ``pylab`` and ``ufit`` imports.  You can do ::

   from ufit.lab import *

at the top of your script and have all pylab (numpy + plotting) and ufit API
available.

Loading data
~~~~~~~~~~~~

.. currentmodule:: ufit

.. autofunction:: set_datatemplate

.. autofunction:: set_dataformat

.. autofunction:: read_data

.. autofunction:: read_numors

.. autofunction:: as_data

.. class:: Dataset

   .. attribute:: name

      The name of the dataset, usually the file number.

   .. attribute:: x
                  y
                  dy

      The X, Y and Y error data as used for fitting.  Normalization is already
      performed on these array.

   .. attribute:: mask

      A boolean array of the same size as the data.  Data points for which this
      array is `False` are not used for fitting.  This can be used to mask out
      "bad" datapoints.

   .. attribute:: fitmin
                  fitmax

      If not None, these two attributes can be used to restrict the X range of
      the data that is used for fitting, similar to :attr:`mask`.

   .. automethod:: plot

   .. automethod:: merge


Plotting mappings
~~~~~~~~~~~~~~~~~

.. autofunction:: do_mapping


Constructing models
~~~~~~~~~~~~~~~~~~~

.. class:: Model

   .. automethod:: add_params

   .. automethod:: fit

   .. automethod:: global_fit

      See :ref:`global-fit`.

   .. automethod:: plot

   .. automethod:: plot_components

      See :ref:`model-components`.

.. autofunction:: fixed

.. autofunction:: expr

.. autofunction:: overall

.. autofunction:: datapar

.. autofunction:: datainit

.. autofunction:: limited


Working with results
~~~~~~~~~~~~~~~~~~~~

.. class:: Result

   .. attribute:: params

      The final list of parameters, as :class:`Param` objects.

   .. attribute:: paramdict

      The final parameters, keyed by name.

   .. attribute:: paramvalues

      A dictionary mapping parameter names to parameter values only.

   .. attribute:: paramerrors

      A dictionary mapping parameter names to parameter errors only.

   .. attribute:: values

      A list of values for each parameter.

   .. attribute:: errors

      A list of errors for each parameter.

   .. attribute:: results

      A list of values, then errors for each parameter and the chi-squared
      value.

   .. attribute:: residuals

      An array of the residuals.

   .. automethod:: plot

   .. automethod:: plotfull

   .. automethod:: printout

   .. attribute:: xx
                  yy

      *xx* is a fine-spaced array of X values between the minimum and the
      maximum of the data X values.  *yy* are the corresponding Y values from
      the model evaluated with the final parameters.

      This can be used for custom plotting.


Scripting usage with GUI assistance
-----------------------------------

For harder fitting problems, it is often impossible to select good initial
parameter values that will make the fit succeed.  For these cases, ufit provides
the fitting part of the full GUI for a combination of noninteractive processing
with interactive fitting.

.. module:: ufit.gui

.. function:: start_fitter(model, data, fit=True)

   Start the GUI fitter component with the given model and dataset.  The user
   can start the fitting process and change parameter values iteratively.
   If *fit* is true, a first fitting pass is started automatically with the
   initial parameter values.

   The function returns a :class:`Result` object with the last fit result after
   the user clicks "Close".

   Usage example::

      # ... (import ufit and load data)
      data = read_data(...)

      # create a model of a simple Gaussian peak with given initial guess
      model = Background() + Gauss('peak', pos=97.5, ampl=100, fwhm=0.5)

      # fit the model, then print and plot the result
      result = start_fitter(model, data)

      # now process the result further, e.g. print the result
      result.printout()


A similar method exists to let the user select the data file with a GUI, and
then do further processing automatically (or call :func:`start_fitter` at some
point):

.. function:: start_loader()

   Start the GUI data loader component.  The user can preview data files and
   finally click "Open", after which the function returns a list of datasets
   loaded.


Backend selection
-----------------

.. currentmodule:: ufit

.. autofunction:: set_backend

   See :ref:`backends`.
