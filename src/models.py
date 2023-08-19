import re
import time
import logging
from typing import Any, List, Dict, Optional
from sqlite3 import OperationalError
from threading import RLock
from .db import Session
from .errors import DBError

ADDRESS_SCHEMA = """CREATE TABLE addresses (
    receive_address VARCHAR NOT NULL UNIQUE,
    change_address VARCHAR NOT NULL UNIQUE,
    derivation_index INTEGER NOT NULL UNIQUE
);
"""

logger = logging.getLogger("resigner")

class BaseModel:
    _cursor: Any = None
    _table: str
    _columns: List
    _schema: str

    @classmethod
    def create(self):
        """Create table"""
        try:
            logger.info("Creating %s table", self._table)
            cursor = Session.cursor()
            cursor.executescript(self._schema)
            cursor.close()
            Session.commit()
        except OperationalError as e:
            if not re.search("already exists" , str(e)):
                raise DBError(str(e))
            logger.info("Table: %s already exists in db", self._table)

    def __insert(self):
        raise NotImplementedError

    @classmethod
    def get(self, args: Optional[List] = [], condition: Optional[Dict] = {}):
        query_condition = []
        query = ""

        if bool(condition):
            for key, value in condition.items():
                query_condition.append(f"{key} = :{key} ")

            query = f"Where {'AND '.join(query_condition)}"

        if bool(args):
            sql_query = f"SELECT {','.join(args)} From {self._table} {query};"
        else:
            sql_query = f"SELECT * From {self._table} {query}"
            args = self._columns

        self._cursor = Session.execute(sql_query, condition)
        
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
    def update(self, values: Dict, condition: Optional[Dict] = {}):
        rlock = RLock()
        query_condition = []
        condition_query = ""

        if bool(condition):
            for key, value in condition.items():
                query_condition.append(f"{key} = :{key} ")

            condition_query = f"Where {'AND '.join(query_condition)}"

        values_query = []
        for key, value in values.items():
            values_query.append(f" {key} = :{key}")


        sql = f"""UPDATE {self._table}
        SET {", ".join(values_query)}
        {condition_query};
        """
        with rlock:
            cursor = Session.cursor()
            cursor.execute(sql, {**values, **condition})
            cursor.close()
            Session.commit()

    @classmethod
    def filter(self):
        raise NotImplementedError

    @classmethod
    def delete(self, condition: Dict = {}):
        rlock = RLock()
        sql_query = ""
        if bool(condition):
            query_condition = []
            for key, value in condition.items():
                query_condition.append(f"{key} = :{key} ")

            sql_query = f"""DELETE FROM {self._table} WHERE {"AND ".join(query_condition)};"""
        else:
            logger.info("About to truncate %s table", self._table)
            sql_query = f"DELETE FROM {self._table};"

        with rlock:
            cursor = Session.cursor()
            cursor.execute(sql_query, condition)
            cursor.close()
            Session.commit()

    @classmethod
    def delete_table(self):
        """Drop table from DB"""
        sql_query = f"DROP TABLE {self._table};"

        # Threads shouldn't be dropping tables willy nilly
        cursor = Session.cursor()
        cursor.execute(sql_query)
        cursor.close()
        Session.commit()


class Utxos(BaseModel):
    _table: str = "UTXOS"
    _schema : str = f"""CREATE TABLE utxos
        (id INTEGER PRIMARY KEY,
        blockheight INT NOT NULL,
        txid VARCHAR NOT NULL,
        vout INT NOT NULL,
        amount_sats INT NOT NULL,
        UNIQUE (txid, vout))
        """
    _primary_key: bool = True
    _columns: List = [
        "id", "blockheight", "txid", "vout", "amount_sats"
    ]

    @classmethod
    def insert(self, blockheight: int, txid: str, vout: int, amount_sats: int):
        # initializing size of string
        #N = 10
         
        # using secrets.choice()
        # generating random strings
        #primary_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(N))

        sql = f"""INSERT INTO {self._table} VALUES (NULL,?,?,?,?);"""

        rlock = RLock()
        with rlock:
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
    _schema: str = """CREATE TABLE SPENT_UTXOS
        (id INTEGER PRIMARY KEY NOT NULL,
        txid VARCHAR NOT NULL,
        vout INT NOT NULL,
        psbt_id INT NOT NULL,
        UNIQUE (txid, vout),
        FOREIGN KEY (psbt_id) REFERENCES SIGNED_SPENDS(id))
        """
    _columns: List = [
        "id", "txid", "vout", "psbt_id"
    ]

    @classmethod
    def insert(self, txid: str, vout: int, psbt_id: int):
        sql = f"""INSERT INTO {self._table} VALUES (NULL,?,?, ?);"""

        rlock = RLock()
        with rlock:
            cursor = Session.cursor()
            cursor.execute(sql, [txid, vout, psbt_id])
            cursor.close()
            Session.commit()


class AggregateSpends(BaseModel):
    _table: str = "AGGREGATE_SPENDS"
    _primary_key: bool = False
    _schema: str = """CREATE TABLE AGGREGATE_SPENDS
        (unconfirmed_daily_spends INT,
        confirmed_daily_spends INT,
        unconfirmed_weekly_spends INT,
        confirmed_weekly_spends INT,
        unconfirmed_monthly_spends INT,
        confirmed_monthly_spends INT
        );
        """
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

        rlock = RLock()
        with rlock:
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
    _schema: str = """CREATE TABLE SIGNED_SPENDS
        (id INTEGER PRIMARY KEY NOT NULL,
        processed_at INT NOT NULL,
        unsigned_psbt VARCHAR NOT NULL,
        signed_psbt VARCHAR NOT NULL,
        amount_sats INT NOT NULL,
        request_timestamp INT,
        confirmed BOOL
        );
        """
    _columns: List = [
        "id",
        "processed_at",
        "unsigned_psbt",
        "signed_psbt",
        "amount_sats",
        "request_timestamp",
        "confirmed"
    ]

    @classmethod
    def insert(
        self,
        unsigned_psbt: str,
        signed_psbt: str,
        amount_sats: int,
        request_timestamp: Optional[int] = 0,
        confirmed: Optional[bool] = False
    ):
        sql = f"""INSERT INTO {self._table} VALUES (NULL,?,?,?,?,?,?);"""

        rlock = RLock()
        with rlock:
            cursor = Session.cursor()
            cursor.execute(
                sql,
                [
                    time.time(),
                    unsigned_psbt,
                    signed_psbt,
                    amount_sats,
                    request_timestamp,
                    confirmed
                ]
            )
            cursor.close()
            Session.commit()
 