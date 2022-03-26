## Brian Blaylock
## September 16, 2020

"""
=============
Retrieve Data
=============
Download and read data from the R-series Geostationary Operational
Environmental Satellite data.

Data is downloaded from Amazon Web Services and can be returned
as a file list or read as an xarray.Dataset. If the data is not
available in a local directory, it is loaded directly into memory.

https://registry.opendata.aws/noaa-goes/
"""

from pathlib import Path
from datetime import datetime, timedelta
import multiprocessing

import s3fs
import xarray as xr
import pandas as pd
import numpy as np

# NOTE: These config dict values are retrieved from __init__ and read
# from the file ${HOME}/.config/goes2go/config.toml
from . import config

# Connect to AWS public buckets
fs = s3fs.S3FileSystem(anon=True)

# Define parameter options and aliases
# ------------------------------------
_satellite = {
    "noaa-goes16": [16, "16", "G16", "EAST", "GOES16"],
    "noaa-goes17": [17, "17", "G17", "WEST", "GOES17"],
    "noaa-goes18": [18, "18", "G18", "WEST", "GOES18"],
}

_domain = {
    "C": ["CONUS"],
    "F": ["FULL", "FULLDISK", "FULL DISK"],
    "M": ["MESOSCALE", "M1", "M2"],
}

_product = {
    # Assume goes17 and goes18 have same products as goes16
    i.split("/")[-1]: []
    for i in fs.ls(f"noaa-goes16")
}
_product.pop("index.html", None)
_product["GLM-L2-LCFA"] = ["GLM"]
_product["ABI-L2-MCMIPC"] = ["ABIC"]
_product["ABI-L2-MCMIPF"] = ["ABIF"]
_product["ABI-L2-MCMIPM"] = ["ABIM"]


def _check_param_inputs(**params):
    """
    Checks the input parameters for correct name or alias.

    Specifically, check the input for product, domain, and satellite are
    in the list of accepted values. If not, then look if it has an alias.
    """
    # Kinda messy, but gets the job done.
    params.setdefault("verbose", True)
    satellite = params["satellite"]
    domain = params["domain"]
    product = params["product"]
    verbose = params["verbose"]

    ## Determine the Satellite
    if satellite not in _satellite:
        satellite = str(satellite).upper()
        for key, aliases in _satellite.items():
            if satellite in aliases:
                satellite = key
    assert (
        satellite in _satellite
    ), f"satellite must be one of {list(_satellite.keys())} or an alias {list(_satellite.values())}"

    ## Determine the Domain (only needed for ABI product)
    if product.upper().startswith("ABI"):
        if product[-1] in _domain:
            # If the product has the domain, this takes priority
            domain = product[-1]
        elif isinstance(domain, str):
            domain = domain.upper()
            if domain in ["M1", "M2"]:
                product = product + "M"
            else:
                for key, aliases in _domain.items():
                    if domain in aliases:
                        domain = key
                product = product + domain
        assert (domain in _domain) or (
            domain in ["M1", "M2"]
        ), f"domain must be one of {list(_domain.keys())} or an alias {list(_domain.values())}"
    else:
        domain = None

    ## Determine the Product
    if product not in _product:
        for key, aliases in _product.items():
            if product.upper() in aliases:
                product = key
    assert (
        product in _product
    ), f"product must be one of {list(_product .keys())} or an alias {list(_product .values())}"

    if verbose:
        print(f" _______________________________")
        print(f" | Satellite: {satellite:<17s}|")
        print(f" |   Product: {product:<17s}|")
        if domain != None:
            print(f" |    Domain: {domain:<17s}|")

    return satellite, product, domain


def _goes_file_df(satellite, product, start, end, refresh=True):
    """
    Get list of requested GOES files as pandas.DataFrame.

    Parameters
    ----------
    satellite : str
    product : str
    start : datetime
    end : datetime
    refresh : bool
        Refresh the s3fs.S3FileSystem object when files are listed.
        Default True will refresh and not use a cached list.
    """
    params = locals()

    DATES = pd.date_range(f"{start:%Y-%m-%d %H:00}", f"{end:%Y-%m-%d %H:00}", freq="1H")

    # List all files for each date
    # ----------------------------
    files = []
    for DATE in DATES:
        files += fs.ls(f"{satellite}/{product}/{DATE:%Y/%j/%H/}", refresh=refresh)

    # Build a table of the files
    # --------------------------
    df = pd.DataFrame(files, columns=["file"])
    df[["start", "end", "creation"]] = (
        df["file"].str.rsplit("_", expand=True, n=3).loc[:, 1:]
    )

    # Filter files by requested time range
    # ------------------------------------
    # Convert filename datetime string to datetime object
    df["start"] = pd.to_datetime(df.start, format="s%Y%j%H%M%S%f")
    df["end"] = pd.to_datetime(df.end, format="e%Y%j%H%M%S%f")
    df["creation"] = pd.to_datetime(df.creation, format="c%Y%j%H%M%S%f.nc")

    # Filter by files within the requested time range
    df = df.loc[df.start >= start].loc[df.end <= end].reset_index(drop=True)

    for i in params:
        df.attrs[i] = params[i]

    return df


