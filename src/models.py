import time
from typing import Any, List, Dict, Optional

from db import Session

# Our coins
UTXOS_SCHEMA = """CREATE TABLE UTXOS
id INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
blockheight INT NOT NULL,
blocktime INT NOT NULL,
txid VARCHAR NOT NULL,
vout INT NOT NULL,
amount_sats INT NOT NULL
UNIQUE (txid, vout)
"""

# Table containing utxos that have been have been signed but has not yet been committed
# to the blockchain or has been commited to the blockchain but does not have enough
#confirmations to survive a blockchain reorganisation
SPENT_UTXOS_SCHEMA = """CREATE TABLE SPENT_UTXOS
(id INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
txid VARCHAR NOT NULL,
vout VARCHAR NOT NULL,
tx_spending_utxo INT NOT NULL,
FOREIGN KEY (tx_spending_utxo) REFERENCES SIGNED_SPENDS(id)
FOREIGN KEY (id) REFERENCES UTXOS(id)
)
"""

AGGREGATE_SPENDS_SCHEMA = """CREATE TABLE AGGREGATE_SPENDS
(daily_spends INT,
weekly_spends INT,
monthly_spends INT
);
"""

# Spend transaction, since we are not responsible for finalizing the transactions
SIGNED_SPENDS_SCHEMA = """CREATE TABLE SIGNED_SPENDS
(id INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
processed_at INT NOT NULL,
unsigned_psbt VARCHAR NOT NULL,
signed_psbt VARCHAR NOT NULL,
destination VARCHAR NOT NULL,
amount_sats INT NOT NULL,
utxo_id VARCHAR NOT NULL,
request_timestamp INT,
FOREIGN KEY (utxo_id) REFERENCES SPENT_UTXOS (id)
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


    @classmethod
    def update(self, options: Dict, condition: Optional[str] = ""):
        """'condition' is piece of sql containing with the 'where' clause"""
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


class Utxos(BaseModel):
    _table: str = "UTXOS"
    _primary_key: bool = True

    @classmethod
    def insert(self, blockheight: int, blocktime: int, txid: str, vout: int, amount_sats: int):
        sql = f"""INSERT INTO {self._table} VALUES (?,?,?,?,?)"""

        Session.execute(
            sql,
            [blockheight, blocktime, txid, vout, amount_sats]
        ).commit()


class SpentUtxos(BaseModel):
    _table: str = "SPENT_UTXOS"
    _primary_key: bool = True

    @classmethod
    def insert(self, txid: str, vout: int, tx_spending_utxo: int):
        sql = f"""INSERT INTO {self._table} VALUES (?,?,?)"""

        Session.execute(sql, [txid, vout, tx_spending_utxo]).commit()


class AggregateSpends(BaseModel):
    _table: str = "AGGREGATE_SPENDS"
    _primary_key: bool = False

    @classmethod
    def insert(self, daily_spends: int = 0, weekly_spends: int = 0, monthly_spends: int = 0):
        sql = f"""INSERT INTO {self._table} VALUES (?,?,?)"""

        Session.execute(sql, [daily_spends, weekly_spends, monthly_spends]).commit()


class SignedSpends(BaseModel):
    _table: str = "SIGNED_SPENDS"
    _primary_key = True

    @classmethod
    def insert(
        self,
        unsigned_psbt: str,
        signed_psbt: str,
        destination: str,
        amount_sats: int,
        utxo_id: str,
        request_timestamp: Optional[int] = 0
    ):
        sql = f"""INSERT INTO {self._tables} VALUES (?,?,?,?,?,?,?)"""

        Session.execute(
            sql,
            [
                time.time(),
                unsigned_psbt,
                signed_psbt,
                destination,
                amount_sats,
                utxo_id,
                request_timestamp
            ]
        ).commit()
