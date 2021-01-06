## Brian Blaylock
## August 8, 2019

"""
================
GOES RGB Recipes
================

For a demo, look at the `make_RGB_Demo notebook <https://github.com/blaylockbk/goes2go/tree/master/notebooks>`_.
These functions take a GOES-East or GOES-West Multichannel data file
(with label ABI-L2-MCMIPC) and generates an 3D array for various GOES
RGB products. These RGB recipes are from the 
`GOES Quick Guides <http://rammb.cira.colostate.edu/training/visit/quick_guides/>_ 
and include the following:

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

The returned RGB variable is a stacked np.array(). These can easily be viewed
with plt.imshow(RGB). 
The values must range between 0 and 1. Values are normalized between the
specified range:

    .. code-block:: python 

        NormalizedValue = (OriginalValue-LowerLimit)/(UpperLimit-LowerLimit)

If a gamma correction is required, it follows the pattern:

    .. code-block:: python 
        
        R_corrected = R**(1/gamma)

The input for all is the variable C, which represents the file GOES file opened
with xarray:

    .. code-block:: python 
        
        FILE = 'OR_ABI-L2-MCMIPC-M6_G17_s20192201631196_e20192201633575_c20192201634109.nc'
        C = xarray.open_dataset(FILE)
"""

import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import xarray as xr

from goes2go.tools import field_of_view

