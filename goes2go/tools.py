## Brian Blaylock
## September 22, 2020

"""
==========
GOES Tools
==========
Tools for handeling NOAA GOES data files.
"""

import numpy as np
import cartopy.crs as ccrs
import metpy
from shapely.geometry import Point, Polygon

def field_of_view(G, resolution=60):
    """
    Create a field-of-view polygon for the GOES data.
    
    Based on information from the GOES-R Series Data Book
    https://www.goes-r.gov/downloads/resources/documents/GOES-RSeriesDataBook.pdf
    
    GLM lense field of view is 16 degree, or +/- 8 degrees (see page 225)
    ABI full-disk field of view if 17.4 degrees (see page 48)
    
    To plot the field of view on the carotpy axes, do the following:
    
    .. code:: python
        FOV, geo = field_of_view(G)
        ax = plt.subplot(projection=geo)
        ax.add_geometries([FOV], crs=geo)
    
    Parameters
    ----------
    G - xarray.Dataset
        The GOES NetCDF file opened with xarray.
    """
    if G.title.startswith('ABI'):
        nadir_lon = G.geospatial_lat_lon_extent.geospatial_lon_nadir
        nadir_lat = G.geospatial_lat_lon_extent.geospatial_lat_nadir
        sat_height = G.nominal_satellite_height.item() * 1000
        # Field of view in degrees
        FOV = 17.4 - .06 # little less to account for imprecise ellipsoid
    elif G.title.startswith('GLM'):
        nadir_lon = G.lon_field_of_view.item()
        nadir_lat = G.lat_field_of_view.item()
        sat_height = G.nominal_satellite_height.item() * 1000
        FOV = 16
    
    # Create a cartopy coordinate reference system for the data
    crs = ccrs.Geostationary(central_longitude=nadir_lon,
                             satellite_height=sat_height)
    
    # Create polygon of the field of view. This polygon is in 
    # the geostationary crs projection units, and is in meters.
    FOV_radius = np.radians(FOV/2) * sat_height
    FOV_poly = Point(nadir_lon, nadir_lat).buffer(FOV_radius,
                                                  resolution=resolution)
    
    ## GLM is a bit funny. I haven't found this in the documentation
    ## anywhere, yet, but the GLM field-of-view is not exactly 
    ## the full circle, there is a square area cut out of it.
    ## The square FOV is ~ 15 degrees
    if G.title.startswith('GLM'):
        FOV_radius = np.radians(15/2) * sat_height
        # Create a square with many points clockwise, starting in bottom left corner
        side1x, side1y = np.ones(resolution)*-FOV_radius, np.linspace(-FOV_radius, FOV_radius, resolution), 
        side2x, side2y = np.linspace(-FOV_radius, FOV_radius, resolution), np.ones(resolution)*FOV_radius
        side3x, side3y = np.ones(resolution)*FOV_radius, np.linspace(FOV_radius, -FOV_radius, resolution),
        side4x, side4y = np.linspace(FOV_radius, -FOV_radius, resolution), np.ones(resolution)*-FOV_radius
        x = np.hstack([side1x, side2x, side3x, side4x])
        y = np.hstack([side1y, side2y, side3y, side4y])
        square_FOV = Polygon(zip(x,y))
        FOV_poly = FOV_poly.intersection(square_FOV)
    
    return FOV_poly, crs
    
    
    
        
        
def abi_crs(G, reference_variable='CMI_C01'):
    """
    Get coordinate reference system for the Advanced Baseline Imager.

    Parameters
    ----------
    G : xarray.Dataset
        An xarray.Dataset to derive the coordinate reference system.
    reference_variable : str
        A variable in the xarray.Dataset to use to parse projection from.
    Returns
    -------
    Three objects: 
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