def _download_MP(src, save_dir, overwrite, i=1, n=1, verbose=True):
    """
    Download a single file -- a multiprocessing helper

    Parameters
    ----------
    src : str
        The source path of the file (path relative to S3 or ``save_dir``)
    save_dir : str or pathlib.Path
        Directory to save the file when it is downloaded.
    overwrite : bool
        True - overwrite files if the exist
        False - skip download if the file exists (default)
    i, n : int
        The iteration number and total number of files (primarily for
        the multiprocessor counter).
    """

    # File destination
    dst = Path(save_dir) / src

    if not dst.parent.is_dir():
        dst.parent.mkdir(parents=True, exist_ok=True)
        print(f"👨🏻‍🏭 Created directory: [{dst.parent}]", end="")

    if verbose:
        print(
            f"\r🏇🏻💨 Downloading ({i:,}/{n:,}) file from AWS to Local Disk. {src} > {dst}",
            end=" ",
        )

    if dst.is_file() and not overwrite:
        if verbose:
            print("---- 👮🏻‍♂️ File already exists. Do not overwrite.", end="")
    else:
        # Downloading file from AWS
        # NOTE: The destination is `str(dst)` and not just `dst` because
        #       Gaffney does not like a Path object for some reason.
        fs.get(src, str(dst))


def _download(df, **params):
    """
    Download each file in the pandas.DataFrame to ``save_dir``.

    Use multiprocessing to improve download time.

    Parameters
    ----------
    df : pandas.DataFrame
        A DataFrame created by ``_goes_file_df`` with a list of files
        to download from the GOES s3 bucket.
    save_dir : str or pathlib.Path
        Directory the files will be downloaded to.
        The default location (set as a variable in this script)
        is ``~/data/``.
    max_cpus : int or None
        If None, use all available CPUs. Else, specify the number of
        CPUs to use.
    overwrite : bool
        True - overwrite files if the exist
        False - skip download if the file exists (default)
    """
    params.setdefault("max_cpus", None)
    params.setdefault("verbose", True)
    save_dir = params["save_dir"]
    overwrite = params["overwrite"]
    max_cpus = params["max_cpus"]
    verbose = params["verbose"]

    n = len(df.file)
    if n == 0:
        print("🛸 No data to download.")
    elif n == 1:
        # If we only have one file, we don't need multiprocessing
        _download_MP(df.file[0], save_dir, overwrite, 1, 1, verbose)
    elif max_cpus == 1:
        [_download_MP(df.file[i], save_dir, overwrite, i, n, verbose) for i in range(n)]
    else:
        # Use Multiprocessing to download multiple files.
        if max_cpus is None:
            max_cpus = multiprocessing.cpu_count()
        cpus = np.minimum(multiprocessing.cpu_count(), max_cpus)
        cpus = np.minimum(cpus, n)

        inputs = [
            (src, save_dir, overwrite, i, n, verbose)
            for i, src in enumerate(df.file, start=1)
        ]

        with multiprocessing.Pool(cpus) as p:
            results = p.starmap(_download_MP, inputs)
            p.close()
            p.join()
    if verbose:
        print(
            f"\r{'':1000}\r📦 Finished downloading [{n}] files to [{save_dir/Path(df.file[0]).parents[3]}]."
        )


