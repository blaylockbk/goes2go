## Brian Blaylock
## July 8, 2021

import warnings
import toml
from pathlib import Path
import os

########################################################################
# Load custom xarray accessors
# TODO: In the future, I may develop some xarray accessors
#try:
#    import goes2go.accessors
#except:
#    warnings.warn("goes2go xarray accessors could not be imported.")
#    pass

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
_config_path = Path('~/.config/goes2go/config.toml').expand()

########################################################################
# Default TOML Configuration
default_toml = f"""
['default']
save_dir = "{str(Path('~/data').expand())}"
satellite = "noaa-goes16"
product = "ABI-L2-MCMIP"
domain = "C"
download = true
return_as = "filelist"
overwrite = false
max_cpus = 1
s3_refresh = true
verbose = true

['timerange']
s3_refresh = false

['latest']
return_as = "xarray"

['nearesttime']
within = "1H"
return_as = "xarray"
"""

########################################################################
# If a config file isn't found, make one
if not _config_path.exists():
    with open(_config_path, 'w') as f:
        toml_string = toml.dump(toml.loads(default_toml), f)
    print(f'⚙ Created config file [{_config_path}] with default values.')

########################################################################
# Read the config file
config = toml.load(_config_path)

config['default']['save_dir'] = Path(config['default']['save_dir']).expand()

# Merge default settings with overwrite settings for each download method
for i in ['timerange', 'latest', 'nearesttime']:
    config[i] = {**config['default'], **config[i]}
