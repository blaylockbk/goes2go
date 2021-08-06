## Brian Blaylock
## August 8, 2019

"""
===========
RGB Recipes
===========

.. image:: /_static/RGB_sample.png

These functions take GOES-East or GOES-West multichannel data on a 
fixed grid (files named ``ABI-L2-MCMIPC``) and generates a 3D 
Red-Green-Blue (RGB) array for various GOES RGB products.

RGB recipes are based on the `GOES Quick Guides
<http://rammb.cira.colostate.edu/training/visit/quick_guides/>`_ 
and include the following:

    - NaturalColor
    - TrueColor
    - FireTemperature
    - AirMass
    - DayCloudPhase
    - DayConvection
    - DayCloudConvection
    - DayLandCloud
    - DayLandCloudFire
    - WaterVapor
    - DifferentialWaterVapor
    - DaySnowFog
    - NighttimeMicrophysics
    - Dust
    - SulfurDioxide
    - Ash
    - SplitWindowDifference
    - NightFogDifference
    - RocketPlume              ✨New - July 9, 2021

The returned RGB can easily be viewed with ``plt.imshow(RGB)``. 

For imshow to show an RGB image, the values must range between 0 and 1. 
Values are normalized between the range specified in the Quick Guides. 
This normalization is synonymous to `contrast or histogram stretching 
<https://micro.magnet.fsu.edu/primer/java/digitalimaging/processing/histogramstretching/index.html>`_
(`more info here
<https://staff.fnwi.uva.nl/r.vandenboomgaard/IPCV20162017/LectureNotes/IP/PointOperators/ImageStretching.html>`_)
and follows the formula:

    .. code-block:: python 

        NormalizedValue = (OriginalValue-LowerLimit)/(UpperLimit-LowerLimit)

`Gamma correction <https://en.wikipedia.org/wiki/Gamma_correction>`_
darkens or lightens an image (`more info 
<https://www.cambridgeincolour.com/tutorials/gamma-correction.htm>`_) 
and follows the decoding formula:

    .. code-block:: python 
        
        R_corrected = R**(1/gamma)

The input for all these functions are denoted by ``C`` for "channels" which
represents the GOES ABI multichannel file opened with xarray. For example:

    .. code-block:: python 
        
        FILE = 'OR_ABI-L2-MCMIPC-M6_G17_s20192201631196_e20192201633575_c20192201634109.nc'
        C = xarray.open_dataset(FILE)

All RGB products are demonstarted in the `make_RGB_Demo 
<https://github.com/blaylockbk/goes2go/tree/master/notebooks>`_ notebook.

Note: I don't have a `GeoColor <https://journals.ametsoc.org/view/journals/atot/37/3/JTECH-D-19-0134.1.xml>`_
RGB, because it is much more involved than simply stacking RGB channels. If anyone does do
something similar to a GeoColor image, let me know!

ABI Band Reference
------------------

https://www.weather.gov/media/crp/GOES_16_Guides_FINALBIS.pdf
http://cimss.ssec.wisc.edu/goes/GOESR_QuickGuides.html
https://www.goes-r.gov/mission/ABI-bands-quick-info.html

=============== ================== ============================================== ======================================
ABI Band Number Central Wavelength  Name                                          Type
=============== ================== ============================================== ======================================
      1             0.47 μm        "Blue" Band                                    Visible
      2             0.64 μm        "Red" Band                                     Visible
      3             0.86 μm        "Veggie" Band                                  Near-IR
      4             1.37 μm        "Cirrus" Band                                  Near-IR
      5             1.6  μm        "Snow/Ice" Band                                Near-IR
      6             2.2  μm        "Cloud Particle Size" Band                     Near-IR
      7             3.9  μm        "Shortwave Window" Band                        IR (with reflected daytime component)
      8             6.2  μm        "Upper-Level Tropospheric Water Vapor" Band    IR
      9             6.9  μm        "Mid-Level Tropospheric Water Vapor" Band      IR
      10            7.3  μm        "Lower-level Water Vapor" Band                 IR
      11            8.4  μm        "Cloud-Top Phase" Band                         IR
      12            9.6  μm        "Ozone Band"                                   IR
      13            10.3 μm        "Clean" IR Longwave Window Band                IR
      14            11.2 μm        IR Longwave Window Band                        IR
      15            12.3 μm        "Dirty" Longwave Window Band                   IR
      16            13.3 μm        "CO2" Longwave infrared                        IR
=============== ================== ============================================== ======================================


"""

