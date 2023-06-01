Reference Guide
===============

.. toctree::
   :hidden:
   :maxdepth: 4

.. automodule:: goes2go.data
.. automodule:: goes2go.NEW

Custom Accessors
----------------

Field of View
^^^^^^^^^^^^^
Create polygon objects of the GOES field of view for the ABI and GLM instrument.
Access with the ``FOV`` accessor.

.. code-block:: python

   # Get latest multi-channel cloud moisture imagery product.
   # "G" is an xarray.Dataset of GOES data.
   G = GOES(satellite=16, product="ABI-L2-MCMIPC").latest()

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

   from goes2go import GOES
   import matplotlib.pyplot as plt

   # Get latest multi-channel cloud moisture imagery product.
   # "G" is an xarray.Dataset of multi-channel GOES data (e.g., product="ABI-L2-MCMIPC").
   G = GOES(satellite=16, product="ABI-L2-MCMIPC").latest()

   # Create RGB an plot
   tc = G.rgb.TrueColor()
   plt.imshow(tc)

   nc = G.rgb.NaturalColor()
   plt.imshow(nc)

   # etc.

   # Also can get the Cartopy coordinate reference system
   crs = G.rgb.crs


To make a simple RGB plot on a Cartopy axes, do the following:

.. code-block:: python

   from goes2go import GOES
   import matplotlib.pyplot as plt
   import cartopy.crs as ccrs

   # Download and read a GOES ABI MCMIPC dataset
   G = GOES(satellite=16, product="ABI-L2-MCMIPC").latest()

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
