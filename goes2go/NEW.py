## Brian Blaylock
## June 4, 2022

"""
==========
GOES Class
==========
"""

import itertools
import logging
import re

import numpy as np
import pandas as pd
import s3fs
import toml

from goes2go import config
from goes2go.data import _goes_file_df, goes_latest, goes_nearesttime, goes_timerange

log = logging.getLogger(__name__)

# Location of tables directory
from pathlib import Path

tables_dir = Path(__file__).parent

# Connect to AWS public buckets
fs = s3fs.S3FileSystem(anon=True)

product_table = pd.read_csv(
    tables_dir / "product_table.txt",
    skiprows=2,
    names=["product", "description"],
    index_col=0,
)
product_table.index = product_table.index.str.strip()
product_table["description"] = product_table.description.str.strip()


# Assume goes17 and goes18 have same products as goes16
_product = {i.split("/")[-1] for i in fs.ls(f"noaa-goes16")}
_product = set(filter(lambda x: x.split(".")[-1] not in ["pdf", "html"], _product))
_product

# you can be unspecific and request any mesoscale domain (M),
# or by number (M1, M2)
_domains = {"F", "C", "M", "M1", "M2"}


class GOES:
    def __init__(
        self,
        satellite=config["timerange"].get("satellite"),
        product=config["timerange"].get("product"),
        domain=config["timerange"].get("domain"),
        bands=None,
    ):
        """Initialize a GOES object for a desired satellite and product.

        Parameters
        ----------
        satellite : {16, 17, 18}
            The satellite number. May also use the following aliases
            {'G16', "G17", "EAST", "WEST"}
        product : str
            The product to aquire.
            - GLM = alias for geostationary lighting mapper
            - ABI = alias for ABI multi-channel cloud moisture imagery
        domain : {None, 'F', 'C', "M", "M1", "M2"}
            Only needed for ABI products.
            - F = Full Disk
            - C = CONUS
            - M = Mesoscale sector (both)
            - M1 = Mesoscale sector 1
            - M2 = Mesoscale sector 2
        band : None, int, or list
            Specify the ABI channels to retrieve. *Only used if the
            product requested requires it.*
        """
        self.satellite = satellite
        self.product = product
        self.domain = domain
        self.bands = bands

        self._check_satellite()
        self._check_product()

    def _check_satellite(self):
        if isinstance(self.satellite, int):
            self.satellite = f"noaa-goes{self.satellite}"
        elif isinstance(self.satellite, str):
            if self.satellite.upper() == "EAST":
                self.satellite = "noaa-goes16"
            elif self.satellite.upper() == "WEST":
                self.satellite = "noaa-goes17"
            else:
                # look for the satellite number in the string (i.e.g, 'G16', 'goes16')
                self.satellite = re.sub("[^0-9]", "", self.satellite)
                self.satellite = f"noaa-goes{self.satellite}"
        else:
            raise ValueError(
                f"Could not figure out what satellite you want from `{self.satellite}`"
            )

    def _check_product(self):
        if self.product == "GLM":
            # Alias for geostationary lighting mapper
            self.product = "GLM-L2-LCFA"
        elif self.product == "ABI":
            # Alias for multi-channel cloud moisture imagery
            if self.domain is None:
                self.product = "ABI-L2-MCMIP" + "C"
            else:
                self.product = "ABI-L2-MCMIP" + re.sub("[0-9]", "", self.domain)
        elif self.product.startswith("ABI"):
            if self.domain is None:
                if self.product[-1] in _domains:
                    self.domain = self.product[-1]

            elif self.domain is not None:
                if self.domain in _domains:
                    self.product = self.product + re.sub("[0-9]", "", self.domain)
                    if self.product not in _product:
                        raise ValueError(
                            f"{self.product} not a valid product product. Must one of {_domains}"
                        )
                else:
                    raise ValueError(
                        f"domain for ABI products must be None or one of {_domains}"
                    )
        else:
            if self.domain is not None:
                log.warning("domain argument is ignored for non-ABI products")

        if self.product in _product:
            self.description = product_table.loc[self.product].description
        else:
            raise ValueError(f"{self.product} is not an available product.")

    def __repr__(self):
        msg = [
            f"╭──────────────────────────",
            f"│ 🌎 GOES Object   ",
            f"│ ───────────────",
            f"│  {self.satellite=}",
            f"│  {self.product=}",
            f"│  {self.domain=}",
            f"│  {self.bands=}",
            f"│  {self.description=}",
            f"╰──────────────────────────",
        ]
        return "\n".join(msg)

    def latest(self, **kwargs):
        """Get the latest available GOES data."""
        return goes_latest(
            satellite=self.satellite, product=self.product, domain=self.domain, **kwargs
        )

    def nearesttime(
        self,
        attime,
        within=pd.to_timedelta(config["nearesttime"].get("within", "1H")),
        **kwargs,
    ):
        """Get the GOES data nearest a specified time.

        Parameters
        ----------
        attime : datetime
            Time to find the nearest observation for.
            May also use a pandas-interpretable datetime string.
        within : timedelta or pandas-parsable timedelta str
            Timerange tht the nearest observation must be.
        """
        return goes_nearesttime(
            attime,
            within,
            satellite=self.satellite,
            product=self.product,
            domain=self.domain,
            bands=self.bands,
            **kwargs,
        )

    def timerange(self, start=None, end=None, recent=None, **kwargs):
        """Get GOES data for a time range.

        Parameters
        ----------
        start, end : datetime
            Required if recent is None.
        recent : timedelta or pandas-parsable timedelta str
            Required if start and end are None. If timedelta(hours=1), will
            get the most recent files for the past hour.
        """
        return goes_timerange(
            start,
            end,
            recent,
            satellite=self.satellite,
            product=self.product,
            domain=self.domain,
            bands=self.bands,
            **kwargs,
        )

    def df(self, start, end, refresh=True):
        """Get list of requested GOES files as pandas.DataFrame.

        Parameters
        ----------
        start : datetime
        end : datetime
        refresh : bool
            Refresh the s3fs.S3FileSystem object when files are listed.
            Default True will refresh and not use a cached list.
        """
        return _goes_file_df(
            self.satellite,
            self.product,
            start=start,
            end=end,
            bands=self.bands,
            refresh=refresh,
        )
