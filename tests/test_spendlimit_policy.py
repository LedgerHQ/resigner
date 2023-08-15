import math

import pytest

from .test_framework.utils import fund_address, createpsbt, reset_aggregate_spends
from ..src import AggregateSpends

SATS = 100000000

def create_funded_psbt(funder, resigner_wallet, user_change_wallet_1, amount):
    receive_addr = funder.getnewaddress()
    change_addr = user_change_wallet_1.getnewaddress()
    unspent = resigner_wallet.listunspent(7)

    if len(unspent) < math.floor(amount/0.2):
        pytest.fail("There is not enough funds in wallet to complete transaction")

    num_of_utxos = math.floor(amount/0.2) + 1
    return createpsbt(resigner_wallet, unspent[0:num_of_utxos], receive_addr, amount, change_addr)

def test_spendlimit_policy(config, client, funder, resigner_wallet, user_wallet_1, user_change_wallet_1):
    """Attempt to spend above daily limit"""
    daily_limit = config.get("spending_limt")["daily_limit"]
    amount = (daily_limit * 2)/SATS
    
    unsigned_psbt = create_funded_psbt(funder, resigner_wallet, user_change_wallet_1, amount)
    incomplete_psbt = user_wallet_1.walletprocesspsbt(unsigned_psbt)["psbt"]

    response = client.post("/process-psbt", json={"psbt": incomplete_psbt})

    assert response.json["error_code"] == 403 and response.json["message"] ==  "PSBT Failed to satisfy configured SpendLimit policy"
