import sqlite3


class Database:
    def __init__(self, path: str = "resigner.db", **kwargs):
        self.connection = sqlite3.connect(path, **kwargs)


Session = Database().connection
