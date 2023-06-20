import time
from typing import Any, List, Dict

from db import Session

AGGREGATE_SPENDS_SCHEMA = """CREATE TABLE AGGREGATE_SPENDS
(daily_spends INT,
weekly_spends INT,
monthly_spends INT
);
"""

SIGNED_SPENDS_SCHEMA = """CREATE TABLE SIGNED_SPENDS
(processed_at INT PRIMARY KEY NOT NULL,
unsigned_psbt VARCHAR NOT NULL,
signed_psbt VARCHAR NOT NULL,
amount INT NOT NULL,
request_timestamp INT
);
"""


class BaseModel:
    _cursor: Any = None

    def __create(self, shema):
        raise NotImplementedError

    def insert(self):
        raise NotImplementedError

    def get(self):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError

    def filter(self):
        raise NotImplementedError


class AggregateSpends(BaseModel):
    def __init__(self):
        self.__create(AGGREGATE_SPENDS_SCHEMA)

    def __create(self, schema):
        Session.execute(schema)

    def insert(self, daily_spends: int = 0, weekly_spends: int = 0, monthly_spends: int = 0):
        sql = """INSERT INTO AGGREGATE_SPENDS VALUES (?,?,?)"""

        Session.execute(sql, [daily_spends, weekly_spends, monthly_spends]).commit()

    def get(self, *args):
        sql = f"""SELECT {",".join(args)} from AGGREGATE_SPENDS"""

        self._cursor = Session.execute(sql)
        
        ret = {}
        for row in self._cursor:
            for i in range(len(args))
                ret[args[i]] = row[i]

        return ret

    def update(self, options: Dict):
        query = []
        for key, value in options.items():
            query.append(f" {key} = {value}")

        # There should be just one Row in AGGREGATE_SPENDS
        sql = f"""UPDATE AGGREGATE_SPENDS
        SET {", ".join(query)}
        """

        Session.execute(sql).commit()


class SignedSpends(BaseModel):
    def __init__(self):
        self.__create(SIGNED_SPENDS_SCHEMA)

    def __create(self, schema):
        Session.execute(schema)

    def insert(self, signed_psbt: str, unsigned_psbt: str, amount: int, request_timestamp: Optional[int] = 0):
        sql = """INSERT INTO SIGNED_SPENDS VALUES (?,?,?,?,?)"""

        Session.execute(
            sql,
            [
                time.time(),
                unsigned_psbt,
                signed_psbt,
                amount,
                request_timestamp
            ]
        ).commit()

    def get(self, *args):
        sql = f"""SELECT {",".join(args)} from SIGNED_SPENDS"""

        self._cursor = Session.execute(sql)
        
        ret = {}
        for row in self._cursor:
            for i in range(len(args))
                ret[args[i]] = row[i]

        return ret

    def update(self, options: Dict):
        query = []
        for key, value in options.items():
            query.append(f" {key} = {value}")

        # There should be just one Row in AGGREGATE_SPENDS
        sql = f"""UPDATE SIGNED_SPENDS
        SET {", ".join(query)}
        """

        Session.execute(sql).commit()
