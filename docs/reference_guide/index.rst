Reference Guide
===============

.. toctree::
   :hidden:
   :maxdepth: 4

.. automodule:: goes2go.data

Custom Accessors
----------------

Field of View Accessor
^^^^^^^^^^^^^^^^^^^^^^
Create polygon objects of the GOES field of view for the ABI and GLM instrument.
Access with the ``FOV`` accessor.

.. code-block:: python

   # G is an xarray.Dataset of GOES data.
   G.FOV.domain  # only ABI datasets
   G.FOV.full_disk  # ABI or GLM datasets

.. autoclass:: goes2go.accessors.fieldOfViewAccessor
   :members:
   :inherited-members:

RGB Recipes Accessor
^^^^^^^^^^^^^^^^^^^^
RGB recipes for ABI multichannel cloud moisture imagery files.
Access with the ``rgb`` accessor. The RGB method will return a DataArray of the
RGB values and also attaches the RGB DataArray to the existing GOES Dataset.

.. code-block:: python

   # G is an xarray.Dataset of GOES data.
   G.rgb.TrueColor()
   G.rgb.NaturalColor()
   ... etc.

   # Also can get the Cartopy coordinate reference system
   G.rgb.crs

.. autoclass:: goes2go.accessors.rgbAccessor
   :members:
   :inherited-members:




..
   =========================================================================
   I would like to get the sphinx-autosummary-accessors to work, but I don't
   have it working at all.
   https://sphinx-autosummary-accessors.readthedocs.io/en/stable/index.html

   .. currentmodule:: xarray

   .. autosummary::
      :toctree: generated/
      :template: autosummary/accessor_attribute.rst

      Dataset.rgb.crs

   .. autosummary::
      :toctree: generated/
      :template: autosummary/accessor_method.rst

      Dataset.rgb.TrueColor

