import sqlite3


class Database:
    def __init__(self, path: str = "resigner.db", **kwargs):
        self.connection = sqlite3.connect(path, check_same_thread=False, **kwargs)


Session = Database().connection
