Reference Guide
===============

.. toctree::
   :hidden:
   :maxdepth: 4

.. automodule:: goes2go.data

Custom Accessors
----------------

Field of View
^^^^^^^^^^^^^
Create polygon objects of the GOES field of view for the ABI and GLM instrument.
Access with the ``FOV`` accessor.

.. code-block:: python

   # G is an xarray.Dataset of GOES data.
   G.FOV.domain  # only ABI datasets
   G.FOV.full_disk  # ABI or GLM datasets

   G.FOV.crs  # Cartopy coordinate reference system for the satellite.

.. autoclass:: goes2go.accessors.fieldOfViewAccessor
   :members:
   :inherited-members:

RGB Recipes
^^^^^^^^^^^
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


To make a simple RGB plot on a Cartopy axes, do the following:

.. code-block:: python

   from goes2go.data import goes_latest
   import matplotlib.pyplot as plt
   import cartopy.crs as ccrs

   # Download a GOES ABI dataset
   G = goes_latest(product='ABI')

   # Make figure on Cartopy axes
   ax = plt.subplot(projection=G.rgb.crs )
   ax.imshow(G.rgb.TrueColor(), **G.rgb.imshow_kwargs)
   ax.coastlines()

.. image:: /_static/demo_rgb_accessor.png

.. autoclass:: goes2go.accessors.rgbAccessor
   :members:
   :inherited-members:


..
   =========================================================================
   I would like to get the sphinx-autosummary-accessors to work, but I don't
   have it working at all.
   https://sphinx-autosummary-accessors.readthedocs.io/en/stable/index.html
