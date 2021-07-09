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
# Configure goes2go
# Configuration file is save in `~/config/goes2go/config.cfg`
# `_default_save_dir` is the default path to save NetCDF files.

config = configparser.ConfigParser()
_config_path = Path('~').expanduser() / '.config' / 'goes2go' / 'config.cfg'

user_home_default = str(Path('~').expanduser() / 'data')

if not _config_path.exists():
    _config_path.parent.mkdir(parents=True)
    _config_path.touch()
    config.read(_config_path)
    config.add_section('download')
    config.set('download', 'default_save_dir', user_home_default)
    with open(_config_path, 'w') as configfile:
        config.write(configfile)
    print(f'⚙ Created config file [{_config_path}]',
          f'with default download directory set as [{user_home_default}]')

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
    config.set('download', 'default_save_dir', user_home_default)
    with open(_config_path, 'w') as configfile:
        config.write(configfile)
    _default_save_dir = Path(config.get('download', 'default_save_dir'))