def _as_xarray_MP(src, save_dir, i=None, n=None, verbose=True):
    """Open a file as a xarray.Dataset -- a multiprocessing helper"""

    # File destination
    local_copy = Path(save_dir) / src

    if local_copy.is_file():
        if verbose:
            print(
                f"\r📖💽 Reading ({i:,}/{n:,}) file from LOCAL COPY [{local_copy}].",
                end=" ",
            )
        ds = xr.open_dataset(local_copy)
    else:
        if verbose:
            print(
                f"\r📖☁ Reading ({i:,}/{n:,}) file from AWS to MEMORY [{src}].", end=" "
            )
        with fs.open(src, "rb") as f:
            ds = xr.open_dataset(f).copy(deep=True)

    # Turn some attributes to coordinates so they will be preserved
    # when we concat multiple GOES DataSets together.
    attr2coord = [
        "dataset_name",
        "date_created",
        "time_coverage_start",
        "time_coverage_end",
    ]
    for i in attr2coord:
        if i in ds.attrs:
            ds.coords[i] = ds.attrs.pop(i)

    ds["filename"] = src

    return ds


def _as_xarray(df, **params):
    """
    Download files in the list to the desired path.

    Use multiprocessing to speed up the download process.

    Parameters
    ----------
    df : pandas.DataFrame
        A list of files in the GOES s3 bucket.
        This DataFrame must have a column of "files"
    params : dict
        Parameters from `goes_*` function.
    """
    params.setdefault("max_cpus", None)
    params.setdefault("verbose", True)
    save_dir = params["save_dir"]
    max_cpus = params["max_cpus"]
    verbose = params["verbose"]

    n = len(df.file)
    if n == 0:
        print("🛸 No data....🌌")
    elif n == 1:
        # If we only have one file, we don't need multiprocessing
        ds = _as_xarray_MP(df.iloc[0].file, save_dir, 1, 1, verbose)
    else:
        # Use Multiprocessing to read multiple files.
        if max_cpus is None:
            max_cpus = multiprocessing.cpu_count()
        cpus = np.minimum(multiprocessing.cpu_count(), max_cpus)
        cpus = np.minimum(cpus, n)

        inputs = [(src, save_dir, i, n) for i, src in enumerate(df.file, start=1)]

        with multiprocessing.Pool(cpus) as p:
            results = p.starmap(_as_xarray_MP, inputs)
            p.close()
            p.join()

        # Need some work to concat the datasets
        if df.attrs["product"].startswith("ABI"):
            print("concatenate Datasets", end="")
            ds = xr.concat(results, dim="t")
        else:
            ds = results

    if verbose:
        print(f"\r{'':1000}\r📚 Finished reading [{n}] files into xarray.Dataset.")
    ds.attrs["path"] = df.file.to_list()
    return ds


###############################################################################
###############################################################################


def goes_timerange(
    start=None,
    end=None,
    recent=None,
    *,
    satellite=config["timerange"].get("satellite"),
    product=config["timerange"].get("product"),
    domain=config["timerange"].get("domain"),
    return_as=config["timerange"].get("return_as"),
    download=config["timerange"].get("download"),
    overwrite=config["timerange"].get("overwrite"),
    save_dir=config["timerange"].get("save_dir"),
    max_cpus=config["timerange"].get("max_cpus"),
    s3_refresh=config["timerange"].get("s3_refresh"),
    verbose=config["timerange"].get("verbose", True),
):
    """
    Get GOES data for a time range.

    Parameters
    ----------
    start, end : datetime
        Required if recent is None.
    recent : timedelta or pandas-parsable timedelta str
        Required if start and end are None. If timedelta(hours=1), will
        get the most recent files for the past hour.
    satellite : {'goes16', 'goes17', 'goes18'}
        Specify which GOES satellite.
        The following alias may also be used:

        - ``'goes16'``: 16, 'G16', or 'EAST'
        - ``'goes17'``: 17, 'G17', or 'WEST'
        - ``'goes18'``: 18, 'G18', or 'WEST'

    product : {'ABI', 'GLM', other GOES product}
        Specify the product name.

        - 'ABI' is an alias for ABI-L2-MCMIP Multichannel Cloud and Moisture Imagery
        - 'GLM' is an alias for GLM-L2-LCFA Geostationary Lightning Mapper

        Others may include ``'ABI-L1b-Rad'``, ``'ABI-L2-DMW'``, etc.
        For more available products, look at this `README
        <https://docs.opendata.aws/noaa-goes16/cics-readme.html>`_
    domain : {'C', 'F', 'M'}
        ABI scan region indicator. Only required for ABI products if the
        given product does not end with C, F, or M.

        - C: Contiguous United States (alias 'CONUS')
        - F: Full Disk (alias 'FULL')
        - M: Mesoscale (alias 'MESOSCALE')

    return_as : {'xarray', 'filelist'}
        Return the data as an xarray.Dataset or as a list of files
    download : bool
        - True: Download the data to disk to the location set by :guilabel:`save_dir`
        - False: Just load the data into memory.
    save_dir : pathlib.Path or str
        Path to save the data.
    overwrite : bool
        - True: Download the file even if it exists.
        - False Do not download the file if it already exists
    max_cpus : int
    s3_refresh : bool
        Refresh the s3fs.S3FileSystem object when files are listed.

    """
    # If `start`, or `end` is a string, parse with Pandas
    if isinstance(start, str):
        start = pd.to_datetime(start)
    if isinstance(end, str):
        end = pd.to_datetime(end)
    # If `recent` is a string (like recent='1H'), parse with Pandas
    if isinstance(recent, str):
        recent = pd.to_timedelta(recent)

    params = locals()
    satellite, product, domain = _check_param_inputs(**params)
    params["satellite"] = satellite
    params["product"] = product
    params["domain"] = domain

    check1 = start is not None and end is not None
    check2 = recent is not None
    assert check1 or check2, "🤔 `start` and `end` *or* `recent` is required"

    if check1:
        assert hasattr(start, "second") and hasattr(
            end, "second"
        ), "`start` and `end` must be a datetime object"
    elif check2:
        assert hasattr(recent, "seconds"), "`recent` must be a timedelta object"

    # Parameter Setup
    # ---------------
    # Create a range of directories to check. The GOES S3 bucket is
    # organized by hour of day.
    if recent is not None:
        start = datetime.utcnow() - recent
        end = datetime.utcnow()

    df = _goes_file_df(satellite, product, start, end, refresh=s3_refresh)

    if download:
        _download(df, **params)

    if return_as == "filelist":
        df.attrs["filePath"] = save_dir
        return df
    elif return_as == "xarray":
        return _as_xarray(df, **params)


