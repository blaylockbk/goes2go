## Brian Blaylock
## September 22, 2020

"""
==========
GOES Tools
==========
Tools for handeling NOAA GOES data files.
"""
import cartopy.crs as ccrs
import metpy

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