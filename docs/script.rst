Using ufit as a library
=======================

.. module:: ufit

Full noninteractive usage
-------------------------

.. autofunction:: set_datatemplate

.. autofunction:: set_dataformat

.. autofunction:: read_data

.. autofunction:: as_data

.. class:: Dataset

   .. attribute:: x
                  y
                  dy
                  norm

   .. attribute:: mask

   .. automethod:: plot

   .. automethod:: merge

.. class:: Model

   .. automethod:: add_params

   .. automethod:: fit

   .. automethod:: global_fit

   .. automethod:: plot

   .. automethod:: plot_components

.. function:: fixed

.. function:: expr

.. autofunction:: overall

.. autofunction:: datapar

.. autofunction:: limited

.. class:: Result

   .. automethod:: plot

   .. automethod:: plotfull

   .. automethod:: printout


Scripting usage with GUI assistance
-----------------------------------

.. module:: ufit.gui

.. autofunction:: start_fitter

.. autofunction:: start_loader


Backend selection
-----------------

.. currentmodule:: ufit

.. autofunction:: set_backend

