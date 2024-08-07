## Brian Blaylock
## July 8, 2021

import os
import warnings
from pathlib import Path

__author__ = "Brian K. Blaylock"


try:
    ## TODO: Will the `_version.py` file *always* be present?
    ## TODO: What if the person doesn't do "pip install"
    from ._version import __version__, __version_tuple__
except:
    __version__ = "unknown"
    __version_tuple__ = (999, 999, 999)


import toml

# =======================================================================
# Load custom xarray accessors
# TODO: Move some of the tools.py to these accessors.
try:
    import goes2go.accessors
except Exception:
    warnings.warn("goes2go xarray accessors could not be imported.")


# =======================================================================
# Overload Path object with my custom `expand` method so the user can
# set environment variables in the config file (e.g., ${HOME}).
def _expand(self):
    """
    Fully expand and resolve the Path with the given environment variables.

    Example
    -------
    >>> Path('$HOME').expand()
    PosixPath('/p/home/blaylock')
    """
    return Path(os.path.expandvars(self)).expanduser().resolve()


Path.expand = _expand

# =======================================================================
# Location of goes2go configuration file
_config_path = os.getenv("GOES2GO_CONFIG_PATH", "~/.config/goes2go")
_config_path = Path(_config_path).expand()
_config_file = _config_path / "config.toml"

# Default directory goes2go saves model output
# NOTE: The `\\` is an escape character in TOML.
#       For Windows paths, "C:\\user\\"" needs to be "C:\\\\user\\\\""
_save_dir = os.getenv("GOES2GO_SAVE_DIR", "~/data")
_save_dir = Path(_save_dir).expand()
_save_dir = str(_save_dir).replace("\\", "\\\\")

# =======================================================================
# Default TOML Configuration
default_toml = f""" # GOES-2-go Defaults
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
within = "1h"
return_as = "xarray"
"""

########################################################################
# Load config file (create one if needed)
try:
    # Load the goes2go config file
    config = toml.load(_config_file)
except Exception:
    try:
        # Create the goes2go config file
        _config_path.mkdir(parents=True, exist_ok=True)
        with open(_config_file, "w", encoding="utf-8") as f:
            f.write(default_toml)

        print(
            f" ╭─goes2go──────────────────────────────────────────────╮\n"
            f" │ INFO: Created a default config file.                 │\n"
            f" │ You may view/edit goes2go's configuration here:      │\n"
            f" │ {str(_config_file):^53s}│\n"
            f" ╰──────────────────────────────────────────────────────╯\n"
        )

        # Load the new goes2go config file
        config = toml.load(_config_file)
    except (OSError, FileNotFoundError, PermissionError):
        print(
            f" ╭─goes2go─────────────────────────────────────────────╮\n"
            f" │ WARNING: Unable to create config file               │\n"
            f" │ {str(_config_file):^53s}│\n"
            f" │ goes2go will use standard default settings.         │\n"
            f" │ Consider setting env variable GOES2GO_CONFIG_PATH.  │\n"
            f" ╰─────────────────────────────────────────────────────╯\n"
        )
        config = toml.loads(default_toml)


# Expand the full path for `save_dir`
config["default"]["save_dir"] = Path(config["default"]["save_dir"]).expand()

if os.getenv("GOES2GO_SAVE_DIR"):
    config["default"]["save_dir"] = Path(os.getenv("GOES2GO_SAVE_DIR")).expand()
    print(
        f" ╭─goes2go──────────────────────────────────────────────╮\n"
        f" │ INFO: Overriding the configured save_dir because the │\n"
        f" │ environment variable GOES2GO_SAVE_DIR is set to      │\n"
        f" │ {os.getenv('GOES2GO_SAVE_DIR'):^53s}│\n"
        f" ╰──────────────────────────────────────────────────────╯\n"
    )

# Merge default settings with overwrite settings for each download method
for i in ["timerange", "latest", "nearesttime"]:
    config[i] = {**config["default"], **config[i]}


from goes2go.data import goes_latest, goes_nearesttime, goes_timerange
from goes2go.NEW import GOES
