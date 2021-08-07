## Brian Blaylock
## July 9, 2021

"""
===========
RGB Recipes
===========

RGB Recipes for the GOES Advanced Baseline Imager.

"""

import xarray as xr
import numpy as np
import cartopy.crs as ccrs

from goes2go.tools import field_of_view

########################
# Image Processing Tools
def _gamma_correction(a, gamma, verbose=False):
    """
    Darken or lighten an image with `gamma correction
    <https://en.wikipedia.org/wiki/_gamma_correction>`_.

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


def _normalize(value, lower_limit, upper_limit, clip=True):
    """
    Normalize values between 0 and 1.

    Normalize between a lower and upper limit. In other words, it
    converts your number to a value in the range between 0 and 1.
    Follows `normalization formula
    <https://stats.stackexchange.com/a/70807/220885>`_

    This is the same concept as `contrast or histogram stretching
    <https://staff.fnwi.uva.nl/r.vandenboomgaard/IPCV20162017/LectureNotes/IP/PointOperators/ImageStretching.html>`_


    .. code:: python

        _normalizedValue = (OriginalValue-LowerLimit)/(UpperLimit-LowerLimit)

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
        Values _normalized between the upper and lower limit.
    """
    norm = (value - lower_limit) / (upper_limit - lower_limit)
    if clip:
        norm = np.clip(norm, 0, 1)
    return norm


##############
# RGB Accessor


@xr.register_dataset_accessor("rgb")
class rgbAccessor:
    def __init__(self, xarray_obj):
        self._obj = xarray_obj
        self._center = None
        self._sat_h = self._obj.goes_imager_projection.perspective_point_height
        self._x = None
        self._y = None
        self._crs = None
        self._imshow_kwargs = None

    @property
    def center(self):
        """Return the geographic center point of this dataset."""
        if self._center is None:
            # we can use a cache on our accessor objects, because accessors
            # themselves are cached on instances that access them.
            lon = self._obj.x
            lat = self._obj.y
            self._center = (float(lon.mean()), float(lat.mean()))
        return self._center

    @property
    def crs(self):
        if self._crs is None:
            ds = self._obj
            # Convert x, y points to latitude/longitude
            _, crs = field_of_view(ds)
            self._crs = crs
        return self._crs

    @property
    def get_x(self):
        """x sweep in crs units (m); x * sat_height"""
        if self._x is None:
            self._x = self._obj.x * sat_h
        return self._x

    @property
    def get_y(self):
        """x sweep in crs units (m); x * sat_height"""
        if self._y is None:
            self._y = self._obj.y * sat_h
        return self._y

    @property
    def get_imshow_kwargs(self):
        if self._imshow_kwargs is None:
            self._imshow_kwargs = dict(
                extent=[
                    self._x.data.min(),
                    self._x.data.max(),
                    self._y.data.min(),
                    self._y.data.max(),
                ],
                transform=self._crs,
                origin="upper",
                interpolation="none",
            )
        return self._imshow_kwargs

    def get_latlon(self):
        """Get lat/lon of all points"""
        X, Y = np.meshgrid(self._x, self._y)
        a = ccrs.PlateCarree().transform_points(self._crs, X, Y)
        lons, lats, _ = a[:, :, 0], a[:, :, 1], a[:, :, 2]

        self._obj.coords["longitude"] = (("y", "x"), lons)
        self._obj.coords["latitude"] = (("y", "x"), lats)

    ####################################################################
    # Helpers
    def _load_RGB_channels(self, channels):
        """
        Return the R, G, and B arrays for the three channels requested. This
        function will convert the data any units in Kelvin to Celsius.

        Parameters
        ----------
        channels : tuple of size 3
            A tuple of the channel number for each (R, G, B).
            For example ``channel=(2, 3, 1)`` is for the true color RGB

        Returns
        -------
        A list with three items that are used for R, G, and B.
        >>> R, G, B = _load_RGB_channels((2,3,1))

        """
        ds = self._obj

        # Units of each channel requested
        units = [ds["CMI_C%02d" % c].units for c in channels]
        RGB = []
        for u, c in zip(units, channels):
            if u == "K":
                # Convert form Kelvin to Celsius                                ## <-- Do I REALLY want to hard-code this in?
                RGB.append(ds["CMI_C%02d" % c].data - 273.15)
            else:
                RGB.append(ds["CMI_C%02d" % c].data)
        return RGB

    ####################################################################
    # RGB Recipes
    def TrueColor(self, gamma=2.2, pseudoGreen=True, night_IR=True, **kwargs):
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
        gamma : float
            Darken or lighten an image with `gamma correction
            <https://en.wikipedia.org/wiki/_gamma_correction>`_.
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
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R, G, B = self._load_RGB_channels((2, 3, 1))

        # Apply range limits for each channel. RGB values must be between 0 and 1
        R = np.clip(R, 0, 1)
        G = np.clip(G, 0, 1)
        B = np.clip(B, 0, 1)

        # Apply a gamma correction to each R, G, B channel
        R = _gamma_correction(R, gamma)
        G = _gamma_correction(G, gamma)
        B = _gamma_correction(B, gamma)

        if pseudoGreen:
            # Calculate the "True" Green
            G = 0.45 * R + 0.1 * G + 0.45 * B
            G = np.clip(G, 0, 1)

        if night_IR:
            # Load the Clean IR channel
            IR = ds["CMI_C13"]
            # _normalize between a range and clip
            IR = _normalize(IR, 90, 313, clip=True)
            # Invert colors so cold clouds are white
            IR = 1 - IR
            # Lessen the brightness of the coldest clouds so they don't
            # appear so bright when we overlay it on the true color image
            IR = IR / 1.4
            # RGB with IR as greyscale
            RGB = np.dstack([np.maximum(R, IR), np.maximum(G, IR), np.maximum(B, IR)])
        else:
            RGB = np.dstack([R, G, B])

        ds["TrueColor"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["TrueColor"].attrs[
            "Quick Guide"
        ] = "http://cimss.ssec.wisc.edu/goes/OCLOFactSheetPDFs/ABIQuickGuide_CIMSSRGB_v2.pdf"
        ds["TrueColor"].attrs["long_name"] = "True Color"

    def NaturalColor(self, gamma=0.8, pseudoGreen=True, night_IR=False, **kwargs):
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
            <https://en.wikipedia.org/wiki/_gamma_correction>`_.
            Values > 1 will lighten an image.
            Values < 1 will darken an image.
        night_IR : bool
            If True, use Clean IR (channel 13) as maximum RGB value overlay
            so that cold clouds show up at night. (Be aware that some
            daytime clouds might appear brighter).
        \*\*kwargs :
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel
        """
        ds = self._obj

        def breakpoint_stretch(C, breakpoint):
            """
            Contrast stretching by break point (number provided by Rick Kohrs)
            """
            lower = _normalize(C, 0, 10)  # Low end
            upper = _normalize(C, 10, 255)  # High end

            # Combine the two datasets
            # This works because if upper=1 and lower==.7, then
            # that means the upper value was out of range and the
            # value for the lower pass was used instead.
            combined = np.minimum(lower, upper)

            return combined

        # Load the three channels into appropriate R, G, and B variables
        R, G, B = _load_RGB_channels(C, (2, 3, 1))

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
            # _normalize between a range and clip
            IR = _normalize(IR, 90, 313, clip=True)
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
        RGB = _gamma_correction(RGB, gamma)

        return _rgb_as_dataset(C, RGB, "Natural Color", **kwargs)

    def FireTemperature(self, **kwargs):
        """
        Fire Temperature RGB:
        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/Fire_Temperature_RGB.pdf>`__ for reference)

        .. image:: /_static/FireTemperature.png

        Parameters
        ----------
        C : xarray.Dataset
            A GOES ABI multichannel file opened with xarray.
        \*\*kwargs :
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R, G, B = _load_RGB_channels(C, (7, 6, 5))

        # _normalize each channel by the appropriate range of values (clipping happens in function)
        R = _normalize(R, 273, 333)
        G = _normalize(G, 0, 1)
        B = _normalize(B, 0, 0.75)

        # Apply the gamma correction to Red channel.
        #   corrected_value = value^(1/gamma)
        gamma = 0.4
        R = _gamma_correction(R, gamma)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        return _rgb_as_dataset(C, RGB, "Fire Temperature", **kwargs)

    def AirMass(self, **kwargs):
        """
        Air Mass RGB:
        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_AirMassRGB_final.pdf>`__ for reference)

        .. image:: /_static/AirMass.png

        Parameters
        ----------
        C : xarray.Dataset
            A GOES ABI multichannel file opened with xarray.
        \*\*kwargs :
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R = C["CMI_C08"].data - C["CMI_C10"].data
        G = C["CMI_C12"].data - C["CMI_C13"].data
        B = C["CMI_C08"].data - 273.15  # remember to convert to Celsius

        # _normalize each channel by the appropriate range of values. e.g. R = (R-minimum)/(maximum-minimum)
        R = _normalize(R, -26.2, 0.6)
        G = _normalize(G, -42.2, 6.7)
        B = _normalize(B, -64.65, -29.25)

        # Invert B
        B = 1 - B

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        return _rgb_as_dataset(C, RGB, "Air Mass", **kwargs)

    def DayCloudPhase(self, **kwargs):
        """
        Day Cloud Phase Distinction RGB:
        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/Day_Cloud_Phase_Distinction.pdf>`__ for reference)

        .. image:: /_static/DayCloudPhase.png

        Parameters
        ----------
        C : xarray.Dataset
            A GOES ABI multichannel file opened with xarray.
        \*\*kwargs :
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R, G, B = _load_RGB_channels(C, (13, 2, 5))

        # _normalize each channel by the appropriate range of values. (Clipping happens inside function)
        R = _normalize(R, -53.5, 7.5)
        G = _normalize(G, 0, 0.78)
        B = _normalize(B, 0.01, 0.59)

        # Invert R
        R = 1 - R

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        return _rgb_as_dataset(C, RGB, "Day Cloud Phase", **kwargs)

    def DayConvection(self, **kwargs):
        """
        Day Convection RGB:
        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_DayConvectionRGB_final.pdf>`__ for reference)

        .. image:: /_static/DayConvection.png

        Parameters
        ----------
        C : xarray.Dataset
            A GOES ABI multichannel file opened with xarray.
        \*\*kwargs :
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        # NOTE: Each R, G, B is a channel difference.
        R = C["CMI_C08"].data - C["CMI_C10"].data
        G = C["CMI_C07"].data - C["CMI_C13"].data
        B = C["CMI_C05"].data - C["CMI_C02"].data

        # _normalize each channel by the appropriate range of values.
        R = _normalize(R, -35, 5)
        G = _normalize(G, -5, 60)
        B = _normalize(B, -0.75, 0.25)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        return _rgb_as_dataset(C, RGB, "Day Convection", **kwargs)

    def DayCloudConvection(self, **kwargs):
        """
        Day Cloud Convection RGB:
        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_DayCloudConvectionRGB_final.pdf>`__ for reference)

        .. image:: /_static/DayCloudConvection.png

        Parameters
        ----------
        C : xarray.Dataset
            A GOES ABI multichannel file opened with xarray.
        \*\*kwargs :
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R, G, B = _load_RGB_channels(C, (2, 2, 13))

        # _normalize each channel by the appropriate range of values.
        R = _normalize(R, 0, 1)
        G = _normalize(G, 0, 1)
        B = _normalize(B, -70.15, 49.85)

        # Invert B
        B = 1 - B

        # Apply the gamma correction to Red channel.
        #   corrected_value = value^(1/gamma)
        gamma = 1.7
        R = _gamma_correction(R, gamma)
        G = _gamma_correction(G, gamma)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        return _rgb_as_dataset(C, RGB, "Day Cloud Convection", **kwargs)

    def DayLandCloud(self, **kwargs):
        """
        Day Land Cloud Fire RGB:
        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_daylandcloudRGB_final.pdf>`__ for reference)

        .. image:: /_static/DayLandCloud.png

        Parameters
        ----------
        C : xarray.Dataset
            A GOES ABI multichannel file opened with xarray.
        \*\*kwargs :
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R, G, B = _load_RGB_channels(C, (5, 3, 2))

        # _normalize each channel by the appropriate range of values  e.g. R = (R-minimum)/(maximum-minimum)
        R = _normalize(R, 0, 0.975)
        G = _normalize(G, 0, 1.086)
        B = _normalize(B, 0, 1)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        return _rgb_as_dataset(C, RGB, "Day Land Cloud", **kwargs)

    def DayLandCloudFire(self, **kwargs):
        """
        Day Land Cloud Fire RGB:
        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_DayLandCloudFireRGB_final.pdf>`__ for reference)

        .. image:: /_static/DayLandCloudFire.png

        Parameters
        ----------
        C : xarray.Dataset
            A GOES ABI multichannel file opened with xarray.
        \*\*kwargs :
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R, G, B = _load_RGB_channels(C, (6, 3, 2))

        # _normalize each channel by the appropriate range of values  e.g. R = (R-minimum)/(maximum-minimum)
        R = _normalize(R, 0, 1)
        G = _normalize(G, 0, 1)
        B = _normalize(B, 0, 1)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        return _rgb_as_dataset(C, RGB, "Day Land Cloud Fire", **kwargs)

    def WaterVapor(self, **kwargs):
        """
        Simple Water Vapor RGB:
        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/Simple_Water_Vapor_RGB.pdf>`__ for reference)

        .. image:: /_static/WaterVapor.png

        Parameters
        ----------
        C : xarray.Dataset
            A GOES ABI multichannel file opened with xarray.
        \*\*kwargs :
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables.
        R, G, B = _load_RGB_channels(C, (13, 8, 10))

        # _normalize each channel by the appropriate range of values. e.g. R = (R-minimum)/(maximum-minimum)
        R = _normalize(R, -70.86, 5.81)
        G = _normalize(G, -58.49, -30.48)
        B = _normalize(B, -28.03, -12.12)

        # Invert the colors
        R = 1 - R
        G = 1 - G
        B = 1 - B

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        return _rgb_as_dataset(C, RGB, "Water Vapor", **kwargs)

    def DifferentialWaterVapor(self, **kwargs):
        """
        Differential Water Vapor RGB:
        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_DifferentialWaterVaporRGB_final.pdf>`__ for reference)

        .. image:: /_static/DifferentialWaterVapor.png

        Parameters
        ----------
        C : xarray.Dataset
            A GOES ABI multichannel file opened with xarray.
        \*\*kwargs :
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables.
        R = C["CMI_C10"].data - C["CMI_C08"].data
        G = C["CMI_C10"].data - 273.15
        B = C["CMI_C08"].data - 273.15

        # _normalize each channel by the appropriate range of values. e.g. R = (R-minimum)/(maximum-minimum)
        R = _normalize(R, -3, 30)
        G = _normalize(G, -60, 5)
        B = _normalize(B, -64.65, -29.25)

        # Gamma correction
        R = _gamma_correction(R, 0.2587)
        G = _gamma_correction(G, 0.4)
        B = _gamma_correction(B, 0.4)

        # Invert the colors
        R = 1 - R
        G = 1 - G
        B = 1 - B

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        return _rgb_as_dataset(C, RGB, "Differenctial Water Vapor", **kwargs)

    def DaySnowFog(self, **kwargs):
        """
        Day Snow-Fog RGB:
        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_DaySnowFog.pdf>`__ for reference)

        .. image:: /_static/DaySnowFog.png

        Parameters
        ----------
        C : xarray.Dataset
            A GOES ABI multichannel file opened with xarray.
        \*\*kwargs :
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R = C["CMI_C03"].data
        G = C["CMI_C05"].data
        B = C["CMI_C07"].data - C["CMI_C13"].data

        # _normalize values
        R = _normalize(R, 0, 1)
        G = _normalize(G, 0, 0.7)
        B = _normalize(B, 0, 30)

        # Apply a gamma correction to the image
        gamma = 1.7
        R = _gamma_correction(R, gamma)
        G = _gamma_correction(G, gamma)
        B = _gamma_correction(B, gamma)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        return _rgb_as_dataset(C, RGB, "Day Snow Fog", **kwargs)

    def NighttimeMicrophysics(self, **kwargs):
        """
        Nighttime Microphysics RGB:
        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_NtMicroRGB_final.pdf>`__ for reference)

        .. image:: /_static/NighttimeMicrophysics.png

        Parameters
        ----------
        C : xarray.Dataset
            A GOES ABI multichannel file opened with xarray.
        \*\*kwargs :
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R = C["CMI_C15"].data - C["CMI_C13"].data
        G = C["CMI_C13"].data - C["CMI_C07"].data
        B = C["CMI_C13"].data - 273.15

        # _normalize values
        R = _normalize(R, -6.7, 2.6)
        G = _normalize(G, -3.1, 5.2)
        B = _normalize(B, -29.6, 19.5)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        return _rgb_as_dataset(C, RGB, "Nighttime Microphysics", **kwargs)

    def Dust(self, **kwargs):
        """
        SulfurDioxide RGB:
        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/Dust_RGB_Quick_Guide.pdf>`__ for reference)

        .. image:: /_static/Dust.png

        Parameters
        ----------
        C : xarray.Dataset
            A GOES ABI multichannel file opened with xarray.
        \*\*kwargs :
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R = C["CMI_C15"].data - C["CMI_C13"].data
        G = C["CMI_C14"].data - C["CMI_C11"].data
        B = C["CMI_C13"].data - 273.15

        # _normalize values
        R = _normalize(R, -6.7, 2.6)
        G = _normalize(G, -0.5, 20)
        B = _normalize(B, -11.95, 15.55)

        # Apply a gamma correction to the image
        gamma = 2.5
        G = _gamma_correction(G, gamma)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        return _rgb_as_dataset(C, RGB, "Dust", **kwargs)

    def SulfurDioxide(self, **kwargs):
        """
        SulfurDioxide RGB:
        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/Quick_Guide_SO2_RGB.pdf>`__ for reference)

        .. image:: /_static/SulfurDioxide.png

        Parameters
        ----------
        C : xarray.Dataset
            A GOES ABI multichannel file opened with xarray.
        \*\*kwargs :
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R = C["CMI_C09"].data - C["CMI_C10"].data
        G = C["CMI_C13"].data - C["CMI_C11"].data
        B = C["CMI_C07"].data - 273.15

        # _normalize values
        R = _normalize(R, -4, 2)
        G = _normalize(G, -4, 5)
        B = _normalize(B, -30.1, 29.8)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        return _rgb_as_dataset(C, RGB, "Sulfur Dioxide", **kwargs)

    def Ash(self, **kwargs):
        """
        Ash RGB:
        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/GOES_Ash_RGB.pdf>`__ for reference)

        .. image:: /_static/Ash.png

        Parameters
        ----------
        C : xarray.Dataset
            A GOES ABI multichannel file opened with xarray.
        \*\*kwargs :
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R = C["CMI_C15"].data - C["CMI_C13"].data
        G = C["CMI_C14"].data - C["CMI_C11"].data
        B = C["CMI_C13"].data - 273.15

        # _normalize values
        R = _normalize(R, -6.7, 2.6)
        G = _normalize(G, -6, 6.3)
        B = _normalize(B, -29.55, 29.25)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        return _rgb_as_dataset(C, RGB, "Ash", **kwargs)

    def SplitWindowDifference(self, **kwargs):
        """
        Split Window Difference RGB (greyscale):
        (See `Quick Guide <http://cimss.ssec.wisc.edu/goes/OCLOFactSheetPDFs/ABIQuickGuide_SplitWindowDifference.pdf>`__ for reference)

        .. image:: /_static/SplitWindowDifference.png

        Parameters
        ----------
        C : xarray.Dataset
            A GOES ABI multichannel file opened with xarray.
        \*\*kwargs :
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        data = C["CMI_C15"].data - C["CMI_C13"].data

        # _normalize values
        data = _normalize(data, -10, 10)

        # The final RGB array :)
        RGB = np.dstack([data, data, data])

        return _rgb_as_dataset(C, RGB, "Split Window Difference", **kwargs)

    def NightFogDifference(self, **kwargs):
        """
        Night Fog Difference RGB (greyscale):
        (See `Quick Guide <http://cimss.ssec.wisc.edu/goes/OCLOFactSheetPDFs/ABIQuickGuide_NightFogBTD.pdf>`__ for reference)

        .. image:: /_static/NightFogDifference.png

        Parameters
        ----------
        C : xarray.Dataset
            A GOES ABI multichannel file opened with xarray.
        \*\*kwargs :
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        data = C["CMI_C13"].data - C["CMI_C07"].data

        # _normalize values
        data = _normalize(data, -90, 15)

        # Invert data
        data = 1 - data

        # The final RGB array :)
        RGB = np.dstack([data, data, data])

        return _rgb_as_dataset(C, RGB, "Night Fog Difference", **kwargs)

    def RocketPlume(self, night=False, **kwargs):
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
            Keyword arguments for ``_rgb_as_dataset`` function.
            - latlon : derive latitude and longitude of each pixel

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R = C["CMI_C07"].data
        G = C["CMI_C08"].data
        if not night:
            B = C["CMI_C02"].data
        else:
            B = C["CMI_C05"].data

        # _normalize values
        R = _normalize(R, 273, 338)
        G = _normalize(G, 233, 253)
        B = _normalize(B, 0, 0.80)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        return _rgb_as_dataset(C, RGB, "RocketPlume", **kwargs)

    #######################
    # 🚧 Construction Zone
    #######################
    def _normalizedBurnRatio(self, **kwargs):
        """
        _normalized Burn Ratio

        **THIS FUNCTION IS NOT FULLY DEVELOPED. Need more info.**

        NBR= (0.86 µm – 2.2 µm)/(0.86 um + 2.2 um)


        https://ntrs.nasa.gov/citations/20190030825

        Parameters
        ----------

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        C3 = C["CMI_C03"].data
        C6 = C["CMI_C06"].data
        data = (C3 - C6) / (C3 + C6)

        # Invert data
        # data = 1-data

        # The final RGB array :)
        RGB = np.dstack([data, data, data])

        return _rgb_as_dataset(C, RGB, "_normalized Burn Ratio", **kwargs)
