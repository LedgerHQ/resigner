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

def async_wrapper(func, params):
    asyncio.run(func(*params))

async def async_looper(btcd):
    while True:
        start_time = time.time()
        await asyncio.gather(sync_utxos(btcd), sync_aggregate_spends(btcd))

        end_time = time.time()
        if (end_time - start_time) < BLOCK_TIME:
            await asyncio.sleep(BLOCK_TIME - (end_time - start_time))


def sync_looper(config, timer):
    while True:
        thread1 = threading.Thread(target=reset_aggregate_spends, args=([config, timer]))

        start_time = math.floor(time.time())
        
        thread1.start()
        thread1.join()

        end_time = math.floor(time.time())

        if (end_time - start_time) < BLOCK_TIME:
            time.sleep(BLOCK_TIME - (end_time - start_time))


async def sync_utxos(btcd: BitcoindRPC):
    tip = await btcd.getblockcount()
    unspent = await btcd.listunspent()
    receive = await btcd.listreceivedbyaddress()

    coins = Utxos.get()
    utxo_is_in_db = False
    
    # Insert new uxto in Utxos Table
    for utxo in unspent:
        for coin in coins:
            if coin["txid"] == utxo["txid"] and coin["vout"] == utxo["vout"]:
                utxo_is_in_db = True

        if not utxo_is_in_db:
            Utxos.insert(
                (tip-utxo["confirmations"]),
                utxo["txid"],
                utxo["vout"],
                utxo["amount"]*SATS
            )
        utxo_is_in_db = False

    # Delete spent coin from Utxos Table
    utxo_has_been_spent = True
    for coin in coins:
        for utxo in unspent:
            if coin["txid"] == utxo["txid"] and coin["vout"] == utxo["vout"]:
                utxo_has_been_spent = False

        if utxo_has_been_spent:
            try:
                Utxos.delete({"txid": coin["txid"]})
            except OperationalError as e:
                # Ignoring this for now
                print("Database not fully synced. ", e)

        utxo_has_been_spent = True


async def sync_aggregate_spends(btcd: BitcoindRPC):
    signed_spends = SignedSpends.get()
    spent_utxos = SpentUtxos.get()
    if bool(signed_spends):
        for row in signed_spends:
            spent_utxos = SpentUtxos.get([], {"id": row["utxo_id"]})

            txout = None
            if not row["confirmed"]:
                txout = await btcd.gettxout(spent_utxos["txid"], spent_utxos["vout"])
                if not txout:
                    SignedSpends.update({"confirmed": True}, {"utxo_id": row["utxo_id"]})
                    agg_spends = AggregateSpends.get()
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
    btcd = config.get("bitcoind")["client"]
    timer = SpendLimit(config)

    config.set({
        "hrs_passed_since_last_day": timer._hrs_passed_since_last_day,
        "days_passed_since_last_week": timer._days_passed_since_last_week,
        "days_passed_since_last_month": timer._days_passed_since_last_month
        }, "timer")

    thread1 = threading.Thread(target=async_wrapper, args=(async_looper, [btcd]))
    thread2 = threading.Thread(target=sync_looper, args=([config, timer]))

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()