def get_imshow_kwargs(ds):
    """
    Help with the imshow arguments.
    
    Usage
    -----
    ... code: python
        r = TrueColor(G)
        ax = common_features(r.crs)
        ax.imshow(r.TrueColor, **get_imshow_kwargs(r))
    """
    return dict(
        extent=[ds.x2.data.min(), ds.x2.data.max(),
                ds.y2.data.min(), ds.y2.data.max()],
        transform=ds.crs,
        origin='upper',
        interpolation='none',
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
    ds = xr.Dataset({description.replace(' ', ''): (['y', 'x', 'rgb'], RGB)})
    ds.attrs['description'] = description
    
    # Convert x, y points to latitude/longitude
    _, crs = field_of_view(G)
    sat_h = G.goes_imager_projection.perspective_point_height
    x2 = G.x * sat_h
    y2 = G.y * sat_h
    ds.coords['x2'] = x2
    ds.coords['y2'] = y2
    
    ds['x2'].attrs['long_name'] = 'x sweep in crs units (m); x * sat_height'
    ds['y2'].attrs['long_name'] = 'y sweep in crs units (m); y * sat_height'
    
    ds.attrs['crs'] = crs
    
    if latlon:
        X, Y = np.meshgrid(x2, y2)
        a = ccrs.PlateCarree().transform_points(crs, X, Y)
        lons, lats, _ = a[:,:,0], a[:,:,1], a[:,:,2]
        ds.coords['longitude'] = (('y', 'x'), lons)
        ds.coords['latitude'] = (('y', 'x'), lats)
        
    # Copy some coordinates and attributes of interest from the original data
    for i in ['x', 'y', 't', 'geospatial_lat_lon_extent']:
        ds.coords[i] = G[i]
    for i in ['orbital_slot', 'platform_ID', 'scene_id', 'spatial_resolution', 'instrument_type', 'title']:
        ds.attrs[i] = G.attrs[i]
        
    ## Provide some helpers to plot with imshow        
    ds.attrs['imshow_kwargs'] = get_imshow_kwargs(ds)
    
    ## Provide some helpers to plot with imshow and pcolormesh
    ## Not super useful, because pcolormesh doesn't allow nans in x, y dimension
    #pcolormesh_kwargs = dict(
    #    color = RGB.reshape(np.shape(RGB)[0] * np.shape(RGB)[1], np.shape(RGB)[2])
    #    shading='nearest'
    #    )
    #ds.attrs['pcolormesh_kwargs'] = pcolormesh_kwargs
    
    return ds   

def load_RGB_channels(C, channels):
    """
    Return the R, G, and B arrays for the three channels requested. This 
    function will convert the data any units in Kelvin to Celsius.
    Input: 
        C        - The GOES multi-channel file opened with xarray.
        channels - A tuple of the channel number for each (R, G, B).
                   For example channel=(2, 3, 1) is for the true color RGB
    Return:
        Returns a list with three items--R, G, and B.
        Example: R, G, B = load_RGB_channels(C, (2,3,1))
    """
    # Units of each channel requested
    units = [C['CMI_C%02d' % c].units for c in channels]
    RGB = []
    for u, c in zip(units, channels):
        if u == 'K':
            # Convert form Kelvin to Celsius
            RGB.append(C['CMI_C%02d' % c].data-273.15)
        else:
            RGB.append(C['CMI_C%02d' % c].data)
    return RGB

def normalize(value, lower_limit, upper_limit, clip=True):
    """
    RGB values need to be between 0 and 1. This function normalizes the input
    value between a lower and upper limit. In other words, it converts your
    number to a value in the range between 0 and 1. Follows normalization
    formula explained here: 
            https://stats.stackexchange.com/a/70807/220885
    NormalizedValue = (OriginalValue-LowerLimit)/(UpperLimit-LowerLimit)
            
    Input:
        value       - The original value. A single value, vector, or array.
        upper_limit - The upper limit. 
        lower_limit - The lower limit.
        clip        - True: Clips values between 0 and 1 for RGB.
                    - False: Retain the numbers that extends outside 0-1.
    Output:
        Values normalized between the upper and lower limit.
    """
    norm = (value-lower_limit)/(upper_limit-lower_limit)
    if clip:
        norm = np.clip(norm, 0, 1)
    return norm


def TrueColor(C, trueGreen=True, night_IR=True, **kwargs):
    """
    True Color RGB
    http://cimss.ssec.wisc.edu/goes/OCLOFactSheetPDFs/ABIQuickGuide_CIMSSRGB_v2.pdf
    
    trueGreen : bool
        True: returns the calculated "True" green color
        False: returns the "veggie" channel
    night_IR : bool
        If True, use Clean IR (channel 13) as maximum RGB value so that
        clouds show up at night (and even daytime clouds might appear
        brighter than in real life).
    kwargs : dict
        Keyword arguments for ``rgb_as_dataset`` function.
        - latlon : derive latitude and longitude of each pixel

    """
    # Load the three channels into appropriate R, G, and B variables
    R, G, B = load_RGB_channels(C, (2, 3, 1))

    # Apply range limits for each channel. RGB values must be between 0 and 1
    R = np.clip(R, 0, 1)
    G = np.clip(G, 0, 1)
    B = np.clip(B, 0, 1)

    # Apply a gamma correction to the image
    gamma = 2.2
    R = np.power(R, 1/gamma)
    G = np.power(G, 1/gamma)
    B = np.power(B, 1/gamma)

    if trueGreen:
        # Calculate the "True" Green
        G = 0.45 * R + 0.1 * G + 0.45 * B
        G = np.maximum(G, 0)
        G = np.minimum(G, 1)

    if night_IR:
        # Load the Clean IR channel
        IR = C['CMI_C13']
        # Normalize between a range and clip
        IR = normalize(IR, 90, 313, clip=True)
        # Invert colors so cold clouds are white
        IR = 1 - IR  
        # Lessen the brightness of the coldest clouds so they don't
        # appear so bright when we overlay it on the true color image
        IR = IR/1.4
        # RGB with IR as greyscale
        RGB = np.dstack([np.maximum(R, IR),
                         np.maximum(G, IR),
                         np.maximum(B, IR)])
    else:
        RGB = np.dstack([R, G, B])
    
    return rgb_as_dataset(C, RGB, 'True Color', **kwargs)


def FireTemperature(C, **kwargs):
    """
    Fire Temperature RGB:
    http://rammb.cira.colostate.edu/training/visit/quick_guides/Fire_Temperature_RGB.pdf
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
    R = np.power(R, 1/gamma)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])
    
    return rgb_as_dataset(C, RGB, 'Fire Temperature', **kwargs)


def AirMass(C, **kwargs):
    """
    Air Mass RGB:
    http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_AirMassRGB_final.pdf
    """
    # Load the three channels into appropriate R, G, and B variables
    R = C['CMI_C08'].data - C['CMI_C10'].data
    G = C['CMI_C12'].data - C['CMI_C13'].data
    B = C['CMI_C08'].data-273.15 # remember to convert to Celsius

    # Normalize each channel by the appropriate range of values. e.g. R = (R-minimum)/(maximum-minimum)
    R = normalize(R, -26.2, 0.6)
    G = normalize(G, -42.2, 6.7)
    B = normalize(B, -64.65, -29.25)

    # Invert B
    B = 1-B

    # The final RGB array :)
    RGB = np.dstack([R, G, B])
    
    return rgb_as_dataset(C, RGB, 'Air Mass', **kwargs)


def DayCloudPhase(C, **kwargs):
    """
    Day Cloud Phase Distinction RGB:
    http://rammb.cira.colostate.edu/training/visit/quick_guides/Day_Cloud_Phase_Distinction.pdf
    """
    # Load the three channels into appropriate R, G, and B variables
    R, G, B = load_RGB_channels(C, (13, 2, 5))

    # Normalize each channel by the appropriate range of values. (Clipping happens inside function)
    R = normalize(R, -53.5, 7.5)
    G = normalize(G, 0, 0.78)
    B = normalize(B, .01, 0.59)

    # Invert R
    R = 1-R

    # The final RGB array :)
    RGB = np.dstack([R, G, B])
    
    return rgb_as_dataset(C, RGB, 'Day Cloud Phase', **kwargs)


def DayConvection(C, **kwargs):
    """
    Day Convection RGB:
    http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_DayConvectionRGB_final.pdf
    """
    # Load the three channels into appropriate R, G, and B variables
    # NOTE: Each R, G, B is a channel difference.
    R = C['CMI_C08'].data - C['CMI_C10'].data
    G = C['CMI_C07'].data - C['CMI_C13'].data
    B = C['CMI_C05'].data - C['CMI_C02'].data

    # Normalize each channel by the appropriate range of values.
    R = normalize(R, -35, 5)
    G = normalize(G, -5, 60)
    B = normalize(B, -0.75, 0.25)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])
    
    return rgb_as_dataset(C, RGB, 'Day Convection', **kwargs)


def DayCloudConvection(C, **kwargs):
    """
    Day Convection RGB:
    http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_DayCloudConvectionRGB_final.pdf
    """
    # Load the three channels into appropriate R, G, and B variables
    R, G, B = load_RGB_channels(C, (2,2,13))

    # Normalize each channel by the appropriate range of values.
    R = normalize(R, 0, 1)
    G = normalize(G, 0, 1)
    B = normalize(B, -70.15, 49.85)

    # Invert B
    B = 1-B

    # Apply the gamma correction to Red channel.
    #   corrected_value = value^(1/gamma)
    gamma = 1.7
    R = np.power(R, 1/gamma)
    G = np.power(G, 1/gamma)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])
    
    return rgb_as_dataset(C, RGB, 'Day Cloud Convection', **kwargs)


def DayLandCloud(C, **kwargs):
    """
    Day Land Cloud Fire RGB:
    http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_daylandcloudRGB_final.pdf
    """
    # Load the three channels into appropriate R, G, and B variables
    R, G, B = load_RGB_channels(C, (5, 3, 2))

    # Normalize each channel by the appropriate range of values  e.g. R = (R-minimum)/(maximum-minimum)
    R = normalize(R, 0, .975)
    G = normalize(G, 0, 1.086)
    B = normalize(B, 0, 1)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])
    
    return rgb_as_dataset(C, RGB, 'Day Land Cloud', **kwargs)


def DayLandCloudFire(C, **kwargs):
    """
    Day Land Cloud Fire RGB:
    http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_DayLandCloudFireRGB_final.pdf
    """
    # Load the three channels into appropriate R, G, and B variables
    R, G, B = load_RGB_channels(C, (6, 3, 2))

    # Normalize each channel by the appropriate range of values  e.g. R = (R-minimum)/(maximum-minimum)
    R = normalize(R, 0, 1)
    G = normalize(G, 0, 1)
    B = normalize(B, 0, 1)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])
    
    return rgb_as_dataset(C, RGB, 'Day Land Cloud Fire', **kwargs)


def WaterVapor(C, **kwargs):
    """
    Simple Water Vapor RGB:
    http://rammb.cira.colostate.edu/training/visit/quick_guides/Simple_Water_Vapor_RGB.pdf
    """
    # Load the three channels into appropriate R, G, and B variables.
    R, G, B = load_RGB_channels(C, (13, 8, 10))

    # Normalize each channel by the appropriate range of values. e.g. R = (R-minimum)/(maximum-minimum)
    R = normalize(R, -70.86, 5.81)
    G = normalize(G, -58.49, -30.48)
    B = normalize(B, -28.03, -12.12)

    # Invert the colors
    R = 1-R
    G = 1-G
    B = 1-B

    # The final RGB array :)
    RGB = np.dstack([R, G, B])
    
    return rgb_as_dataset(C, RGB, 'Water Vapor', **kwargs)


def DifferentialWaterVapor(C, **kwargs):
    """
    Differential Water Vapor RGB:
    http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_DifferentialWaterVaporRGB_final.pdf
    """
    # Load the three channels into appropriate R, G, and B variables.
    R = C['CMI_C10'].data - C['CMI_C08'].data
    G = C['CMI_C10'].data - 273.15
    B = C['CMI_C08'].data - 273.15

    # Normalize each channel by the appropriate range of values. e.g. R = (R-minimum)/(maximum-minimum)
    R = normalize(R, -3, 30)
    G = normalize(G, -60, 5)
    B = normalize(B, -64.65, -29.25)

    # Gamma correction
    R = np.power(R, 1/0.2587)
    G = np.power(G, 1/0.4)
    B = np.power(B, 1/0.4)

    # Invert the colors
    R = 1-R
    G = 1-G
    B = 1-B

    # The final RGB array :)
    RGB = np.dstack([R, G, B])
    
    return rgb_as_dataset(C, RGB, 'Differenctial Water Vapor', **kwargs)


def DaySnowFog(C, **kwargs):
    """
    Day Snow-Fog RGB:
    http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_DaySnowFog.pdf
    """
    # Load the three channels into appropriate R, G, and B variables
    R = C['CMI_C03'].data 
    G = C['CMI_C05'].data
    B = C['CMI_C07'].data - C['CMI_C13'].data

    # Normalize values    
    R = normalize(R, 0, 1)
    G = normalize(G, 0, 0.7)
    B = normalize(B, 0, 30)

    # Apply a gamma correction to the image
    gamma = 1.7
    R = np.power(R, 1/gamma)
    G = np.power(G, 1/gamma)
    B = np.power(B, 1/gamma)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])
    
    return rgb_as_dataset(C, RGB, 'Day Snow Fog', **kwargs)


def NighttimeMicrophysics(C, **kwargs):
    """
    Nighttime Microphysics RGB:
    http://rammb.cira.colostate.edu/training/visit/quick_guides/QuickGuide_GOESR_NtMicroRGB_final.pdf
    """
    # Load the three channels into appropriate R, G, and B variables
    R = C['CMI_C15'].data - C['CMI_C13'].data
    G = C['CMI_C13'].data - C['CMI_C07'].data
    B = C['CMI_C13'].data - 273.15

    # Normalize values    
    R = normalize(R, -6.7, 2.6)
    G = normalize(G, -3.1, 5.2)
    B = normalize(B, -29.6, 19.5)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])
    
    return rgb_as_dataset(C, RGB, 'Nighttime Microphysics', **kwargs)


def Dust(C, **kwargs):
    """
    SulfurDioxide RGB:
    http://rammb.cira.colostate.edu/training/visit/quick_guides/Dust_RGB_Quick_Guide.pdf
    """
    # Load the three channels into appropriate R, G, and B variables
    R = C['CMI_C15'].data - C['CMI_C13'].data
    G = C['CMI_C14'].data - C['CMI_C11'].data
    B = C['CMI_C13'].data - 273.15

    # Normalize values    
    R = normalize(R, -6.7, 2.6)
    G = normalize(G, -0.5, 20)
    B = normalize(B, -11.95, 15.55)

    # Apply a gamma correction to the image
    gamma = 2.5
    G = np.power(G, 1/gamma)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])
    
    return rgb_as_dataset(C, RGB, 'Dust', **kwargs)

def SulfurDioxide(C, **kwargs):
    """
    SulfurDioxide RGB:
    http://rammb.cira.colostate.edu/training/visit/quick_guides/Quick_Guide_SO2_RGB.pdf
    """
    # Load the three channels into appropriate R, G, and B variables
    R = C['CMI_C09'].data - C['CMI_C10'].data
    G = C['CMI_C13'].data - C['CMI_C11'].data
    B = C['CMI_C07'].data - 273.15

    # Normalize values    
    R = normalize(R, -4, 2)
    G = normalize(G, -4, 5)
    B = normalize(B, -30.1, 29.8)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])
    
    return rgb_as_dataset(C, RGB, 'Sulfur Dioxide', **kwargs)


def Ash(C, **kwargs):
    """
    Ash RGB:
    http://rammb.cira.colostate.edu/training/visit/quick_guides/GOES_Ash_RGB.pdf
    """
    # Load the three channels into appropriate R, G, and B variables
    R = C['CMI_C15'].data - C['CMI_C13'].data
    G = C['CMI_C14'].data - C['CMI_C11'].data
    B = C['CMI_C13'].data - 273.15

    # Normalize values    
    R = normalize(R, -6.7, 2.6)
    G = normalize(G, -6, 6.3)
    B = normalize(B, -29.55, 29.25)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])
    
    return rgb_as_dataset(C, RGB, 'Ash', **kwargs)


def SplitWindowDifference(C, **kwargs):
    """
    Split Window Difference RGB (greyscale):
    http://cimss.ssec.wisc.edu/goes/OCLOFactSheetPDFs/ABIQuickGuide_SplitWindowDifference.pdf
    """
    # Load the three channels into appropriate R, G, and B variables
    data = C['CMI_C15'].data - C['CMI_C13'].data

    # Normalize values    
    data = normalize(data, -10, 10)

    # The final RGB array :)
    RGB = np.dstack([data, data, data])
        
    return rgb_as_dataset(C, RGB, 'Split Window Difference', **kwargs)


def NightFogDifference(C, **kwargs):
    """
    Night Fog Difference RGB (greyscale):
    http://cimss.ssec.wisc.edu/goes/OCLOFactSheetPDFs/ABIQuickGuide_NightFogBTD.pdf
    """
    # Load the three channels into appropriate R, G, and B variables
    data = C['CMI_C13'].data - C['CMI_C07'].data

    # Normalize values    
    data = normalize(data, -90, 15)
    
    # Invert data
    data = 1-data

    # The final RGB array :)
    RGB = np.dstack([data, data, data])
    
    return rgb_as_dataset(C, RGB, 'Night Fog Difference', **kwargs)