import json

import pytest

from .test_framework.utils import fund_address, createpsbt, reset_aggregate_spends
from ..src import BitcoindRPCError

def test_signer(client, funder, resigner_wallet, user_wallet_1, user_change_wallet_1):
    # Truncate AggregateSpends Table
    #reset_aggregate_spends()

    receive_addr = funder.getnewaddress()
    change_addr = user_change_wallet_1.getnewaddress()
    unspent = resigner_wallet.listunspent(7)
    unsigned_psbt = createpsbt(resigner_wallet, [unspent[0]], receive_addr, 0.1, change_addr)

    incomplete_psbt = user_wallet_1.walletprocesspsbt(unsigned_psbt)["psbt"]

    response = client.post("/process-psbt", json={"psbt": incomplete_psbt})
 
    assert response.json["signed"] == True

    raw_hex = resigner_wallet.finalisepsbt(response.json["psbt"])["hex"]
    txid =  resigner_wallet.sendrawtransaction(raw_hex)

    # generate extra block to confirm the tx
    funder.generatetoaddress(7, funder.getnewaddress())

    # verify transaction
    try:
        tx = funder.gettransaction(txid)
    except BitcoindRPCError as excinfo:
        pytest.fail("the transaction: ", hex_tx, ", was not broadcasted: ", excinfo)