import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import xarray as xr

from goes2go.tools import field_of_view


def get_imshow_kwargs(ds):
    """
    Help determine the ``plt.imshow`` arguments.

    Parameters
    ----------
    ds : xarray.Dataset

    Returns
    -------
    kwargs for the ``plt.imshow`` with the correct image extent limits.

    Examples
    --------

    .. code:: python

        r = TrueColor(G)
        ax = common_features(r.crs)
        ax.imshow(r.TrueColor, *\*\get_imshow_kwargs(r))

    """
    return dict(
        extent=[ds.x2.data.min(), ds.x2.data.max(), ds.y2.data.min(), ds.y2.data.max()],
        transform=ds.crs,
        origin="upper",
        interpolation="none",
    )


def rgb_as_dataset(G, RGB, description, latlon=False):
    """
    Assemble a dataset with the RGB array with other data from the file.

    Parameters
    ----------
    G : xarray.Dataset
        GOES ABI data from multispectral channel
    RGB : array
        A 3D array of R, G, and B values at each pixel
    description : str
        A description of what the RGB data represents.
    latlon : bool
        Derive the latitude and longitude of each pixel.

    """
    # Assemble a new xarray.Dataset for the RGB data
    ds = xr.Dataset({description.replace(" ", ""): (["y", "x", "rgb"], RGB)})
    ds.attrs["description"] = description

    # Convert x, y points to latitude/longitude
    _, crs = field_of_view(G)
    sat_h = G.goes_imager_projection.perspective_point_height
    x2 = G.x * sat_h
    y2 = G.y * sat_h
    ds.coords["x2"] = x2
    ds.coords["y2"] = y2

    ds["x2"].attrs["long_name"] = "x sweep in crs units (m); x * sat_height"
    ds["y2"].attrs["long_name"] = "y sweep in crs units (m); y * sat_height"

    ds.attrs["crs"] = crs

    if latlon:
        X, Y = np.meshgrid(x2, y2)
        a = ccrs.PlateCarree().transform_points(crs, X, Y)
        lons, lats, _ = a[:, :, 0], a[:, :, 1], a[:, :, 2]
        ds.coords["longitude"] = (("y", "x"), lons)
        ds.coords["latitude"] = (("y", "x"), lats)

    # Copy some coordinates and attributes of interest from the original data
    for i in ["x", "y", "t", "geospatial_lat_lon_extent"]:
        ds.coords[i] = G[i]
    for i in [
        "orbital_slot",
        "platform_ID",
        "scene_id",
        "spatial_resolution",
        "instrument_type",
        "title",
    ]:
        ds.attrs[i] = G.attrs[i]

    ## Provide some helpers to plot with imshow
    ds.attrs["imshow_kwargs"] = get_imshow_kwargs(ds)

    ## Provide some helpers to plot with imshow and pcolormesh
    ## Not super useful, because pcolormesh doesn't allow nans in x, y dimension
    # pcolormesh_kwargs = dict(
    #    color = RGB.reshape(np.shape(RGB)[0] * np.shape(RGB)[1], np.shape(RGB)[2])
    #    shading='nearest'
    #    )
    # ds.attrs['pcolormesh_kwargs'] = pcolormesh_kwargs

    return ds


def load_RGB_channels(C, channels):
    """
    Return the R, G, and B arrays for the three channels requested. This
    function will convert the data any units in Kelvin to Celsius.

    Parameters
    ----------
    C : xarray.Dataset
        The GOES multi-channel file opened with xarray.
    channels : tuple of size 3
        A tuple of the channel number for each (R, G, B).
        For example ``channel=(2, 3, 1)`` is for the true color RGB

    Returns
    -------
    A list with three items that are used for R, G, and B.
    >>> R, G, B = load_RGB_channels(C, (2,3,1))

    """
    # Units of each channel requested
    units = [C["CMI_C%02d" % c].units for c in channels]
    RGB = []
    for u, c in zip(units, channels):
        if u == "K":
            # Convert form Kelvin to Celsius
            RGB.append(C["CMI_C%02d" % c].data - 273.15)
        else:
            RGB.append(C["CMI_C%02d" % c].data)
    return RGB


