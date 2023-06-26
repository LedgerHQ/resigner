from api import SigningService
from config import Configuration
from policy import Policy
from psbt import Psbt
from db import Session
from models import (
    Utxos,
    SpentUtxos,
    AggregateSpends,
    SignedSpends,
    UTXOS_SCHEMA,
    SPENT_UTXOS_SCHEMA,
    AGGREGATE_SPENDS_SCHEMA,
    SIGNED_SPENDS_SCHEMA
)

from policy import SpendLimit

class 

def main():
    # Create tables
    Session.execute(UTXOS_SCHEMA)
    Session.execute(SPENT_UTXOS_SCHEMA)
    Session.execute(AGGREGATE_SPENDS_SCHEMA)
    Session.execute(SIGNED_SPENDS_SCHEMA)

    # Todo


if __name__ == '__main__':
    main()
