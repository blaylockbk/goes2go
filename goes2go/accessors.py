## Brian Blaylock
## July 9, 2021

"""
===========
RGB Recipes
===========

RGB Recipes for the GOES Advanced Baseline Imager.

More about xarray accessors:
http://xarray.pydata.org/en/stable/internals/extending-xarray.html?highlight=extending#
"""

import warnings

import cartopy.crs as ccrs
import numpy as np
import xarray as xr
from shapely.geometry import Point, Polygon


########################
# Image Processing Tools
def _gamma_correction(a, gamma, verbose=False):
    """
    Darken or lighten an image with `gamma correction.

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
    Normalize values between an upper and lower limit between 0 and 1.

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
    """
    norm = (value - lower_limit) / (upper_limit - lower_limit)
    if clip:
        norm = np.clip(norm, 0, 1)
    return norm


@xr.register_dataset_accessor("FOV")
class fieldOfViewAccessor:
    """
    Create a field-of-view polygon for the GOES data.

    Based on information from the `GOES-R Series Data Book
    <https://www.goes-r.gov/downloads/resources/documents/GOES-RSeriesDataBook.pdf>`_.

    GLM lense field of view is 16 degree, or +/- 8 degrees (see page 225)
    ABI full-disk field of view if 17.4 degrees (see page 48)
    """

    def __init__(self, xarray_obj):
        self._obj = xarray_obj
        self._crs = None
        self._x = None
        self._y = None
        self._sat_h = self._obj.goes_imager_projection.perspective_point_height
        self._imshow_kwargs = None

    @property
    def crs(self):
        """Cartopy coordinate reference system for the Satellite."""
        ds = self._obj
        if ds.cdm_data_type == "Image":
            globe_kwargs = dict(
                semimajor_axis=ds.goes_imager_projection.semi_major_axis,
                semiminor_axis=ds.goes_imager_projection.semi_minor_axis,
                inverse_flattening=ds.goes_imager_projection.inverse_flattening,
            )
            sat_height = ds.goes_imager_projection.perspective_point_height
            nadir_lon = ds.geospatial_lat_lon_extent.geospatial_lon_nadir
            # nadir_lat = ds.geospatial_lat_lon_extent.geospatial_lat_nadir
        elif ds.cdm_data_type == "Point":
            globe_kwargs = dict(
                semimajor_axis=ds.goes_lat_lon_projection.semi_major_axis,
                semiminor_axis=ds.goes_lat_lon_projection.semi_minor_axis,
                inverse_flattening=ds.goes_lat_lon_projection.inverse_flattening,
            )
            sat_height = ds.nominal_satellite_height.item() * 1000
            nadir_lon = ds.lon_field_of_view.item()
            # nadir_lat = ds.lat_field_of_view.item()
        # Create a cartopy coordinate reference system (crs)
        globe = ccrs.Globe(ellipse=None, **globe_kwargs)

        crs = ccrs.Geostationary(
            central_longitude=nadir_lon,
            satellite_height=sat_height,
            globe=globe,
            sweep_axis="x",
        )

        return crs

    @property
    def x(self):
        """The x sweep in crs units (m); x * sat_height."""
        if self._x is None:
            self._x = self._obj.x * self._sat_h
        return self._x

    @property
    def y(self):
        """The y sweep in crs units (m); x * sat_height."""
        if self._y is None:
            self._y = self._obj.y * self._sat_h
        return self._y

    @property
    def imshow_kwargs(self):
        """Key word arguments for plt.imshow for generating images.

        Projection axis must be the coordinate reference system.
        """
        if self._imshow_kwargs is None:
            self._imshow_kwargs = dict(
                extent=[
                    self.x.data.min(),
                    self.x.data.max(),
                    self.y.data.min(),
                    self.y.data.max(),
                ],
                transform=self._crs,
                origin="upper",
                interpolation="none",
            )
        return self._imshow_kwargs

    def get_latlon(self):
        """Get lat/lon of all points."""
        X, Y = np.meshgrid(self.x, self.y)
        a = ccrs.PlateCarree().transform_points(self._crs, X, Y)
        lons, lats, _ = a[:, :, 0], a[:, :, 1], a[:, :, 2]

        self._obj.coords["longitude"] = (("y", "x"), lons)
        self._obj.coords["latitude"] = (("y", "x"), lats)
        return self._obj["latitude"], self._obj["longitude"]

    @property
    def full_disk(self):
        """
        Full-disk field of view for the ABI or GLM instruments.

        .. image:: /_static/ABI_field-of-view.png

        .. image:: /_static/GLM_field-of-view.png

        Returns
        -------
        shapely.Polygon
        """
        ds = self._obj

        # Create polygon of the field of view. This polygon is in
        # the geostationary crs projection units, and is in meters.
        # The central point is at 0,0 (not the nadir position), because
        # we are working in the geostationary projection coordinates
        # and the center point is 0,0 meters.
        if ds.title.startswith("ABI"):
            # Field of view (FOV) in degrees. Reduce just a little to
            # get all polygon points in the projection plane so cartopy
            # can plot it correctly.
            # TODO: Is there a more "correct" way to handle this?
            sat_height = ds.goes_imager_projection.perspective_point_height
            FOV_degrees = 17.4
            FOV_degrees -= 0.06
            FOV_radius = np.radians(FOV_degrees / 2) * sat_height
            FOV_polygon = Point(0, 0).buffer(FOV_radius, resolution=160)
        elif ds.title.startswith("GLM"):
            # Field of view (FOV) of GLM is different than ABI.
            # Do a little offset to better match boundary from
            # Rudlosky et al. 2018
            sat_height = ds.nominal_satellite_height.item() * 1000
            FOV_degrees = 8 * 2
            FOV_degrees += 0.15
            FOV_radius = np.radians(FOV_degrees / 2) * sat_height
            FOV_polygon = Point(0, 0).buffer(FOV_radius, resolution=160)

            # I haven't found this explained in the documentation yet,
            # but the GLM field-of-view is not exactly the full circle,
            # there is a square area cut out of it.
            # The square FOV width and height is about 15 degrees.
            cutout_FOV_degrees = 15 / 2
            cutout_FOV_length = np.radians(cutout_FOV_degrees) * sat_height
            # Create a square with many points clockwise, starting in bottom left corner
            side_points = np.linspace(-cutout_FOV_length, cutout_FOV_length, 300)
            cutout_points = np.array(
                [(-cutout_FOV_length, i) for i in side_points]
                + [(i, cutout_FOV_length) for i in side_points]
                + [(cutout_FOV_length, i) for i in side_points][::-1]
                + [(i, -cutout_FOV_length) for i in side_points][::-1]
            )
            cutout = Polygon(cutout_points)
            FOV_polygon = FOV_polygon.intersection(cutout)
        return FOV_polygon

    @property
    def domain(self):
        """
        Field of view for the ABI domain (CONUS or MesoScale).

        .. image:: /_static/ABI_field-of-view_16dom.png

        .. image:: /_static/ABI_field-of-view_16M1M2.png

        .. image:: /_static/ABI_field-of-view_17dom.png

        Returns
        -------
        shapely.Polygon
        """
        ds = self._obj
        if not ds.title.startswith("ABI"):
            raise ValueError("Domain polygon only available for ABI CONUS and Mesoscale files.")
        sat_height = ds.goes_imager_projection.perspective_point_height
        # Trim out domain FOV from the full disk (this is necessary for GOES-16).
        dom_border = np.array(
            [(i, ds.y.data[0]) for i in ds.x.data]
            + [(ds.x.data[-1], i) for i in ds.y.data]
            + [(i, ds.y.data[-1]) for i in ds.x.data[::-1]]
            + [(ds.x.data[0], i) for i in ds.y.data[::-1]]
        )
        FOV_domain = Polygon(dom_border * sat_height)
        FOV_domain = FOV_domain.intersection(self.full_disk)
        return FOV_domain


