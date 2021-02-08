# 📔 [Documentation Page](https://blaylockbk.github.io/goes2go/_build/html/)


|![](https://blaylockbk.github.io/goes2go/_build/html/_static/goes2go_logo.png)|**Brian Blaylock**<br>🌐 [Webpage](http://home.chpc.utah.edu/~u0553130/Brian_Blaylock/home.html)<br>[🔩 PyPI](https://pypi.org/user/blaylockbk/)
|:--|:--|


# 🏃🏻‍♂️💨 🌎 🛰 GOES-2-go 

Download and read files from the NOAA GOES archive on AWS.http://home.chpc.utah.edu/~u0553130/Brian_Blaylock/hrrr_FAQ.html

Read doc strings for functions in `goes2go/` folder for full usage description.

>### Some Useful Links
>- [📔 GOES-R Series Data Book](https://www.goes-r.gov/downloads/resources/documents/GOES-RSeriesDataBook.pdf)
>- [🎠 Beginner's Guide](https://www.goes-r.gov/downloads/resources/documents/Beginners_Guide_to_GOES-R_Series_Data.pdf)
>- [🖥 Rammb Slider GOES Viewer](https://rammb-slider.cira.colostate.edu)
>- [💾 GOES on AWS](https://registry.opendata.aws/noaa-goes/)
>- [🐍 Unidata Plot GOES Data](https://unidata.github.io/python-training/gallery/mapping_goes16_truecolor/)
>- [🗺 Plotting tips form geonetcast blog](https://geonetcast.wordpress.com/2019/08/02/plot-0-5-km-goes-r-full-disk-regions/)
>- [🐍 `glmtools`](https://github.com/deeplycloudy/glmtools/)

---

> ### What if I don't like the goes2go package?
> As an alternative you can use [rclone](https://rclone.org/) to download GOES files from AWS. I quite like rclone. Here is a [short rclone tutorial](https://github.com/blaylockbk/pyBKB_v3/blob/master/rclone_howto.md).

# Download Data
Download GOES 16 ABI (this example downloads the multichannel fixed grid product for CONUS) and read it with xarray.

```python
from goes2go.data import goes_latest, goes_nearesttime

# Get latest data
G1 = goes_latest(satellite='G16', product='ABI')

# Get data for a specific time
G2 = goes_nearesttime(datetime(2020,10,1), satellite='G16', product='GLM')
```

# RGB Recipies
For a GOES ABI multichannel xarray.Dataset, return an RGB array for an RGB product. See [DEMO](./notebooks/DEMO_rgb_recipies.ipynb) for more examples of RGB products.

![](./images/TrueColor.png)


# Field of View

See notebooks for [GLM](./notebooks/field-of-view_GLM.ipynb) and [ABI](./notebooks/field-of-view_ABI.ipynb) field of view.

GOES-West is centered over -137 W and GOES-East is centered over -75 W. When GOES was being tested, it was in a "central" position, outlined in the dashed black line. Below is the ABI field of view for the full disk:
![field of view image](./images/ABI_field-of-view.png)

The GLM field of view is slightly smaller and limited by a bounding box. Below is the GLM field of view:
![field of view image](./images/GLM_field-of-view.png)
