# Todo: We need to build up a database of utxos on startup
# Check for receives so we can update the db:
# - after each restart
# - after a certain blocktime
# - during each sign request
# Check periodically for spends outside resigner. update the db ?
#

import time
import math
import asyncio
import threading
from sqlite3 import OperationalError

from .config import Configuration
from .bitcoind_rpc_client import BitcoindRPC, BitcoindRPCError
from .db import Session
from .models import (
    Utxos,
    SpentUtxos,
    SignedSpends,
    AggregateSpends
)

from .policy import SpendLimit

SATS=100000000
BLOCK_TIME = 10*60  # Approx time to create a block


def sync_utxos(btd_client: BitcoindRPC, btd_change_client: BitcoindRPCError):

    def update_utxos(tip, unspent, coins):
        # Insert new uxto in Utxos Table
        for utxo in unspent:
            coin = Utxos.get(["id"], {"txid": utxo["txid"], "vout": utxo["vout"]})
            if not coin:
                Utxos.insert(
                    (tip-utxo["confirmations"]),
                    utxo["txid"],
                    utxo["vout"],
                    utxo["amount"]*SATS
                )

        # Delete spent coin from Utxos Table
        for coin in coins:
            txout = btd_client.gettxout(coin["txid"], coin["vout"])
            if not txout:
                # Should not fail
                Utxos.delete({"txid": coin["txid"]})


    coins = Utxos.get()
    tip = btd_client.getblockcount()
    unspent = btd_client.listunspent()

    update_utxos(tip, unspent, coins)

    if btd_change_client is not None:
        unspent_change = btd_change_client.listunspent()
        update_utxos(tip, unspent_change, coins)


def sync_aggregate_spends(btd_client: BitcoindRPC):
    signed_spends = SignedSpends.get()
    for row in signed_spends:
        spent_utxos = SpentUtxos.get([], {"psbt_id": row["id"]})
        print("in sync_aggregate_spends: spent_utxos: ", spent_utxos)
        if not row["confirmed"]:
            txouts = [(btd_client.gettxout(spends["txid"], spends["vout"])) for spends in spent_utxos]
            if not all(txouts):
                SignedSpends.update({"confirmed": True}, {"id": row["id"]})
                agg_spends = AggregateSpends.get()[0]
                AggregateSpends.update(
                    {
                        "confirmed_daily_spends": agg_spends["confirmed_daily_spends"] + row["amount_sats"],
                        "unconfirmed_daily_spends": agg_spends["unconfirmed_daily_spends"] - row["amount_sats"],
                        "confirmed_weekly_spends": agg_spends["confirmed_weekly_spends"] + row["amount_sats"],
                        "unconfirmed_weekly_spends": agg_spends["unconfirmed_weekly_spends"] - row["amount_sats"],
                        "confirmed_monthly_spends": agg_spends["confirmed_monthly_spends"] + row["amount_sats"],
                        "unconfirmed_monthly_spends": agg_spends["unconfirmed_monthly_spends"] - row["amount_sats"]
                    }
                )

def reset_aggregate_spends(config: Configuration, timer: SpendLimit):
    """Reset the aggregate spends in the db after each day, week and month
    """
    prvs_time = config.get("timer")

    if prvs_time["hrs_passed_since_last_day"] > timer._hrs_passed_since_last_day:
        AggregateSpends.update({"confirmed_daily_spends": 0})

    if prvs_time["days_passed_since_last_week"] > timer._days_passed_since_last_week:
        AggregateSpends.update({"confirmed_weekly_spends": 0})

    if prvs_time["days_passed_since_last_month"] > timer._days_passed_since_last_month:
        AggregateSpends.update({"confirmed_monthly_spends": 0})

    config.set({
        "hrs_passed_since_last_day": timer._hrs_passed_since_last_day,
        "days_passed_since_last_week": timer._days_passed_since_last_week,
        "days_passed_since_last_month": timer._days_passed_since_last_month
        }, "timer")

def daemon(config: Configuration):
    timer = SpendLimit(config)

    config.set({
        "hrs_passed_since_last_day": timer._hrs_passed_since_last_day,
        "days_passed_since_last_week": timer._days_passed_since_last_week,
        "days_passed_since_last_month": timer._days_passed_since_last_month
        }, "timer")

    btd_client = config.get("bitcoind")["client"]
    btd_change_client = config.get("bitcoind")["change_client"]

    synced_db_with_onchain_data = False
    threads = []
    while True:
        threads.append(threading.Thread(target=sync_utxos, args=([btd_client, btd_change_client])))
        threads.append(threading.Thread(target=sync_aggregate_spends, args=([btd_client])))
        threads.append(threading.Thread(target=reset_aggregate_spends, args=([config, timer])))

        start_time = math.floor(time.time())
        
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        synced_db_with_onchain_data = True
        config.set({"synced_db_with_onchain_data": synced_db_with_onchain_data},"resigner_config")

        end_time = math.floor(time.time())

        if (end_time - start_time) < BLOCK_TIME:
            time.sleep(BLOCK_TIME - (end_time - start_time))