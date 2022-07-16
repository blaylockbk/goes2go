<div
  align="center"
>

![](https://github.com/blaylockbk/goes2go/blob/main/docs/_static/goes2go_logo_100dpi.png?raw=true)

# Download and display GOES-East and GOES-West data

<!-- Badges -->

[![](https://img.shields.io/pypi/v/goes2go)](https://pypi.python.org/pypi/goes2go/)
![](https://img.shields.io/github/license/blaylockbk/goes2go)
[![DOI](https://zenodo.org/badge/296737878.svg)](https://zenodo.org/badge/latestdoi/296737878)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

<!--[![Join the chat at https://gitter.im/blaylockbk/goes2go](https://badges.gitter.im/blaylockbk/goes2go.svg)](https://gitter.im/blaylockbk/goes2go?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)-->
<!--(Badges)-->

</div>

GOES-East and GOES-West satellite data are made available on Amazon Web Services through [NOAA's Big Data Program](https://www.noaa.gov/information-technology/big-data). **GOES-2-go** is a python package that makes it easy to find and download the files you want to your local computer with some additional helpers to look at and understand the data.

---

<br>

# 📔 [GOES-2-go Documentation](https://blaylockbk.github.io/goes2go/_build/html/)

<br>

---

# Capabilities

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

The `rgb` xarray accessor creates an RGB product for a GOES ABI multichannel xarray.Dataset. See the [demo](https://blaylockbk.github.io/goes2go/_build/html/user_guide/notebooks/DEMO_rgb_recipes.html#) for more examples of RGB products.

```python
import matplotlib.pyplot as plt
ds = GOES().latest()
ax = plt.subplot(projection=ds.rgb.crs)
ax.imshow(ds.rgb.TrueColor(), **ds.rgb.imshow_kwargs)
ax.coastlines()
```

![](./images/TrueColor.png)

## Field of View

The `FOV` xarray accessor creates shapely.Polygon objects for the ABI and GLM field of view. See notebooks for [GLM](https://blaylockbk.github.io/goes2go/_build/html/user_guide/notebooks/field-of-view_GLM.html) and [ABI](https://blaylockbk.github.io/goes2go/_build/html/user_guide/notebooks/field-of-view_ABI.html) field of view.

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

> ### Useful Links
>
> - [🙋🏻‍♂️ Brian's AWS GOES Web Downloader](https://home.chpc.utah.edu/~u0553130/Brian_Blaylock/cgi-bin/goes16_download.cgi)
> - [📔 GOES-R Series Data Book](https://www.goes-r.gov/downloads/resources/documents/GOES-RSeriesDataBook.pdf)
> - [🎠 Beginner's Guide](https://www.goes-r.gov/downloads/resources/documents/Beginners_Guide_to_GOES-R_Series_Data.pdf)
> - [🖥 Rammb Slider GOES Viewer](https://rammb-slider.cira.colostate.edu)
> - [💾 GOES on AWS](https://registry.opendata.aws/noaa-goes/)
> - [🐍 Unidata Plot GOES Data](https://unidata.github.io/python-training/gallery/mapping_goes16_truecolor/)
> - [🗺 Plotting tips form geonetcast blog](https://geonetcast.wordpress.com/2019/08/02/plot-0-5-km-goes-r-full-disk-regions/)
> - [🐍 `glmtools`](https://github.com/deeplycloudy/glmtools/)
> - [🐍 `satpy`](https://github.com/pytroll/satpy)

> ### What if I don't like the GOES-2-go or Python?
>
> As an alternative you can use [rclone](https://rclone.org/) to download GOES files from AWS. I quite like rclone. Here is a [short rclone tutorial](https://github.com/blaylockbk/pyBKB_v3/blob/master/rclone_howto.md).

---

---

I hope you find this makes GOES data easier to retrieve and display. Enjoy!

\- Brian Blaylock

👨🏻‍💻 [Contributing Guidelines](https://blaylockbk.github.io/goes2go/_build/html/user_guide/contribute.html)  
💬 [GitHub Discussions](https://github.com/blaylockbk/goes2go/discussions)  
🚑 [GitHub Issues](https://github.com/blaylockbk/goes2go/issues)  
🌐 [Personal Webpage](http://home.chpc.utah.edu/~u0553130/Brian_Blaylock/home.html)

P.S. If you like GOES-2-go, check out my [Herbie](https://github.com/blaylockbk/Herbie) package to download weather model data and [SynopticPy](https://github.com/blaylockbk/Herbie) to download mesonet data from the Synoptic API.
