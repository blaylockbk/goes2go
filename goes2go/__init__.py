## Brian Blaylock
## July 8, 2021

import warnings
import configparser
from pathlib import Path

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
# Configure goes2go
# Configuration file is save in `~/config/goes2go/config.cfg`
# `_default_save_dir` is the default path to save NetCDF files.
config = configparser.ConfigParser()
_config_path = Path('~/.config/goes2go/config.cfg').expand()

########################################################################
# Default Configuration Values
defaults = dict(
    data_dir = str(Path('~/data').expand()),
)

########################################################################
# If a config file isn't found, make one
if not _config_path.exists():
    _config_path.parent.mkdir(parents=True)
    _config_path.touch()
    config.read(_config_path)
    config.add_section('download')
    config.set('download', 'default_save_dir', defaults["data_dir"])
    with open(_config_path, 'w') as configfile:
        config.write(configfile)
    print(f'⚙ Created config file [{_config_path}]',
          f'with default download directory set as [{defaults["data_dir"]}]')

########################################################################
# Read the config file
config.read(_config_path)

try:
    _default_save_dir = Path(config.get('download', 'default_save_dir'))
except:
    print(f'🦁🐯🐻 oh my! {_config_path} looks weird,',
          f'but I will add new settings')
    try:
        config.add_section('download')
    except:
        pass  # section already exists
    config.set('download', 'default_save_dir', defaults["data_dir"])
    with open(_config_path, 'w') as configfile:
        config.write(configfile)
    _default_save_dir = Path(config.get('download', 'default_save_dir'))