def gamma_correction(a, gamma, verbose=False):
    """
    Darken or lighten an image with `gamma correction
    <https://en.wikipedia.org/wiki/Gamma_correction>`_.

    Parameters
    ----------
    a : array-like
        An array of values, typically the RGB array of values in
        an image.
    gamma : float
        Gamma value to decode the image by.
        Values > 1 will lighten an image.
        Values < 1 will darken an image.
    """
    if verbose:
        if gamma > 1:
            print("Gamma Correction: 🌔 Lighten image")
        elif gamma < 1:
            print("Gamma Correction: 🌒 Darken image")
        else:
            print("Gamma Correction: 🌓 Gamma=1. No correction made.")
            return a

    # Gamma decoding formula
    return np.power(a, 1 / gamma)


def normalize(value, lower_limit, upper_limit, clip=True):
    """
    Normalize values between 0 and 1.

    Normalize between a lower and upper limit. In other words, it
    converts your number to a value in the range between 0 and 1.
    Follows `normalization formula
    <https://stats.stackexchange.com/a/70807/220885>`_

    This is the same concept as `contrast or histogram stretching
    <https://staff.fnwi.uva.nl/r.vandenboomgaard/IPCV20162017/LectureNotes/IP/PointOperators/ImageStretching.html>`_


    .. code:: python

        NormalizedValue = (OriginalValue-LowerLimit)/(UpperLimit-LowerLimit)

    Parameters
    ----------
    value :
        The original value. A single value, vector, or array.
    upper_limit :
        The upper limit.
    lower_limit :
        The lower limit.
    clip : bool
        - True: Clips values between 0 and 1 for RGB.
        - False: Retain the numbers that extends outside 0-1 range.
    Output:
        Values normalized between the upper and lower limit.
    """
    norm = (value - lower_limit) / (upper_limit - lower_limit)
    if clip:
        norm = np.clip(norm, 0, 1)
    return norm


# ======================================================================
# ======================================================================


