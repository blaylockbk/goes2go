=======================
⚙ Configure Defaults
=======================

The first time you import goes2go, it creates a configure file

.. code-block:: bash

    ~/.config/goes2go/config.toml


In this file, you may set the default arguments for the download functions.
The default is

.. code-block::

    [default]
    save_dir = "~/data"
    satellite = "noaa-goes16"
    product = "ABI-L2-MCMIP"
    domain = "C"
    download = true
    return_as = "filelist"
    overwrite = false
    max_cpus = 1
    s3_refresh = true
    verbose = true

    [timerange]
    s3_refresh = false

    [latest]
    return_as = "xarray"

    [nearesttime]
    within = "1h"
    return_as = "xarray"

The ``[default]`` section are global settings used by each download method. These can be overwritten for each method. For instance, *s3_refresh* is set to false for ``[timerange]`` because it's unlikely you will need to refresh the file listing. Also, ``[latest]`` and ``[nearesttime]`` are by default returned as an xarray object instead of a list of files downloaded.

save_dir
    Path to save the downloaded data.

satellite
    Specify which GOES satellite to get data from. ``'noaa-goes16'`` or ``'noaa-goes17'``
    The following alias may also be used: 

    - ``'goes16'``: 16, 'G16', or 'EAST'
    - ``'goes17'``: 17, 'G17', or 'WEST'

product
    Specify the product name. `List of Products <https://docs.opendata.aws/noaa-goes16/cics-readme.html>`_

    - 'ABI' is an alias for ABI-L2-MCMIP Multichannel Cloud and Moisture Imagery
    - 'GLM' is an alias for GLM-L2-LCFA Geostationary Lightning Mapper
    
domain
    ABI scan region indicator. Only required for ABI products if the
    given product does not end with C, F, or M.

    - C: Contiguous United States (alias 'CONUS')
    - F: Full Disk (alias 'FULL')
    - M: Mesoscale (alias 'MESOSCALE')

download
    - true: Download the data to disk to the location set by ``save_dir``
    - false: Load the data into memory (slower).
    
return_as
    Return the data as an xarray.Dataset with ``"xarray"``, or as a list of files with ``"filelist"``.

overwrite
    - true: Download the file even if it exists.
    - false: Do not download the file if it already exists

max_cpus
    Number of cpus to use to download files. Using more CPUs can increase speed when downloading many files in a timeseries. ONLY USED IN ``[timeseries]``.

within
    Period of time to consider when downloading ``[latest]`` file.

s3_refresh
    Refresh the s3fs.S3FileSystem object when files are listed.

verbose
    - true: Print info to screen.
    - false: don't print info to screen.