@xr.register_dataset_accessor("rgb")
class rgbAccessor:
    """An accessor to create RGB composites."""

    def __init__(self, xarray_obj):
        self._obj = xarray_obj
        if not self._obj.title == "ABI L2 Cloud and Moisture Imagery":
            raise ValueError("Dataset must be an ABI L2 Cloud and Moisture Imagery file.")
        self._crs = None
        self._x = None
        self._y = None
        self._sat_h = self._obj.goes_imager_projection.perspective_point_height
        self._imshow_kwargs = None

    @property
    def crs(self):
        """Cartopy coordinate reference system."""
        if self._crs is None:
            # Why am I doing this? To cache the values.
            self._crs = self._obj.FOV.crs
        return self._crs

    @property
    def x(self):
        """The x sweep in crs units (m); x * sat_height."""
        if self._x is None:
            self._x = self._obj.x * self._sat_h
        return self._x

    @property
    def y(self):
        """The y sweep in crs units (m); x * sat_height."""
        if self._y is None:
            self._y = self._obj.y * self._sat_h
        return self._y

    @property
    def imshow_kwargs(self):
        """Key word arguments for plt.imshow for generating images.

        Projection axis must be the coordinate reference system.
        """
        if self._imshow_kwargs is None:
            self._imshow_kwargs = dict(
                extent=[
                    self.x.data.min(),
                    self.x.data.max(),
                    self.y.data.min(),
                    self.y.data.max(),
                ],
                transform=self._crs,
                origin="upper",
                interpolation="none",
            )
        return self._imshow_kwargs

    def get_latlon(self):
        """Get lat/lon of all points."""
        X, Y = np.meshgrid(self.x, self.y)
        a = ccrs.PlateCarree().transform_points(self._crs, X, Y)
        lons, lats, _ = a[:, :, 0], a[:, :, 1], a[:, :, 2]

        self._obj.coords["longitude"] = (("y", "x"), lons)
        self._obj.coords["latitude"] = (("y", "x"), lats)
        return self._obj["latitude"], self._obj["longitude"]

    ####################################################################
    # Helpers
    def _load_RGB_channels(self, channels):
        """Load the specified RGB channels.

        Return the R, G, and B arrays for the three channels requested.
        This function convert any data given in Kelvin to Celsius.

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
                # Convert form Kelvin to Celsius
                RGB.append(ds["CMI_C%02d" % c].data - 273.15)
            else:
                RGB.append(ds["CMI_C%02d" % c].data)
        return RGB

    ####################################################################
    # RGB Recipes
    def TrueColor(self, gamma=2.2, pseudoGreen=True, night_IR=True):
        """Create a True Color RGB.

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
        ds["TrueColor"].attrs["Quick Guide"] = (
            "http://cimss.ssec.wisc.edu/goes/OCLOFactSheetPDFs/ABIQuickGuide_CIMSSRGB_v2.pdf"
        )
        ds["TrueColor"].attrs["long_name"] = "True Color"

        return ds["TrueColor"]

    def NaturalColor(self, gamma=0.8, pseudoGreen=True, night_IR=False):
        """Create a Natural Color RGB based on CIMSS method.

        Thanks Rick Kohrs!
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
        gamma : float
            Darken or lighten an image with `gamma correction
            <https://en.wikipedia.org/wiki/_gamma_correction>`_.
            Values > 1 will lighten an image.
            Values < 1 will darken an image.
        night_IR : bool
            If True, use Clean IR (channel 13) as maximum RGB value overlay
            so that cold clouds show up at night. (Be aware that some
            daytime clouds might appear brighter).

        """
        ds = self._obj

        def breakpoint_stretch(C, breakpoint):
            """Contrast stretching by break point.

            (number provided by Rick Kohrs).
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
        R, G, B = self._load_RGB_channels((2, 3, 1))

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
            IR = ds["CMI_C13"]
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

        ds["NaturalColor"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["NaturalColor"].attrs["Quick Guide"] = (
            "http://cimss.ssec.wisc.edu/goes/OCLOFactSheetPDFs/ABIQuickGuide_CIMSSRGB_v2.pdf"
        )
        ds["NaturalColor"].attrs["long_name"] = "Natural Color"

        return ds["NaturalColor"]

    def FireTemperature(self):
        """Create the Fire Temperature RGB.

        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/Fire_Temperature_RGB.pdf>`__ for reference)

        .. image:: /_static/FireTemperature.png


        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R, G, B = self._load_RGB_channels((7, 6, 5))

        # _normalize each channel by the appropriate range of values (clipping happens in function)
        R = _normalize(R, 0, 60)
        G = _normalize(G, 0, 1)
        B = _normalize(B, 0, 0.75)

        # Apply the gamma correction to Red channel.
        #   corrected_value = value^(1/gamma)
        gamma = 0.4
        R = _gamma_correction(R, gamma)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        ds["FireTemperature"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["FireTemperature"].attrs["Quick Guide"] = (
            "http://rammb.cira.colostate.edu/training/visit/quick_guides/Fire_Temperature_RGB.pdf"
        )
        ds["FireTemperature"].attrs["long_name"] = "Fire Temperature"

        return ds["FireTemperature"]

    def AirMass(self):
        """Create the Air Mass RGB.

        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_AirMassRGB_final.pdf>`__ for reference)

        .. image:: /_static/AirMass.png


        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R = ds["CMI_C08"].data - ds["CMI_C10"].data
        G = ds["CMI_C12"].data - ds["CMI_C13"].data
        B = ds["CMI_C08"].data - 273.15  # remember to convert to Celsius

        # _normalize each channel by the appropriate range of values. e.g. R = (R-minimum)/(maximum-minimum)
        R = _normalize(R, -26.2, 0.6)
        G = _normalize(G, -42.2, 6.7)
        B = _normalize(B, -64.65, -29.25)

        # Invert B
        B = 1 - B

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        ds["AirMass"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["AirMass"].attrs["Quick Guide"] = (
            "http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_AirMassRGB_final.pdf"
        )
        ds["AirMass"].attrs["long_name"] = "Air Mass"

        return ds["AirMass"]

    def AirMassTropical(self):
        """Create the Air Mass Tropical RGB.

        (See `Quick Guide <https://www.eumetsat.int/media/43301>`__ for reference)

        .. image:: /_static/AirMassTropical.png


        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R = ds["CMI_C08"].data - ds["CMI_C13"].data
        G = ds["CMI_C12"].data - ds["CMI_C13"].data
        B = ds["CMI_C08"].data - 273.15  # remember to convert to Celsius

        # _normalize each channel by the appropriate range of values. e.g. R = (R-minimum)/(maximum-minimum)
        R = _normalize(R, -25, 5)
        G = _normalize(G, -30, 25)
        B = _normalize(B, -83, -30)

        # Invert B
        B = 1 - B

        # Apply the gamma correction to Red channel.
        #   corrected_value = value^(1/gamma)
        gamma = 0.5
        G = _gamma_correction(G, gamma)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        ds["AirMassTropical"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["AirMassTropical"].attrs["Quick Guide"] = (
            "https://www.eumetsat.int/media/43301"
        )
        ds["AirMassTropical"].attrs["long_name"] = "Air Mass Tropical"

        return ds["AirMassTropical"]

    def AirMassTropicalPac(self):
        """Create the Air Mass Tropical Pac RGB.

        (See `Blog Write-up <https://cimss.ssec.wisc.edu/satellite-blog/archives/51777>`__ for reference)

        .. image:: /_static/AirMassTropicalPac.png

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R = ds["CMI_C08"].data - ds["CMI_C10"].data
        G = ds["CMI_C12"].data - ds["CMI_C13"].data
        B = ds["CMI_C08"].data - 273.15  # remember to convert to Celsius

        # _normalize each channel by the appropriate range of values. e.g. R = (R-minimum)/(maximum-minimum)
        R = _normalize(R, -26.2, 0.6)
        G = _normalize(G, -26.2, 27.4)
        B = _normalize(B, -64.45, -29.25)

        # Invert B
        B = 1 - B

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        ds["AirMassTropicalPac"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["AirMassTropicalPac"].attrs["Quick Guide"] = (
            "https://cimss.ssec.wisc.edu/satellite-blog/archives/51777"
        )
        ds["AirMassTropicalPac"].attrs["long_name"] = "Air Mass Tropical Pac"

        return ds["AirMassTropicalPac"]

    def DayCloudPhase(self):
        """Create the Day Cloud Phase Distinction RGB.

        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/Day_Cloud_Phase_Distinction.pdf>`__ for reference)

        .. image:: /_static/DayCloudPhase.png


        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R, G, B = self._load_RGB_channels((13, 2, 5))

        # _normalize each channel by the appropriate range of values. (Clipping happens inside function)
        R = _normalize(R, -53.5, 7.5)
        G = _normalize(G, 0, 0.78)
        B = _normalize(B, 0.01, 0.59)

        # Invert R
        R = 1 - R

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        ds["DayCloudPhase"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["DayCloudPhase"].attrs["Quick Guide"] = (
            "http://rammb.cira.colostate.edu/training/visit/quick_guides/Day_Cloud_Phase_Distinction.pdf"
        )
        ds["DayCloudPhase"].attrs["long_name"] = "Day Cloud Phase"

        return ds["DayCloudPhase"]

    def DayConvection(self):
        """Create the Day Convection RGB.

        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_DayConvectionRGB_final.pdf>`__ for reference)

        .. image:: /_static/DayConvection.png


        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        # NOTE: Each R, G, B is a channel difference.
        R = ds["CMI_C08"].data - ds["CMI_C10"].data
        G = ds["CMI_C07"].data - ds["CMI_C13"].data
        B = ds["CMI_C05"].data - ds["CMI_C02"].data

        # _normalize each channel by the appropriate range of values.
        R = _normalize(R, -35, 5)
        G = _normalize(G, -5, 60)
        B = _normalize(B, -0.75, 0.25)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        ds["DayConvection"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["DayConvection"].attrs["Quick Guide"] = (
            "http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_DayConvectionRGB_final.pdf"
        )
        ds["DayConvection"].attrs["long_name"] = "Day Convection"

        return ds["DayConvection"]

    def DayCloudConvection(self):
        """Create the Day Cloud Convection RGB.

        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_DayCloudConvectionRGB_final.pdf>`__ for reference)

        .. image:: /_static/DayCloudConvection.png

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R, G, B = self._load_RGB_channels((2, 2, 13))

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

        ds["DayCloudConvection"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["DayCloudConvection"].attrs["Quick Guide"] = (
            "http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_DayCloudConvectionRGB_final.pdf"
        )
        ds["DayCloudConvection"].attrs["long_name"] = "Day Cloud Convection"

        return ds["DayCloudConvection"]

    def DayLandCloud(self):
        """Create the Day Land Cloud Fire RGB.

        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_daylandcloudRGB_final.pdf>`__ for reference)

        .. image:: /_static/DayLandCloud.png


        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R, G, B = self._load_RGB_channels((5, 3, 2))

        # _normalize each channel by the appropriate range of values  e.g. R = (R-minimum)/(maximum-minimum)
        R = _normalize(R, 0, 0.975)
        G = _normalize(G, 0, 1.086)
        B = _normalize(B, 0, 1)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        ds["DayLandCloud"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["DayLandCloud"].attrs["Quick Guide"] = (
            "http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_daylandcloudRGB_final.pdf"
        )
        ds["DayLandCloud"].attrs["long_name"] = "Day Land Cloud"

        return ds["DayLandCloud"]

    def DayLandCloudFire(self):
        """Create the Day Land Cloud Fire RGB.

        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_DayLandCloudFireRGB_final.pdf>`__ for reference)

        .. image:: /_static/DayLandCloudFire.png


        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R, G, B = self._load_RGB_channels((6, 3, 2))

        # _normalize each channel by the appropriate range of values  e.g. R = (R-minimum)/(maximum-minimum)
        R = _normalize(R, 0, 1)
        G = _normalize(G, 0, 1)
        B = _normalize(B, 0, 1)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        ds["DayLandCloudFire"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["DayLandCloudFire"].attrs["Quick Guide"] = (
            "http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_DayLandCloudFireRGB_final.pdf"
        )
        ds["DayLandCloudFire"].attrs["long_name"] = "Day Land Cloud Fire"

        return ds["DayLandCloudFire"]

    def WaterVapor(self):
        """Create the Simple Water Vapor RGB.

        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/Simple_Water_Vapor_RGB.pdf>`__ for reference)

        .. image:: /_static/WaterVapor.png


        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables.
        R, G, B = self._load_RGB_channels((13, 8, 10))

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

        ds["WaterVapor"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["WaterVapor"].attrs["Quick Guide"] = (
            "http://rammb.cira.colostate.edu/training/visit/quick_guides/Simple_Water_Vapor_RGB.pdf"
        )
        ds["WaterVapor"].attrs["long_name"] = "Water Vapor"

        return ds["WaterVapor"]

    def DifferentialWaterVapor(self):
        """Differential Water Vapor RGB.

        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_DifferentialWaterVaporRGB_final.pdf>`__ for reference)

        .. image:: /_static/DifferentialWaterVapor.png


        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables.
        R = ds["CMI_C10"].data - ds["CMI_C08"].data
        G = ds["CMI_C10"].data - 273.15
        B = ds["CMI_C08"].data - 273.15

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

        ds["DifferentialWaterVapor"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["DifferentialWaterVapor"].attrs["Quick Guide"] = (
            "http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_DifferentialWaterVaporRGB_final.pdf"
        )
        ds["DifferentialWaterVapor"].attrs["long_name"] = "Differential Water Vapor"

        return ds["DifferentialWaterVapor"]

    def DaySnowFog(self):
        """Day Snow-Fog RGB.

        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_DaySnowFog.pdf>`__ for reference)

        .. image:: /_static/DaySnowFog.png


        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R = ds["CMI_C03"].data
        G = ds["CMI_C05"].data
        B = ds["CMI_C07"].data - ds["CMI_C13"].data

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

        ds["DaySnowFog"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["DaySnowFog"].attrs["Quick Guide"] = (
            "http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_DaySnowFog.pdf"
        )
        ds["DaySnowFog"].attrs["long_name"] = "Day Snow Fog"

        return ds["DaySnowFog"]

    def NighttimeMicrophysics(self):
        """Create the Nighttime Microphysics RGB.

        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_NtMicroRGB_final.pdf>`__ for reference)

        .. image:: /_static/NighttimeMicrophysics.png


        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R = ds["CMI_C15"].data - ds["CMI_C13"].data
        G = ds["CMI_C13"].data - ds["CMI_C07"].data
        B = ds["CMI_C13"].data - 273.15

        # _normalize values
        R = _normalize(R, -6.7, 2.6)
        G = _normalize(G, -3.1, 5.2)
        B = _normalize(B, -29.6, 19.5)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        ds["NighttimeMicrophysics"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["NighttimeMicrophysics"].attrs["Quick Guide"] = (
            "http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_NtMicroRGB_final.pdf"
        )
        ds["NighttimeMicrophysics"].attrs["long_name"] = "Nighttime Microphysics"

        return ds["NighttimeMicrophysics"]

    def Dust(self):
        """Create the SulfurDioxide RGB.

        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/Dust_RGB_Quick_Guide.pdf>`__ for reference)

        .. image:: /_static/Dust.png


        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R = ds["CMI_C15"].data - ds["CMI_C13"].data
        G = ds["CMI_C14"].data - ds["CMI_C11"].data
        B = ds["CMI_C13"].data - 273.15

        # _normalize values
        R = _normalize(R, -6.7, 2.6)
        G = _normalize(G, -0.5, 20)
        B = _normalize(B, -11.95, 15.55)

        # Apply a gamma correction to the image
        gamma = 2.5
        G = _gamma_correction(G, gamma)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        ds["Dust"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["Dust"].attrs["Quick Guide"] = (
            "http://rammb.cira.colostate.edu/training/visit/quick_guides/Dust_RGB_Quick_Guide.pdf"
        )
        ds["Dust"].attrs["long_name"] = "Dust"

        return ds["Dust"]

    def SulfurDioxide(self):
        """Create the SulfurDioxide RGB.

        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/Quick_Guide_SO2_RGB.pdf>`__ for reference)

        .. image:: /_static/SulfurDioxide.png


        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R = ds["CMI_C09"].data - ds["CMI_C10"].data
        G = ds["CMI_C13"].data - ds["CMI_C11"].data
        B = ds["CMI_C07"].data - 273.15

        # _normalize values
        R = _normalize(R, -4, 2)
        G = _normalize(G, -4, 5)
        B = _normalize(B, -30.1, 29.8)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        ds["SulfurDioxide"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["SulfurDioxide"].attrs["Quick Guide"] = (
            "http://rammb.cira.colostate.edu/training/visit/quick_guides/Quick_Guide_SO2_RGB.pdf"
        )
        ds["SulfurDioxide"].attrs["long_name"] = "Sulfur Dioxide"

        return ds["SulfurDioxide"]

    def Ash(self):
        """Create the Ash RGB.

        (See `Quick Guide <http://rammb.cira.colostate.edu/training/visit/quick_guides/GOES_Ash_RGB.pdf>`__ for reference)

        .. image:: /_static/Ash.png


        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R = ds["CMI_C15"].data - ds["CMI_C13"].data
        G = ds["CMI_C14"].data - ds["CMI_C11"].data
        B = ds["CMI_C13"].data - 273.15

        # _normalize values
        R = _normalize(R, -6.7, 2.6)
        G = _normalize(G, -6, 6.3)
        B = _normalize(B, -29.55, 29.25)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        ds["Ash"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["Ash"].attrs["Quick Guide"] = (
            "http://rammb.cira.colostate.edu/training/visit/quick_guides/GOES_Ash_RGB.pdf"
        )
        ds["Ash"].attrs["long_name"] = "Ash"

        return ds["Ash"]

    def SplitWindowDifference(self):
        """Split Window Difference RGB (greyscale).

        (See `Quick Guide <http://cimss.ssec.wisc.edu/goes/OCLOFactSheetPDFs/ABIQuickGuide_SplitWindowDifference.pdf>`__ for reference)

        .. image:: /_static/SplitWindowDifference.png


        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        data = ds["CMI_C15"].data - ds["CMI_C13"].data

        # _normalize values
        data = _normalize(data, -10, 10)

        # The final RGB array :)
        RGB = np.dstack([data, data, data])

        ds["SplitWindowDifference"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["SplitWindowDifference"].attrs["Quick Guide"] = (
            "http://cimss.ssec.wisc.edu/goes/OCLOFactSheetPDFs/ABIQuickGuide_SplitWindowDifference.pdf"
        )
        ds["SplitWindowDifference"].attrs["long_name"] = "Split Window Difference"

        return ds["SplitWindowDifference"]

    def NightFogDifference(self):
        """Night Fog Difference RGB (greyscale).

        (See `Quick Guide <http://cimss.ssec.wisc.edu/goes/OCLOFactSheetPDFs/ABIQuickGuide_NightFogBTD.pdf>`__ for reference)

        .. image:: /_static/NightFogDifference.png


        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        data = ds["CMI_C13"].data - ds["CMI_C07"].data

        # _normalize values
        data = _normalize(data, -90, 15)

        # Invert data
        data = 1 - data

        # The final RGB array :)
        RGB = np.dstack([data, data, data])

        ds["NightFogDifference"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["NightFogDifference"].attrs["Quick Guide"] = (
            "http://cimss.ssec.wisc.edu/goes/OCLOFactSheetPDFs/ABIQuickGuide_NightFogBTD.pdf"
        )
        ds["NightFogDifference"].attrs["long_name"] = "NightFogDifference"

        return ds["NightFogDifference"]

    def RocketPlume(self, night=False):
        """Create the  Rocket Plume RGB.

        For identifying rocket launches.

        See `this blog <https://cimss.ssec.wisc.edu/satellite-blog/archives/41335>`__ and
        the `Quick Guide <https://cimss.ssec.wisc.edu/satellite-blog/images/2021/06/QuickGuide_Template_GOESRBanner_Rocket_Plume.pdf>`__
        for reference

        .. image:: /_static/RocketPlume.png

        Parameters
        ----------
        night : bool
            If the area is in night, turn this on to use a different channel
            than the daytime application.


        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R = ds["CMI_C07"].data
        G = ds["CMI_C08"].data
        if not night:
            B = ds["CMI_C02"].data
        else:
            B = ds["CMI_C05"].data

        # _normalize values
        R = _normalize(R, 273, 338)
        G = _normalize(G, 233, 253)
        B = _normalize(B, 0, 0.80)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        ds["RocketPlume"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["RocketPlume"].attrs["Quick Guide"] = (
            "https://cimss.ssec.wisc.edu/satellite-blog/images/2021/06/QuickGuide_Template_GOESRBanner_Rocket_Plume.pdf"
        )
        ds["RocketPlume"].attrs["long_name"] = "Rocket Plume"

        return ds["RocketPlume"]

    def NormalizedBurnRatio(self):
        """Create the Normalized Burn Ratio.

        **THIS FUNCTION IS NOT FULLY DEVELOPED. Need more info.**

        NBR= (0.86 µm - 2.2 µm)/(0.86 um + 2.2 um)


        https://ntrs.nasa.gov/citations/20190030825

        """
        warnings.warn(
            "THE `NormalizedBurnRatio` FUNCTION IS NOT FULLY DEVELOPED. NEED MORE INFO."
        )
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        C3 = ds["CMI_C03"].data
        C6 = ds["CMI_C06"].data
        data = (C3 - C6) / (C3 + C6)

        # Invert data
        # data = 1-data

        # The final RGB array :)
        RGB = np.dstack([data, data, data])

        ds["NormalizedBurnRatio"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["NormalizedBurnRatio"].attrs["Quick Guide"] = (
            "https://ntrs.nasa.gov/citations/20190030825"
        )
        ds["NormalizedBurnRatio"].attrs["long_name"] = "Normalized Burn Ratio"

        return ds["NormalizedBurnRatio"]

    def SeaSpray(self, **kwargs):
        """Create the Sea Spray RGB.

        (See `Quick Guide <https://rammb.cira.colostate.edu/training/visit/quick_guides/VIIRS_Sea_Spray_RGB_Quick_Guide_v2.pdf>`__ for reference)

        .. image:: /_static/SeaSpray.png

        """
        ds = self._obj

        # Load the three channels into appropriate R, G, and B variables
        R = ds["CMI_C07"].data - ds["CMI_C13"].data
        G = ds["CMI_C03"].data
        B = ds["CMI_C02"].data

        # Normalize each channel by the appropriate range of values. e.g. R = (R-minimum)/(maximum-minimum)
        R = _normalize(R, 0, 5)
        G = _normalize(G, 0.01, 0.09)  # values for this channel go from 0 to 1.
        B = _normalize(B, 0.02, 0.12)  # values for this channel go from o to 1.

        # Apply a gamma correction to each R, G, B channel
        R = _gamma_correction(R, 1.0)
        G = _gamma_correction(G, 1.67)
        B = _gamma_correction(B, 1.67)

        # The final RGB array :)
        RGB = np.dstack([R, G, B])

        ds["SeaSpray"] = (("y", "x", "rgb"), RGB)
        ds["rgb"] = ["R", "G", "B"]
        ds["SeaSpray"].attrs["Quick Guide"] = (
            "https://rammb.cira.colostate.edu/training/visit/quick_guides/VIIRS_Sea_Spray_RGB_Quick_Guide_v2.pdf"
        )
        ds["SeaSpray"].attrs["long_name"] = "Sea Spray"

        return ds["SeaSpray"]
