import time
import sys

import toml
from toml import TomlDecodeError


def get_utc_offset():
    # Calculate UTC offset
    utc_offset = time.timezone if (time.localtime().tm_isdst == 0) else time.altzone
    # utc_offset = (utc_offset / 3600)
    return utc_offset


class Configuration:
    config: dict

    def __init__(self, config_path: str):
        try:
            self.config = toml.load(config_path)
        except TomlDecodeError as err:
            print(f"An error occurred while parsing {config_path}: ", err)
            sys.exit(1)  # Refactor

        # Set timezone offset
        self.config["utc_offset"] = get_utc_offset()

        if "use_servertime" not in self.config:
            self.config["use_servertime"] = True
 
    def get_value(self, key: str):
        if key in self.config:
            return self.config[key]
        else:
            raise TypeError(f"requested key: {key} not in configuration")
