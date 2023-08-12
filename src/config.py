import os
import sys
import time
from typing import Union, Dict

import toml


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
        except toml.TomlDecodeError as err:
            print(f"An error occurred while parsing {config_path}: ", err)
            sys.exit(1)  # Refactor

        # Set timezone offset
        self.config["utc_offset"] = get_utc_offset()

        if "use_servertime" not in self.config:
            self.config["use_servertime"] = True

        # Get bitcoind rpc_user and password from env if not in config
        if "bitcoind" not in self.config:
            if "bitcoind_rpc_user" not in self.config["bitcoind"]:
                self.set({"bitcoind_rpc_user": os.getenv("RPC_USER")}, "bitcoind")
            
            if "bitcoind_rpc_password" not in self.config["bitcoind"]:
                self.set({"bitcoind_rpc_password": os.getenv("RPC_PASSWORD")}, "bitcoind")

            if "rpc_url" not in self.config["bitcoind"]:
                self.set({"rpc_url": os.getenv("RESIGNER_RPC_URL")}, "bitcoind")

        print("config: ", self.config)
 
    def get(self, key: str) -> Union[Dict, str]:
        if key in self.config:
            return self.config[key]
        else:
            raise TypeError(f"requested key: {key} not in configuration")

    def set(self, key: Dict, section: str = None) -> None:
        if isinstance(key, Dict):
            if section:
                if section in self.config:
                    self.config[section].update(key)
                else:
                    self.config[section] = key
            else:
                self.config.update(key)