def TrueColor(C, gamma=2.2, pseudoGreen=True, night_IR=True, **kwargs):
    """
    True Color RGB:
    (See `Quick Guide <http://cimss.ssec.wisc.edu/goes/OCLOFactSheetPDFs/ABIQuickGuide_CIMSSRGB_v2.pdf>`__ for reference)

    This is similar to the NaturalColor RGB, but uses a different gamma
    correction and does not apply contrast stretching. I think these
    images look a little "washed out" when compared to the NaturalColor
    RGB. So, I would recommend using the NaturalColor RGB.

    For more details on combing RGB and making the psedo green channel, refer to
    `Bah et al. 2018 <https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2018EA000379>`_.

    .. image:: /_static/TrueColor.png

    .. image:: /_static/gamma_demo_TrueColor.png

    .. image:: /_static/Color-IR_demo.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened with xarray.
    gamma : float
        Darken or lighten an image with `gamma correction
        <https://en.wikipedia.org/wiki/Gamma_correction>`_.
        Values > 1 will lighten an image.
        Values < 1 will darken an image.
    pseudoGreen : bool
        True: returns the calculated "True" green color
        False: returns the "veggie" channel
    night_IR : bool
        If True, use Clean IR (channel 13) as maximum RGB value overlay
        so that cold clouds show up at night. (Be aware that some
        daytime clouds might appear brighter).
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables
    R, G, B = load_RGB_channels(C, (2, 3, 1))

    # Apply range limits for each channel. RGB values must be between 0 and 1
    R = np.clip(R, 0, 1)
    G = np.clip(G, 0, 1)
    B = np.clip(B, 0, 1)

    # Apply a gamma correction to each R, G, B channel
    R = gamma_correction(R, gamma)
    G = gamma_correction(G, gamma)
    B = gamma_correction(B, gamma)

    if pseudoGreen:
        # Calculate the "True" Green
        G = 0.45 * R + 0.1 * G + 0.45 * B
        G = np.clip(G, 0, 1)

    if night_IR:
        # Load the Clean IR channel
        IR = C["CMI_C13"]
        # Normalize between a range and clip
        IR = normalize(IR, 90, 313, clip=True)
        # Invert colors so cold clouds are white
        IR = 1 - IR
        # Lessen the brightness of the coldest clouds so they don't
        # appear so bright when we overlay it on the true color image
        IR = IR / 1.4
        # RGB with IR as greyscale
        RGB = np.dstack([np.maximum(R, IR), np.maximum(G, IR), np.maximum(B, IR)])
    else:
        RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "True Color", **kwargs)


def NaturalColor(C, gamma=0.8, pseudoGreen=True, night_IR=False, **kwargs):
    """
    Natural Color RGB based on CIMSS method. Thanks Rick Kohrs!
    (See `Quick Guide <http://cimss.ssec.wisc.edu/goes/OCLOFactSheetPDFs/ABIQuickGuide_CIMSSRGB_v2.pdf>`__ for reference)

    Check out Rick Kohrs `merged GOES images <https://www.ssec.wisc.edu/~rickk/local-noon.html>`_.

    This NaturalColor RGB is *very* similar to the TrueColor RGB but
    uses slightly different contrast stretches and ranges.

    For more details on combing RGB and making the psedo green channel, refer to
    `Bah et al. 2018 <https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2018EA000379>`_.

    .. image:: /_static/NaturalColor.png

    .. image:: /_static/gamma_demo_NaturalColor-PsuedoGreen.png

    .. image:: /_static/gamma_demo_NaturalColor-VeggieGreen.png

    .. image:: /_static/Color-IR_demo.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened ith xarray.
    gamma : float
        Darken or lighten an image with `gamma correction
        <https://en.wikipedia.org/wiki/Gamma_correction>`_.
        Values > 1 will lighten an image.
        Values < 1 will darken an image.
    night_IR : bool
        If True, use Clean IR (channel 13) as maximum RGB value overlay
        so that cold clouds show up at night. (Be aware that some
        daytime clouds might appear brighter).
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel
    """

    def breakpoint_stretch(C, breakpoint):
        """
        Contrast stretching by break point (number provided by Rick Kohrs)
        """
        lower = normalize(C, 0, 10)  # Low end
        upper = normalize(C, 10, 255)  # High end

        # Combine the two datasets
        # This works because if upper=1 and lower==.7, then
        # that means the upper value was out of range and the
        # value for the lower pass was used instead.
        combined = np.minimum(lower, upper)

        return combined

    # Load the three channels into appropriate R, G, and B variables
    R, G, B = load_RGB_channels(C, (2, 3, 1))

    # Apply range limits for each channel. RGB values must be between 0 and 1
    R = np.clip(R, 0, 1)
    G = np.clip(G, 0, 1)
    B = np.clip(B, 0, 1)

    if pseudoGreen:
        # Derive pseudo Green channel
        G = 0.45 * R + 0.1 * G + 0.45 * B
        G = np.clip(G, 0, 1)

    # Convert Albedo to Brightness, ranging from 0-255 K
    # (numbers based on email from Rick Kohrs)
    R = np.sqrt(R * 100) * 25.5
    G = np.sqrt(G * 100) * 25.5
    B = np.sqrt(B * 100) * 25.5

    # Apply contrast stretching based on breakpoints
    # (numbers based on email form Rick Kohrs)
    R = breakpoint_stretch(R, 33)
    G = breakpoint_stretch(G, 40)
    B = breakpoint_stretch(B, 50)

    if night_IR:
        # Load the Clean IR channel
        IR = C["CMI_C13"]
        # Normalize between a range and clip
        IR = normalize(IR, 90, 313, clip=True)
        # Invert colors so cold clouds are white
        IR = 1 - IR
        # Lessen the brightness of the coldest clouds so they don't
        # appear so bright when we overlay it on the true color image
        IR = IR / 1.4
        # Overlay IR channel, as greyscale image (use IR in R, G, and B)
        RGB = np.dstack([np.maximum(R, IR), np.maximum(G, IR), np.maximum(B, IR)])
    else:
        RGB = np.dstack([R, G, B])

    # Apply a gamma correction to the image
    RGB = gamma_correction(RGB, gamma)

    return rgb_as_dataset(C, RGB, "Natural Color", **kwargs)


def FireTemperature(C, **kwargs):
    """
    Fire Temperature RGB:
    (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/Fire_Temperature_RGB.pdf>`__ for reference)

    .. image:: /_static/FireTemperature.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened with xarray.
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables
    R, G, B = load_RGB_channels(C, (7, 6, 5))

    # Normalize each channel by the appropriate range of values (clipping happens in function)
    R = normalize(R, 273, 333)
    G = normalize(G, 0, 1)
    B = normalize(B, 0, 0.75)

    # Apply the gamma correction to Red channel.
    #   corrected_value = value^(1/gamma)
    gamma = 0.4
    R = gamma_correction(R, gamma)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Fire Temperature", **kwargs)


def AirMass(C, **kwargs):
    """
    Air Mass RGB:
    (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_AirMassRGB_final.pdf>`__ for reference)

    .. image:: /_static/AirMass.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened with xarray.
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables
    R = C["CMI_C08"].data - C["CMI_C10"].data
    G = C["CMI_C12"].data - C["CMI_C13"].data
    B = C["CMI_C08"].data - 273.15  # remember to convert to Celsius

    # Normalize each channel by the appropriate range of values. e.g. R = (R-minimum)/(maximum-minimum)
    R = normalize(R, -26.2, 0.6)
    G = normalize(G, -42.2, 6.7)
    B = normalize(B, -64.65, -29.25)

    # Invert B
    B = 1 - B

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Air Mass", **kwargs)


