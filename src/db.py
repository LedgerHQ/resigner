import sqlite3

class db:
    def __init__(self, path: str = "resigner.db", **kwargs):
        self.connection = sqlite3.connect(path, **kwargs)

    def create(self, schema):
        self.connection.execute(schema)

Session = db().connection
