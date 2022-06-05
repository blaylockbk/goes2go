## Brian Blaylock
## July 8, 2021

import warnings
import toml
from pathlib import Path
import os

########################################################################
# Load custom xarray accessors
# TODO: Move some of the tools.py to these accessors.
try:
    import goes2go.accessors
except:
    warnings.warn("goes2go xarray accessors could not be imported.")

########################################################################
# Append Path object with my custom expand method so user can use
# environment variables in the config file (e.g., ${HOME}).
def _expand(self):
    """
    Fully expand and resolve the Path with the given environment variables.

    Example
    -------
    >>> Path('$HOME').expand()
    >>> PosixPath('/p/home/blaylock')
    """
    return Path(os.path.expandvars(self)).expanduser().resolve()


Path.expand = _expand

########################################################################
# goes2go configuration file
# Configuration file is save in `~/config/goes2go/config.toml`
_config_path = Path("~/.config/goes2go/config.toml").expand()
_save_dir = str(Path("~/data").expand())

# NOTE: The `\\` is an escape character in TOML.
# For Windows paths "C:\\user\\"" needs to be "C:\\\\user\\\\""
_save_dir = str(Path("~/data").expand())
_save_dir = _save_dir.replace("\\", "\\\\")

########################################################################
# Default TOML Configuration
default_toml = f"""
["default"]
save_dir = "{_save_dir}"
satellite = "noaa-goes16"
product = "ABI-L2-MCMIP"
domain = "C"
download = true
return_as = "filelist"
overwrite = false
max_cpus = 1
s3_refresh = true
verbose = true

["timerange"]
s3_refresh = false

["latest"]
return_as = "xarray"

["nearesttime"]
within = "1H"
return_as = "xarray"
"""

########################################################################
# If a config file isn't found, make one
if not _config_path.exists():
    print(
        f" ╭─────────────────────────────────────────────────╮\n"
        f" │ I'm building goes2go's default config file.     │\n"
        f" ╰╥────────────────────────────────────────────────╯\n"
        f" 👷🏻‍♂️"
    )
    _config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(_config_path, "w") as f:
        toml_string = toml.dump(toml.loads(default_toml), f)
    print(f"⚙ Created config file [{_config_path}] with default values.")

########################################################################
# Read the config file
config = toml.load(_config_path)

config["default"]["save_dir"] = Path(config["default"]["save_dir"]).expand()

# Merge default settings with overwrite settings for each download method
for i in ["timerange", "latest", "nearesttime"]:
    config[i] = {**config["default"], **config[i]}


from goes2go.NEW import GOES
from goes2go.data import goes_nearesttime, goes_latest, goes_timerange