def DayCloudPhase(C, **kwargs):
    """
    Day Cloud Phase Distinction RGB:
    (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/Day_Cloud_Phase_Distinction.pdf>`__ for reference)

    .. image:: /_static/DayCloudPhase.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened with xarray.
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables
    R, G, B = load_RGB_channels(C, (13, 2, 5))

    # Normalize each channel by the appropriate range of values. (Clipping happens inside function)
    R = normalize(R, -53.5, 7.5)
    G = normalize(G, 0, 0.78)
    B = normalize(B, 0.01, 0.59)

    # Invert R
    R = 1 - R

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Day Cloud Phase", **kwargs)


def DayConvection(C, **kwargs):
    """
    Day Convection RGB:
    (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_DayConvectionRGB_final.pdf>`__ for reference)

    .. image:: /_static/DayConvection.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened with xarray.
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables
    # NOTE: Each R, G, B is a channel difference.
    R = C["CMI_C08"].data - C["CMI_C10"].data
    G = C["CMI_C07"].data - C["CMI_C13"].data
    B = C["CMI_C05"].data - C["CMI_C02"].data

    # Normalize each channel by the appropriate range of values.
    R = normalize(R, -35, 5)
    G = normalize(G, -5, 60)
    B = normalize(B, -0.75, 0.25)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Day Convection", **kwargs)


def DayCloudConvection(C, **kwargs):
    """
    Day Cloud Convection RGB:
    (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_DayCloudConvectionRGB_final.pdf>`__ for reference)

    .. image:: /_static/DayCloudConvection.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened with xarray.
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables
    R, G, B = load_RGB_channels(C, (2, 2, 13))

    # Normalize each channel by the appropriate range of values.
    R = normalize(R, 0, 1)
    G = normalize(G, 0, 1)
    B = normalize(B, -70.15, 49.85)

    # Invert B
    B = 1 - B

    # Apply the gamma correction to Red channel.
    #   corrected_value = value^(1/gamma)
    gamma = 1.7
    R = gamma_correction(R, gamma)
    G = gamma_correction(G, gamma)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Day Cloud Convection", **kwargs)


def DayLandCloud(C, **kwargs):
    """
    Day Land Cloud Fire RGB:
    (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_daylandcloudRGB_final.pdf>`__ for reference)

    .. image:: /_static/DayLandCloud.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened with xarray.
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables
    R, G, B = load_RGB_channels(C, (5, 3, 2))

    # Normalize each channel by the appropriate range of values  e.g. R = (R-minimum)/(maximum-minimum)
    R = normalize(R, 0, 0.975)
    G = normalize(G, 0, 1.086)
    B = normalize(B, 0, 1)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Day Land Cloud", **kwargs)


def DayLandCloudFire(C, **kwargs):
    """
    Day Land Cloud Fire RGB:
    (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_DayLandCloudFireRGB_final.pdf>`__ for reference)

    .. image:: /_static/DayLandCloudFire.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened with xarray.
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables
    R, G, B = load_RGB_channels(C, (6, 3, 2))

    # Normalize each channel by the appropriate range of values  e.g. R = (R-minimum)/(maximum-minimum)
    R = normalize(R, 0, 1)
    G = normalize(G, 0, 1)
    B = normalize(B, 0, 1)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Day Land Cloud Fire", **kwargs)


def WaterVapor(C, **kwargs):
    """
    Simple Water Vapor RGB:
    (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/Simple_Water_Vapor_RGB.pdf>`__ for reference)

    .. image:: /_static/WaterVapor.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened with xarray.
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables.
    R, G, B = load_RGB_channels(C, (13, 8, 10))

    # Normalize each channel by the appropriate range of values. e.g. R = (R-minimum)/(maximum-minimum)
    R = normalize(R, -70.86, 5.81)
    G = normalize(G, -58.49, -30.48)
    B = normalize(B, -28.03, -12.12)

    # Invert the colors
    R = 1 - R
    G = 1 - G
    B = 1 - B

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Water Vapor", **kwargs)


