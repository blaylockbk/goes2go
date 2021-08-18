## Brian Blaylock
## September 22, 2020

"""
===========
Other Tools
===========
Other tools for handeling NOAA GOES data files.
"""

import numpy as np
import cartopy.crs as ccrs

try:
    import metpy  # Need accessors to get projection info.
except:
    # Not sure why sphinx can't import metpy??
    pass
from shapely.geometry import Point, Polygon


def field_of_view(G, resolution=60, reduce_abi_fov=0.06):
    """
    Create a field-of-view polygon for the GOES data.

    Based on information from the `GOES-R Series Data Book
    <https://www.goes-r.gov/downloads/resources/documents/GOES-RSeriesDataBook.pdf>`_.

    GLM lense field of view is 16 degree, or +/- 8 degrees (see page 225)
    ABI full-disk field of view if 17.4 degrees (see page 48)

    To plot the field of view on the cartopy axes, do the following:

    .. code:: python

        FOV, geo = field_of_view(G)
        ax = plt.subplot(projection=geo)
        ax.add_geometries([FOV], crs=geo)

    Parameters
    ----------
    G : xarray.Dataset
        The GOES NetCDF file opened with xarray. A file is required
        because we get info from the file to define the projection.
    resolution : int
        Resolution of polygon shapes
    reduce_abi_fov : float or int
        Since the globe isn't a perfect ellipse, reduce the field of
        view just slightly to get all the points to be on the projection
        plane. If this number is less than the default, the polygon
        will not be calculated correctly because edge points will lie
        off the projection globe.
    """
    if G.title.startswith("ABI"):
        globe_kwargs = dict(
            semimajor_axis=G.goes_imager_projection.semi_major_axis,
            semiminor_axis=G.goes_imager_projection.semi_minor_axis,
            inverse_flattening=G.goes_imager_projection.inverse_flattening,
        )
        sat_height = G.goes_imager_projection.perspective_point_height
        nadir_lon = G.geospatial_lat_lon_extent.geospatial_lon_nadir
        nadir_lat = G.geospatial_lat_lon_extent.geospatial_lat_nadir
        # Field of view in degrees
        FOV = 17.4
        FOV -= reduce_abi_fov  # little less to account for imprecise ellipsoid
    elif G.title.startswith("GLM"):
        globe_kwargs = dict(
            semimajor_axis=G.goes_lat_lon_projection.semi_major_axis,
            semiminor_axis=G.goes_lat_lon_projection.semi_minor_axis,
            inverse_flattening=G.goes_lat_lon_projection.inverse_flattening,
        )
        sat_height = G.nominal_satellite_height.item() * 1000
        nadir_lon = G.lon_field_of_view.item()
        nadir_lat = G.lat_field_of_view.item()
        FOV = 8 * 2
        FOV += 0.15  # Little offset to better match boundary from Rudlosky et al. 2018

    # Create a cartopy coordinate reference system for the data

    # These numbers are from the `goes_imager_projection` variable
    globe = ccrs.Globe(ellipse=None, **globe_kwargs)

    crs = ccrs.Geostationary(
        central_longitude=nadir_lon,
        satellite_height=sat_height,
        globe=globe,
        sweep_axis="x",
    )

    # Create polygon of the field of view. This polygon is in
    # the geostationary crs projection units, and is in meters.
    # The central point is at 0,0 (not the nadir position), because
    # we are working in the geostationary projection coordinates
    # and the center point is 0,0 meters.
    FOV_radius = np.radians(FOV / 2) * sat_height
    FOV_poly = Point(0, 0).buffer(FOV_radius, resolution=resolution)

    ## GLM is a bit funny. I haven't found this in the documentation
    ## anywhere, yet, but the GLM field-of-view is not exactly
    ## the full circle, there is a square area cut out of it.
    ## The square FOV is ~ 15 degrees
    if G.title.startswith("GLM"):
        FOV_square = 15 / 2
        # FOV_square += .1 # offset to match Rudlosky et al. 2018
        FOV_radius = np.radians(FOV_square) * sat_height
        # Create a square with many points clockwise, starting in bottom left corner
        side1x, side1y = (
            np.ones(resolution) * -FOV_radius,
            np.linspace(-FOV_radius, FOV_radius, resolution),
        )
        side2x, side2y = (
            np.linspace(-FOV_radius, FOV_radius, resolution),
            np.ones(resolution) * FOV_radius,
        )
        side3x, side3y = (
            np.ones(resolution) * FOV_radius,
            np.linspace(FOV_radius, -FOV_radius, resolution),
        )
        side4x, side4y = (
            np.linspace(FOV_radius, -FOV_radius, resolution),
            np.ones(resolution) * -FOV_radius,
        )
        x = np.hstack([side1x, side2x, side3x, side4x])
        y = np.hstack([side1y, side2y, side3y, side4y])
        square_FOV = Polygon(zip(x, y))
        FOV_poly = FOV_poly.intersection(square_FOV)

        return FOV_poly, crs

    if G.title.startswith("ABI"):
        # We have the global field of view
        # now we need the domain field of view
        dom_border = np.array(
            [(i, G.y.data[0]) for i in G.x.data]
            + [(G.x.data[-1], i) for i in G.y.data]
            + [(i, G.y.data[-1]) for i in G.x.data[::-1]]
            + [(G.x.data[0], i) for i in G.y.data[::-1]]
        )
        FOV_dom = Polygon(dom_border * sat_height)
        FOV_dom = FOV_dom.intersection(FOV_poly)
        return FOV_poly, FOV_dom, crs


def abi_crs(G, reference_variable="CMI_C01"):
    """
    Get coordinate reference system for the Advanced Baseline Imager (ABI).

    Parameters
    ----------
    G : xarray.Dataset
        An xarray.Dataset to derive the coordinate reference system.
    reference_variable : str
        A variable in the xarray.Dataset to use to parse projection from.

    Returns
    -------
    Three objects are returned
        1. cartopy coordinate reference system
        2. data projection coordinates in x direction
        3. data projection coordinates in y direction

    """
    # We'll use the `CMI_C01` variable as a 'hook' to get the CF metadata.
    dat = G.metpy.parse_cf(reference_variable)

    crs = dat.metpy.cartopy_crs

    # We also need the x (north/south) and y (east/west) axis sweep of the ABI data
    x, y = (dat.x, dat.y)

    return crs, x, y


def glm_crs(G, reference_variable="flash_lat"):
    """Not too useful, because it's just lat/lon coordinates"""
    dat = G.metpy.parse_cf("flash_lat")
    crs = dat.metpy.cartopy_crs
    return crs
