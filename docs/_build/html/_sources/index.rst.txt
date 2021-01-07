.. GOES-2-go documentation master file, created by
   sphinx-quickstart on Wed Jan  6 23:27:49 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. image:: _static/goes2go_logo.png

.. toctree::
   :glob:
   :maxdepth: 1
   :caption: ⚙ Code

   /goes2go

These python functions can help you download GOES-R series NetCDF files from the `Amazon Web Services <https://registry.opendata.aws/noaa-goes/>`_ archive.

Download Data
-------------
The following example downloads GOES 16 ABI multichannel file on the fixed grid for the CONUS domain and reads it with xarray for the latest image and an image nearest a specific time.

.. code-block:: python

   from goes2go.data import goes_latest, goes_nearesttime

   # Get latest data
   G1 = goes_latest(satellite='G16', product='ABI')

   # Get data for a specific time
   G2 = goes_nearesttime(datetime(2020,10,1), satellite='G16', product='GLM')

RGB Recipes
-----------
Generate RGB arrays for different RGB products. Check out this `notebook <https://github.com/blaylockbk/goes2go/blob/master/notebooks/DEMO_rgb_recipies.ipynb>`_ for a demonstration.

.. figure:: _static/TrueColor.png
   :class: img-fluid

   ABI TrueColor RGB image

Field of View
-------------
See notebooks for `GLM <https://github.com/blaylockbk/goes2go/blob/master/notebooks/GLM_field-of-view.ipynb>`_ and `ABI <https://github.com/blaylockbk/goes2go/blob/master/notebooks/ABI_field-of-view.ipynb>`_ field of view.

GOES-West is centered over -137 W and GOES-East is centered over -75 W. When GOES was being tested, it was in a "central" position, outlined in the dashed black line. Below is the ABI field of view for the full disk:

.. figure:: _static/ABI_field-of-view.png
   :class: img-fluid

   ABI full disk field of view

The GLM field of view is slightly smaller and limited by a bounding box. The field of view can be estimated.

.. figure:: _static/ABI_field-of-view.png
   :class: img-fluid

   Approximate GLM field of view


More notebooks
--------------
`GitHub notebooks <https://github.com/blaylockbk/goes2go/tree/master/notebooks>`_ 


Useful Links
------------

- `📔 GOES-R Series Data Book <https://www.goes-r.gov/downloads/resources/documents/GOES-RSeriesDataBook.pdf>`_
- `🖥 Rammb Slider GOES Viewer <https://rammb-slider.cira.colostate.edu/>`_
- `💾 GOES on AWS <https://registry.opendata.aws/noaa-goes/>`_
- `🐍 Unidata Plot GOES Data <https://unidata.github.io/python-training/gallery/mapping_goes16_truecolor/>`_
- `🗺 Plotting tips form geonetcast blog <https://geonetcast.wordpress.com/2019/08/02/plot-0-5-km-goes-r-full-disk-regions/>`_
- `🐍 glmtools <https://github.com/deeplycloudy/glmtools/>`_


.. note::
   **This page is a work in progress.** I'm doing SynopticPy and GOES-2-go 
   with the PyData theme and HRRR-B with the ReadTheDocs theme.
