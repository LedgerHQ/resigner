# Todo: We need to build up a database of utxos on startup
# Check for receives so we can update the db:
# - after each restart
# - after a certain blocktime
# - during each sign request
# Check periodically for spends outside resigner. update the db ?
#

import time
import math
import logging
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

# Logging
sh = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s - %(asctime)s.%(msecs)03d - %(name)s - ThreadId %(thread)d: %(message)s", datefmt='%H:%M:%S')
sh.setFormatter(formatter)

logger = logging.getLogger("resigner.daemon")
logger.addHandler(sh)

def sync_utxos(btd_client: BitcoindRPC):

    def update_utxos(tip, unspent, coins):
        # Insert new uxto in Utxos Table
        for utxo in unspent:
            coin = Utxos.get(["id"], {"txid": utxo["txid"], "vout": utxo["vout"]})
            if not coin:
                logger.debug("Inserting new UTXO into Utxos Table. txid: %s, vout: %d", utxo["txid"], utxo["vout"])
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
                logger.debug("Deleting spent UTXO from Utxos Table. txid: %s, vout: %d", coin["txid"], coin["vout"])
                Utxos.delete({"txid": coin["txid"]})


    coins = Utxos.get()
    tip = btd_client.getblockcount()
    unspent = btd_client.listunspent()

    logger.info("Updating utxos")
    update_utxos(tip, unspent, coins)

def sync_aggregate_spends(config: Configuration):
    btd_client = config.get("bitcoind")["client"]
    min_conf = config.get("resigner_config")["min_conf"]
    signed_spends = SignedSpends.get()

    for row in signed_spends:
        if not row["confirmed"]:
            try:
                tx = btd_client.getrawtransaction(row["id"])
                # After 6 confirmations, the chances of loosing a tx due to reorganisations becomes negligible
                if tx["confirmations"] > min_conf:
                    logger.info("Signed psbt: %s has been confirmed on the blockchain", row["signed_psbt"])
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
            except BitcoindRPCError as e:
                logger.info("Transaction `%s` does not exist on the blockchain", row["id"])
                spent_utxos = SpentUtxos.get([], {"psbt_id": row["id"]})
                txouts = [(btd_client.gettxout(spends["txid"], spends["vout"])) for spends in spent_utxos]
                if not all(txouts):
                    logger.info("UTXOs in transaction `%s` has been respent in another transaction", row["id"])
                    SignedSpends.delete({"id": row["id"]})
                    SpentUtxos.delete({"psbt_id": row["id"]})
                

def reset_aggregate_spends(config: Configuration, timer: SpendLimit):
    """Reset the aggregate spends in the db after each day, week and month
    """
    prvs_time = config.get("timer")

    if prvs_time["hrs_passed_since_last_day"] > timer._hrs_passed_since_last_day:
        logger.info("Aggregate daily spends has been reset to 0")
        logger.info("Aggregate spends counted towards the daily limit reset to 0")

    if prvs_time["days_passed_since_last_week"] > timer._days_passed_since_last_week:
        logger.info("Aggregate weekly spends has been reset to 0")
        AggregateSpends.update({"confirmed_weekly_spends": 0})

    if prvs_time["days_passed_since_last_month"] > timer._days_passed_since_last_month:
        logger.info("Aggregate monthly spends has been reset to 0")
        AggregateSpends.update({"confirmed_monthly_spends": 0})

    config.set({
        "hrs_passed_since_last_day": timer._hrs_passed_since_last_day,
        "days_passed_since_last_week": timer._days_passed_since_last_week,
        "days_passed_since_last_month": timer._days_passed_since_last_month
        }, "timer")

def daemon(config: Configuration, condition: threading.Condition):
    logger.info("resigner daemon starting...")

    timer = SpendLimit(config)

    config.set({
        "hrs_passed_since_last_day": timer._hrs_passed_since_last_day,
        "days_passed_since_last_week": timer._days_passed_since_last_week,
        "days_passed_since_last_month": timer._days_passed_since_last_month
        }, "timer")

    btd_client = config.get("bitcoind")["client"]

    condition.acquire()
    synced_db_with_onchain_data = False
    threads = []
    while True:
        threads.append(threading.Thread(target=sync_utxos, args=([btd_client])))
        threads.append(threading.Thread(target=sync_aggregate_spends, args=([config])))
        threads.append(threading.Thread(target=reset_aggregate_spends, args=([config, timer])))

        start_time = math.floor(time.time())
        
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        threads.clear()
        synced_db_with_onchain_data = True
        if condition._is_owned():
            config.set({"synced_db_with_onchain_data": synced_db_with_onchain_data},"resigner_config")
            # Notify main thread
            condition.notify()
            condition.release()

        end_time = math.floor(time.time())

        if (end_time - start_time) < BLOCK_TIME:
            time.sleep(BLOCK_TIME - (end_time - start_time))
