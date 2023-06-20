import sqlite3

from config import Configuration


class db:
    def __init__(self, path: str = "resigner.db", **kwargs):
        self.connection = sqlite3.connect(path,**kwargs)

    def create(self, schema):
        connection.execute(schema)


Session = db().connection
        