def DifferentialWaterVapor(C, **kwargs):
    """
    Differential Water Vapor RGB:
    (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_DifferentialWaterVaporRGB_final.pdf>`__ for reference)

    .. image:: /_static/DifferentialWaterVapor.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened with xarray.
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables.
    R = C["CMI_C10"].data - C["CMI_C08"].data
    G = C["CMI_C10"].data - 273.15
    B = C["CMI_C08"].data - 273.15

    # Normalize each channel by the appropriate range of values. e.g. R = (R-minimum)/(maximum-minimum)
    R = normalize(R, -3, 30)
    G = normalize(G, -60, 5)
    B = normalize(B, -64.65, -29.25)

    # Gamma correction
    R = gamma_correction(R, 0.2587)
    G = gamma_correction(G, 0.4)
    B = gamma_correction(B, 0.4)

    # Invert the colors
    R = 1 - R
    G = 1 - G
    B = 1 - B

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Differenctial Water Vapor", **kwargs)


def DaySnowFog(C, **kwargs):
    """
    Day Snow-Fog RGB:
    (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_DaySnowFog.pdf>`__ for reference)

    .. image:: /_static/DaySnowFog.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened with xarray.
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables
    R = C["CMI_C03"].data
    G = C["CMI_C05"].data
    B = C["CMI_C07"].data - C["CMI_C13"].data

    # Normalize values
    R = normalize(R, 0, 1)
    G = normalize(G, 0, 0.7)
    B = normalize(B, 0, 30)

    # Apply a gamma correction to the image
    gamma = 1.7
    R = gamma_correction(R, gamma)
    G = gamma_correction(G, gamma)
    B = gamma_correction(B, gamma)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Day Snow Fog", **kwargs)


def NighttimeMicrophysics(C, **kwargs):
    """
    Nighttime Microphysics RGB:
    (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_NtMicroRGB_final.pdf>`__ for reference)

    .. image:: /_static/NighttimeMicrophysics.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened with xarray.
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables
    R = C["CMI_C15"].data - C["CMI_C13"].data
    G = C["CMI_C13"].data - C["CMI_C07"].data
    B = C["CMI_C13"].data - 273.15

    # Normalize values
    R = normalize(R, -6.7, 2.6)
    G = normalize(G, -3.1, 5.2)
    B = normalize(B, -29.6, 19.5)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Nighttime Microphysics", **kwargs)


def Dust(C, **kwargs):
    """
    SulfurDioxide RGB:
    (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/Dust_RGB_Quick_Guide.pdf>`__ for reference)

    .. image:: /_static/Dust.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened with xarray.
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables
    R = C["CMI_C15"].data - C["CMI_C13"].data
    G = C["CMI_C14"].data - C["CMI_C11"].data
    B = C["CMI_C13"].data - 273.15

    # Normalize values
    R = normalize(R, -6.7, 2.6)
    G = normalize(G, -0.5, 20)
    B = normalize(B, -11.95, 15.55)

    # Apply a gamma correction to the image
    gamma = 2.5
    G = gamma_correction(G, gamma)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Dust", **kwargs)


def SulfurDioxide(C, **kwargs):
    """
    SulfurDioxide RGB:
    (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/Quick_Guide_SO2_RGB.pdf>`__ for reference)

    .. image:: /_static/SulfurDioxide.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened with xarray.
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables
    R = C["CMI_C09"].data - C["CMI_C10"].data
    G = C["CMI_C13"].data - C["CMI_C11"].data
    B = C["CMI_C07"].data - 273.15

    # Normalize values
    R = normalize(R, -4, 2)
    G = normalize(G, -4, 5)
    B = normalize(B, -30.1, 29.8)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Sulfur Dioxide", **kwargs)


def Ash(C, **kwargs):
    """
    Ash RGB:
    (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/GOES_Ash_RGB.pdf>`__ for reference)

    .. image:: /_static/Ash.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened with xarray.
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables
    R = C["CMI_C15"].data - C["CMI_C13"].data
    G = C["CMI_C14"].data - C["CMI_C11"].data
    B = C["CMI_C13"].data - 273.15

    # Normalize values
    R = normalize(R, -6.7, 2.6)
    G = normalize(G, -6, 6.3)
    B = normalize(B, -29.55, 29.25)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Ash", **kwargs)


