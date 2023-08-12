import time
from typing import Any, List, Dict, Optional

from .db import Session

# Our coins
UTXOS_SCHEMA = """CREATE TABLE utxos
(id INTEGER PRIMARY KEY,
blockheight INT NOT NULL,
txid VARCHAR NOT NULL,
vout INT NOT NULL,
amount_sats INT NOT NULL,
UNIQUE (txid, vout))
"""

# Table containing utxos that have been have been signed but has not yet been committed
# to the blockchain or has been commited to the blockchain but does not have enough
#confirmations to survive a blockchain reorganisation
SPENT_UTXOS_SCHEMA = """CREATE TABLE SPENT_UTXOS
(id INTEGER PRIMARY KEY NOT NULL,
txid VARCHAR NOT NULL,
vout VARCHAR NOT NULL,
FOREIGN KEY (id) REFERENCES UTXOS(id)
)
"""

AGGREGATE_SPENDS_SCHEMA = """CREATE TABLE AGGREGATE_SPENDS
(unconfirmed_daily_spends INT,
confirmed_daily_spends INT,
unconfirmed_weekly_spends INT,
confirmed_weekly_spends INT,
unconfirmed_monthly_spends INT,
confirmed_monthly_spends INT
);
"""

# Spend transaction, since we are not responsible for finalizing the transactions
SIGNED_SPENDS_SCHEMA = """CREATE TABLE SIGNED_SPENDS
(id INTEGER PRIMARY KEY NOT NULL,
processed_at INT NOT NULL,
unsigned_psbt VARCHAR NOT NULL,
signed_psbt VARCHAR NOT NULL,
amount_sats INT NOT NULL,
utxo_id VARCHAR NOT NULL,
request_timestamp INT,
confirmed BOOL,
FOREIGN KEY (utxo_id) REFERENCES SPENT_UTXOS (id)
);
"""

ADDRESS_SCHEMA = """CREATE TABLE addresses (
    receive_address VARCHAR NOT NULL UNIQUE,
    change_address VARCHAR NOT NULL UNIQUE,
    derivation_index INTEGER NOT NULL UNIQUE
);
"""

class BaseModel:
    _cursor: Any = None
    _columns: List

    def __create(self, shema):
        raise NotImplementedError

    def __insert(self):
        raise NotImplementedError

    @classmethod
    def get(self, args: Optional[List] = [], condition: Optional[Dict] = {}):
        query_condition = []
        query = ""

        if bool(condition):
            for key, value in condition.items():
                query_condition.append(f"{key} = {value} ")

            query = f"Where {query_condition}"

        if bool(args):
            sql_query = f"""SELECT {",".join(args)}
                From {self._table}
                {query};
            """
        else:
            sql_query = f"SELECT * From {self._table}"
            args = self._columns

        self._cursor = Session.execute(sql_query)
        
        result = []
        for row in self._cursor:
            row_dict = {}
            for i in range(len(args)):
                row_dict[args[i]] = row[i]

            result.append(row_dict)

        # Close cursor object
        self._cursor.close()
        return result


    @classmethod
    def update(self, options: Dict, condition: Optional[Dict] = {}):
        query_condition = []
        condition_query = ""

        if bool(condition):
            for key, value in condition.items():
                query_condition.append(f"{key} = {value} ")

            condition_query = f"Where {query_condition}"

        query = []
        for key, value in options.items():
            query.append(f" {key} = {value}")


        sql = f"""UPDATE {self._table}
        SET {", ".join(query)}
        {condition_query};
        """
        cursor = Session.cursor()
        cursor.execute(sql)
        cursor.close()
        Session.commit()

    @classmethod
    def filter(self):
        raise NotImplementedError

    @classmethod
    def delete(self, condition: Dict):
        query_condition = []
        if bool(condition):
            for key, value in condition.items():
                query_condition.append(f"{key} = {value} ")

        sql_query = f"""DELETE FROM {self._table} WHERE {", ".join(query_condition)};"""

        cursor = Session.cursor()
        cursor.execute(sql_query)
        cursor.close()
        Session.commit()

    @classmethod
    def delete_table(self):
        """Drop table from DB"""
        sql_query = f"DROP TABLE {self._table};"

        cursor = Session.cursor()
        cursor.execute(sql_query)
        cursor.close()
        Session.commit()


class Utxos(BaseModel):
    _table: str = "UTXOS"
    _primary_key: bool = True
    _columns: List = [
        "id", "blockheight", "txid", "vout", "amount_sats"
    ]

    @classmethod
    def insert(self, blockheight: int, txid: str, vout: int, amount_sats: int):
        sql = f"""INSERT INTO {self._table} VALUES (NULL, ?,?,?,?);"""

        cursor = Session.cursor()
        cursor.execute(
            sql,
            [blockheight, txid, vout, amount_sats]
        )
        cursor.close()
        Session.commit()


class SpentUtxos(BaseModel):
    _table: str = "SPENT_UTXOS"
    _primary_key: bool = True
    _columns: List = [
        "id", "txid", "vout"
    ]

    @classmethod
    def insert(self, _id: int, txid: str, vout: int):
        sql = f"""INSERT INTO {self._table} VALUES (?,?,?);"""

        cursor = Session.cursor()
        cursor.execute(sql, [_id, txid, vout])
        cursor.close()
        Session.commit()


class AggregateSpends(BaseModel):
    _table: str = "AGGREGATE_SPENDS"
    _primary_key: bool = False
    _columns: List = [
        "unconfirmed_daily_spends",
        "confirmed_daily_spends",
        "unconfirmed_weekly_spends",
        "confirmed_weekly_spends",
        "unconfirmed_monthly_spends",
        "confirmed_monthly_spends",
    ]

    @classmethod
    def insert(self,
        confirmed_daily_spends: int = 0,
        unconfirmed_daily_spends: int = 0,
        confirmed_weekly_spends: int = 0,
        unconfirmed_weekly_spends: int = 0,
        confirmed_monthly_spends: int = 0,
        unconfirmed_monthly_spends: int = 0
    ):
        sql = f"""INSERT INTO {self._table} VALUES (?,?,?,?,?,?);"""

        cursor = Session.cursor()
        cursor.execute(sql, [
            confirmed_daily_spends,
            unconfirmed_daily_spends,
            confirmed_weekly_spends,
            unconfirmed_weekly_spends,
            confirmed_monthly_spends,
            unconfirmed_monthly_spends
            ]
        )
        cursor.close()
        Session.commit()


class SignedSpends(BaseModel):
    _table: str = "SIGNED_SPENDS"
    _primary_key = True
    _columns: List = [
        "id",
        "processed_at",
        "unsigned_psbt",
        "signed_psbt",
        "amount_sats",
        "utxo_id",
        "request_timestamp",
        "confirmed"
    ]

    @classmethod
    def insert(
        self,
        unsigned_psbt: str,
        signed_psbt: str,
        destination: str,
        amount_sats: int,
        utxo_id: str,
        request_timestamp: Optional[int] = 0,
        confirmed: Optional[bool] = False
    ):
        sql = f"""INSERT INTO {self._tables} VALUES (NULL,?,?,?,?,?,?,?);"""

        cursor = Session.cursor()
        cursor.execute(
            sql,
            [
                time.time(),
                unsigned_psbt,
                signed_psbt,
                amount_sats,
                utxo_id,
                request_timestamp,
                confirmed
            ]
        )
        cursor.close()
        Session.commit()
