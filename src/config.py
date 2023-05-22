import toml

class Configuration:
    def __init__(self, config_path: str):
        try:
            self.config = toml.load(config_path)
        except(TypeError):
            pass
        except(TomlDecodeError):
            pass
        