def goes_latest(
    *,
    satellite=config["latest"].get("satellite"),
    product=config["latest"].get("product"),
    domain=config["latest"].get("domain"),
    return_as=config["latest"].get("return_as"),
    download=config["latest"].get("download"),
    overwrite=config["latest"].get("overwrite"),
    save_dir=config["latest"].get("save_dir"),
    s3_refresh=config["latest"].get("s3_refresh"),
    verbose=config["latest"].get("verbose", True),
):
    """
    Get the latest available GOES data.

    Parameters
    ----------
    satellite : {'goes16', 'goes17', 'goes18'}
        Specify which GOES satellite.
        The following alias may also be used:

        - ``'goes16'``: 16, 'G16', or 'EAST'
        - ``'goes17'``: 17, 'G17', or 'WEST'
        - ``'goes18'``: 18, 'G18', or 'WEST'

    product : {'ABI', 'GLM', other GOES product}
        Specify the product name.

        - 'ABI' is an alias for ABI-L2-MCMIP Multichannel Cloud and Moisture Imagery
        - 'GLM' is an alias for GLM-L2-LCFA Geostationary Lightning Mapper

        Others may include ``'ABI-L1b-Rad'``, ``'ABI-L2-DMW'``, etc.
        For more available products, look at this `README
        <https://docs.opendata.aws/noaa-goes16/cics-readme.html>`_
    domain : {'C', 'F', 'M'}
        ABI scan region indicator. Only required for ABI products if the
        given product does not end with C, F, or M.

        - C: Contiguous United States (alias 'CONUS')
        - F: Full Disk (alias 'FULL')
        - M: Mesoscale (alias 'MESOSCALE')

    return_as : {'xarray', 'filelist'}
        Return the data as an xarray.Dataset or as a list of files
    download : bool
        - True: Download the data to disk to the location set by :guilabel:`save_dir`
        - False: Just load the data into memory.
    save_dir : pathlib.Path or str
        Path to save the data.
    overwrite : bool
        - True: Download the file even if it exists.
        - False Do not download the file if it already exists
    s3_refresh : bool
        Refresh the s3fs.S3FileSystem object when files are listed.
    """
    params = locals()
    satellite, product, domain = _check_param_inputs(**params)
    params["satellite"] = satellite
    params["product"] = product
    params["domain"] = domain

    # Parameter Setup
    # ---------------
    # Create a range of directories to check. The GOES S3 bucket is
    # organized by hour of day. Look in the current hour and last hour.
    start = datetime.utcnow() - timedelta(hours=1)
    end = datetime.utcnow()

    df = _goes_file_df(satellite, product, start, end, refresh=s3_refresh)

    # Filter for specific mesoscale domain
    if domain is not None and domain.upper() in ["M1", "M2"]:
        df = df[df["file"].str.contains(f"{domain.upper()}-M")]

    # Get the most recent file (latest start date)
    df = df.loc[df.start == df.start.max()].reset_index(drop=True)

    if download:
        _download(df, **params)

    if return_as == "filelist":
        df.attrs["filePath"] = save_dir
        return df
    elif return_as == "xarray":
        return _as_xarray(df, **params)