def SplitWindowDifference(C, **kwargs):
    """
    Split Window Difference RGB (greyscale):
    (See `Quick Guide <http://cimss.ssec.wisc.edu/goes/OCLOFactSheetPDFs/ABIQuickGuide_SplitWindowDifference.pdf>`__ for reference)

    .. image:: /_static/SplitWindowDifference.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened with xarray.
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables
    data = C["CMI_C15"].data - C["CMI_C13"].data

    # Normalize values
    data = normalize(data, -10, 10)

    # The final RGB array :)
    RGB = np.dstack([data, data, data])

    return rgb_as_dataset(C, RGB, "Split Window Difference", **kwargs)


def NightFogDifference(C, **kwargs):
    """
    Night Fog Difference RGB (greyscale):
    (See `Quick Guide <http://cimss.ssec.wisc.edu/goes/OCLOFactSheetPDFs/ABIQuickGuide_NightFogBTD.pdf>`__ for reference)

    .. image:: /_static/NightFogDifference.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened with xarray.
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables
    data = C["CMI_C13"].data - C["CMI_C07"].data

    # Normalize values
    data = normalize(data, -90, 15)

    # Invert data
    data = 1 - data

    # The final RGB array :)
    RGB = np.dstack([data, data, data])

    return rgb_as_dataset(C, RGB, "Night Fog Difference", **kwargs)


def RocketPlume(C, night=False, **kwargs):
    """
    Rocket Plume RGB

    For identifying rocket launches.

    See `this blog <https://cimss.ssec.wisc.edu/satellite-blog/archives/41335>`__ and
    the `Quick Guide <https://cimss.ssec.wisc.edu/satellite-blog/images/2021/06/QuickGuide_Template_GOESRBanner_Rocket_Plume.pdf>`__
    for reference

    .. image:: /_static/RocketPlume.png

    Parameters
    ----------
    C : xarray.Dataset
        A GOES ABI multichannel file opened with xarray.
    night : bool
        If the area is in night, turn this on to use a different channel
        than the daytime application.
    \*\*kwargs :
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables
    R = C["CMI_C07"].data
    G = C["CMI_C08"].data
    if not night:
        B = C["CMI_C02"].data
    else:
        B = C["CMI_C05"].data

    # Normalize values
    R = normalize(R, 273, 338)
    G = normalize(G, 233, 253)
    B = normalize(B, 0, 0.80)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "RocketPlume", **kwargs)


#######################
# 🚧 Construction Zone
#######################
def NormalizedBurnRatio(C, **kwargs):
    """
    Normalized Burn Ratio

    **THIS FUNCTION IS NOT FULLY DEVELOPED. Need more info.**

    NBR= (0.86 µm – 2.2 µm)/(0.86 um + 2.2 um)


    https://ntrs.nasa.gov/citations/20190030825

    Parameters
    ----------

    """
    # Load the three channels into appropriate R, G, and B variables
    C3 = C["CMI_C03"].data
    C6 = C["CMI_C06"].data
    data = (C3 - C6) / (C3 + C6)

    # Invert data
    # data = 1-data

    # The final RGB array :)
    RGB = np.dstack([data, data, data])

    return rgb_as_dataset(C, RGB, "Normalized Burn Ratio", **kwargs)


if __name__ == "__main__":

    # Create images of each for Docs
    print("nothing here for now")
