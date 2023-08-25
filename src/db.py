import os
import sqlite3

class Database:
    def __init__(self, path, **kwargs):
        self.connection = sqlite3.connect(path, timeout=100, check_same_thread=False, **kwargs)


Session = Database(os.getenv("RESIGNER_DB_URI", "resigner.db")).connection