def goes_nearesttime(
    attime,
    within=pd.to_timedelta(config["nearesttime"].get("within", "1H")),
    *,
    satellite=config["nearesttime"].get("satellite"),
    product=config["nearesttime"].get("product"),
    domain=config["nearesttime"].get("domain"),
    return_as=config["nearesttime"].get("return_as"),
    download=config["nearesttime"].get("download"),
    overwrite=config["nearesttime"].get("overwrite"),
    save_dir=config["nearesttime"].get("save_dir"),
    s3_refresh=config["nearesttime"].get("s3_refresh"),
    verbose=config["nearesttime"].get("verbose", True),
):
    """
    Get the latest available GOES data.

    Parameters
    ----------
    attime : datetime
        Time to find the nearest observation for.
        May also use a pandas-interpretable datetime string.
    within : timedelta or pandas-parsable timedelta str
        Timerange tht the nearest observation must be.
    satellite : {'goes16', 'goes17', 'goes18'}
        Specify which GOES satellite.
        The following alias may also be used:

        - ``'goes16'``: 16, 'G16', or 'EAST'
        - ``'goes17'``: 17, 'G17', or 'WEST'
        - ``'goes18'``: 18, 'G18', or 'WEST'

    product : {'ABI', 'GLM', other GOES product}
        Specify the product name.

        - 'ABI' is an alias for ABI-L2-MCMIP Multichannel Cloud and Moisture Imagery
        - 'GLM' is an alias for GLM-L2-LCFA Geostationary Lightning Mapper

        Others may include ``'ABI-L1b-Rad'``, ``'ABI-L2-DMW'``, etc.
        For more available products, look at this `README
        <https://docs.opendata.aws/noaa-goes16/cics-readme.html>`_
    domain : {'C', 'F', 'M'}
        ABI scan region indicator. Only required for ABI products if the
        given product does not end with C, F, or M.

        - C: Contiguous United States (alias 'CONUS')
        - F: Full Disk (alias 'FULL')
        - M: Mesoscale (alias 'MESOSCALE')

    return_as : {'xarray', 'filelist'}
        Return the data as an xarray.Dataset or as a list of files
    download : bool
        - True: Download the data to disk to the location set by :guilabel:`save_dir`
        - False: Just load the data into memory.
    save_dir : pathlib.Path or str
        Path to save the data.
    overwrite : bool
        - True: Download the file even if it exists.
        - False: Do not download the file if it already exists
    s3_refresh : bool
        Refresh the s3fs.S3FileSystem object when files are listed.
    """
    if isinstance(attime, str):
        attime = pd.to_datetime(attime)
    if isinstance(within, str):
        within = pd.to_timedelta(within)

    params = locals()
    satellite, product, _ = _check_param_inputs(**params)
    params["satellite"] = satellite
    params["product"] = product

    # Parameter Setup
    # ---------------
    # Create a range of directories to check. The GOES S3 bucket is
    # organized by hour of day.
    start = attime - within
    end = attime + within

    df = _goes_file_df(satellite, product, start, end, refresh=s3_refresh)

    # return df, start, end, attime

    # Filter for specific mesoscale domain
    if domain.upper() in ["M1", "M2"]:
        df = df[df["file"].str.contains(f"{domain.upper()}-M")]

    # Get row that matches the nearest time
    df = df.sort_values("start")
    df = df.set_index(df.start)
    nearest_time_index = df.index.get_indexer([attime], method='nearest')
    df = df.iloc[nearest_time_index]
    df = df.reset_index(drop=True)

    n = len(df.file)
    if n == 0:
        print("🛸 No data....🌌")
        return None

    if download:
        _download(df, **params)

    if return_as == "filelist":
        df.attrs["filePath"] = save_dir
        return df
    elif return_as == "xarray":
        return _as_xarray(df, **params)
