import time
from typing import Any, List, Dict, Optional

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

    def __insert(self):
        raise NotImplementedError

    @classmethod
    def get(self, *args):
        sql_query = f"""SELECT {",".join(args)} from {self._table}"""
        self._cursor = Session.execute(sql_query)
        
        result = {}
        for row in self._cursor:
            for i in range(len(args)):
                result[args[i]] = row[i]

        return result

    # 'condition' is piece of sql containing with the 'where' clause
    @classmethod
    def update(self, options: Dict, condition: Optional[str] = ""):
        query = []
        for key, value in options.items():
            query.append(f" {key} = {value}")

        sql = f"""UPDATE {self._table}
        SET {", ".join(query)}
        {condition}
        """

        Session.execute(sql).commit()

    @classmethod
    def filter(self):
        raise NotImplementedError


class AggregateSpends(BaseModel):
    _table: str = "AGGREGATE_SPENDS"
    _primary_key = False

    def insert(self, daily_spends: int = 0, weekly_spends: int = 0, monthly_spends: int = 0):
        sql = f"""INSERT INTO {self._table} VALUES (?,?,?)"""

        Session.execute(sql, [daily_spends, weekly_spends, monthly_spends]).commit()



class SignedSpends(BaseModel):
    _table: str = "SIGNED_SPENDS"
    _primary_key = True

    @classmethod
    def insert(self, signed_psbt: str, unsigned_psbt: str, amount: int, request_timestamp: Optional[int] = 0):
        sql = f"""INSERT INTO {self._tables} VALUES (?,?,?,?,?)"""

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
