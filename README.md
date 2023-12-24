<div
  align="center"
>

![](https://github.com/blaylockbk/goes2go/blob/main/docs/_static/goes2go_logo_100dpi.png?raw=true)

# Download and display GOES-East and GOES-West data

<!-- Badges -->

[![](https://img.shields.io/pypi/v/goes2go)](https://pypi.python.org/pypi/goes2go/)
[![Conda Version](https://img.shields.io/conda/vn/conda-forge/goes2go.svg)](https://anaconday.org/conda-forge/goes2go)
[![DOI](https://zenodo.org/badge/296737878.svg)](https://zenodo.org/badge/latestdoi/296737878)

![](https://img.shields.io/github/license/blaylockbk/goes2go)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Tests (Python)](https://github.com/blaylockbk/goes2go/actions/workflows/tests-python.yml/badge.svg)](https://github.com/blaylockbk/goes2go/actions/workflows/tests-python.yml)
[![Documentation Status](https://readthedocs.org/projects/goes2go/badge/?version=latest)](https://goes2go.readthedocs.io/?badge=latest)
[![Python](https://img.shields.io/pypi/pyversions/goes2go.svg)](https://pypi.org/project/goes2go/)
[![Conda Recipe](https://img.shields.io/badge/recipe-goes2go-green.svg)](https://anaconda.org/conda-forge/goes2go)
[![Conda Downloads](https://img.shields.io/conda/dn/conda-forge/goes2go.svg)](https://anaconda.org/conda-forge/goes2go)
[![Conda Platforms](https://img.shields.io/conda/pn/conda-forge/goes2go.svg)](https://anaconda.org/conda-forge/goes2go)

<!--(Badges)-->

</div>

GOES-East and GOES-West satellite data are made available on Amazon Web Services through [NOAA's Open Data Dissemination Program](https://www.noaa.gov/information-technology/open-data-dissemination). **GOES-2-go** is a python package that makes it easy to find and download the files you want from [AWS](https://registry.opendata.aws/noaa-goes/) to your local computer with some additional helpers to visualize and understand the data.

<hr>

<br>

# 📔 [GOES-2-go Documentation](https://goes2go.readthedocs.io/)

<br>

<hr>

# Installation

The easiest way to install `goes2go` and its dependencies is with [Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html) from conda-forge.

```
conda install -c conda-forge goes2go
```

You may also create the provided Conda environment, **[`environment.yml`](https://github.com/blaylockbk/goes2go/blob/main/environment.yml)**.

```bash
# Download environment file
wget https://github.com/blaylockbk/goes2go/raw/main/environment.yml

# Modify that file if you wish.

# Create the environment
conda env create -f environment.yml

# Activate the environment
conda activate goes2go
```

Alternatively, `goes2go` is published on PyPI and you can install it with pip, _but_ it requires some additional dependencies that you will have to install yourself:

- Python 3.8+
- [Cartopy](https://scitools.org.uk/cartopy/docs/latest/installing.html), which requires GEOS and Proj (if using `cartopy<0.22.0`).
- MetPy
- _Optional:_ [Carpenter Workshop](https://github.com/blaylockbk/Carpenter_Workshop)

When those are installed within your environment, _then_ you can install GOES-2-go with pip.

```bash
# Latest published version
pip install goes2go

# ~~ or ~~

# Most recent changes
pip install git+https://github.com/blaylockbk/goes2go.git
```

# Capabilities

- [Download GOES Data](#download-data)
- [Create RGB composites](#rgb-recipes)
- [Get the field of view](#field-of-view)

```mermaid
  graph TD;
      aws16[(AWS\nnoaa-goes16)] -.-> G
      aws17[(AWS\nnoaa-goes17)] -.-> G
      aws18[(AWS\nnoaa-goes18)] -.-> G
      G((. GOES 2-go .))
      G --- .latest
      G --- .nearesttime
      G --- .timerange
      .latest --> ds[(xarray.DataSet)]
      .nearesttime --> ds[(xarray.DataSet)]
      .timerange --> ds[(xarray.DataSet)]
      ds --- rgb[ds.rgb\naccessor to make RGB composites]
      ds --- fov[ds.FOV\naccessor to get field-of-view polygons]

      style G fill:#F8AF22,stroke:#259DD7,stroke-width:4px,color:#000000
```

## Download Data

Download GOES ABI or GLM NetCDF files to your local computer. Files can also be read with xarray.

First, create a GOES object to specify the satellite, data product, and domain you are interested in. The example below downloads the Multi-Channel Cloud Moisture Imagery for CONUS.

```python
from goes2go import GOES

# ABI Multi-Channel Cloud Moisture Imagry Product
G = GOES(satellite=16, product="ABI-L2-MCMIP", domain='C')

# Geostationary Lightning Mapper
G = GOES(satellite=17, product="GLM-L2-LCFA", domain='C')

# ABI Level 1b Data
G = GOES(satellite=17, product="ABI-L1b-Rad", domain='F')
```

> A complete listing of the products available are available [here](https://github.com/blaylockbk/goes2go/blob/main/goes2go/product_table.txt).

There are methods to do the following:

- List the available files for a time range
- Download data to your local drive for a specified time range
- Read the data into an xarray Dataset for a specific time

```python
   # Produce a pandas DataFrame of the available files in a time range
   df = G.df(start='2022-07-04 01:00', end='2022-07-04 01:30')
```

```python
   # Download and read the data as an xarray Dataset nearest a specific time
   ds = G.nearesttime('2022-01-01')
```

```python
   # Download and read the latest data as an xarray Dataset
   ds = G.latest()
```

```python
   # Download data for a specified time range
   G.timerange(start='2022-06-01 00:00', end='2022-06-01 01:00')

   # Download recent data for a specific interval
   G.timerange(recent='30min')
```

## RGB Recipes

The `rgb` xarray accessor computes various RGB products from a GOES ABI **_ABI-L2-MCMIP_** (multi-channel cloud and moisture imagry products) `xarray.Dataset`. See the [demo](https://goes2go.readthedocs.io/en/latest/user_guide/notebooks/DEMO_rgb_recipes.html#) for more examples of RGB products.

```python
import matplotlib.pyplot as plt
ds = GOES().latest()
ax = plt.subplot(projection=ds.rgb.crs)
ax.imshow(ds.rgb.TrueColor(), **ds.rgb.imshow_kwargs)
ax.coastlines()
```

![](./images/TrueColor.png)

## Field of View

The `FOV` xarray accessor creates `shapely.Polygon` objects for the ABI and GLM field of view. See notebooks for [GLM](https://goes2go.readthedocs.io/en/latest/user_guide/notebooks/field-of-view_GLM.html) and [ABI](https://goes2go.readthedocs.io/en/latest/user_guide/notebooks/field-of-view_ABI.html) field of view.

```python
from goes2go.data import goes_latest
G = goes_latest()
# Get polygons of the full disk or ABI domain field of view.
G.FOV.full_disk
G.FOV.domain
# Get Cartopy coordinate reference system
G.FOV.crs
```

GOES-West is centered over -137 W and GOES-East is centered over -75 W. When GOES was being tested, it was in a "central" position, outlined in the dashed black line. Below is the ABI field of view for the full disk:
![field of view image](./images/ABI_field-of-view.png)

The GLM field of view is slightly smaller and limited by a bounding box. Below is the approximated GLM field of view:
![field of view image](./images/GLM_field-of-view.png)

# How to Cite and Acknowledge

If GOES-2-go played an important role in your work, please [tell me about it](https://github.com/blaylockbk/goes2go/discussions/categories/show-and-tell)! Also, consider including a citation or acknowledgement in your article or product.

**_Suggested Citation_**

> Blaylock, B. K. (2023). GOES-2-go: Download and display GOES-East and GOES-West data (Version 2022.07.15) [Computer software]. https://github.com/blaylockbk/goes2go

**_Suggested Acknowledgment_**

> A portion of this work used code generously provided by Brian Blaylock's GOES-2-go python package (https://github.com/blaylockbk/goes2go)

### What if I don't like the GOES-2-go or Python?

As an alternative you can use [rclone](https://rclone.org/) to download GOES files from AWS. I quite like rclone. Here is a [short rclone tutorial](https://github.com/blaylockbk/pyBKB_v3/blob/master/rclone_howto.md).

<hr>

I hope you find this makes GOES data easier to retrieve and display. Enjoy!

\- Brian Blaylock

👨🏻‍💻 [Contributing Guidelines](https://goes2go.readthedocs.io/en/latest/user_guide/contribute.html)  
💬 [GitHub Discussions](https://github.com/blaylockbk/goes2go/discussions)  
🚑 [GitHub Issues](https://github.com/blaylockbk/goes2go/issues)  
🌐 [Personal Webpage](http://home.chpc.utah.edu/~u0553130/Brian_Blaylock/home.html)

P.S. If you like GOES-2-go, check out my other python packages

- [🏁 Herbie](https://github.com/blaylockbk/Herbie): download numerical weather model data
- [🌡️ SynopticPy](https://github.com/blaylockbk/SynopticPy): retrieve mesonet data from the Synoptic API.
- [🌹 Pandas-rose](https://github.com/blaylockbk/pandas-rose): easly wind rose from Pandas dataframe.

# Related Content

- [🙋🏻‍♂️ Brian's AWS GOES Web Downloader](https://home.chpc.utah.edu/~u0553130/Brian_Blaylock/cgi-bin/goes16_download.cgi)
- [📔 GOES-R Series Data Book](https://www.goes-r.gov/downloads/resources/documents/GOES-RSeriesDataBook.pdf)
- [🎠 Beginner's Guide](https://www.goes-r.gov/downloads/resources/documents/Beginners_Guide_to_GOES-R_Series_Data.pdf)
- [🖥 Rammb Slider GOES Viewer](https://rammb-slider.cira.colostate.edu)
- [💾 GOES on AWS](https://registry.opendata.aws/noaa-goes/)
- [🐍 Unidata Plot GOES Data](https://unidata.github.io/python-training/gallery/mapping_goes16_truecolor/)
- [🗺 Plotting tips form geonetcast blog](https://geonetcast.wordpress.com/2019/08/02/plot-0-5-km-goes-r-full-disk-regions/)
- [🐍 `glmtools`](https://github.com/deeplycloudy/glmtools/)
- [🐍 `satpy`](https://github.com/pytroll/satpy)
- [🖥 CSPPGEO](http://cimss.ssec.wisc.edu/csppgeo/) | [Gridded GLM software package](https://download.ssec.wisc.edu/files/csppgeo/)
