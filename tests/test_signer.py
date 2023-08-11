import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, Request

import pytest

from ..src import BitcoindRPCError

async def fund_address(address, funder):
    await funder.sendtoaddress(address, 1.5)
    funder_addr = await funder.getnewaddress()
    await funder.generatetoaddress(10, funder_addr)

def make_request(data, url, headers={"Content-Type": "application/json"}):
    data = data.encode("utf-8")
    request = Request(url, headers=headers, data=data)
    signed_psbt = None
    try:
        with urlopen(request) as response:
            print(response.status)
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        pytest.fail(f"status: {error.status}, {error.reason}")
    except URLError as error:
        pytest.fail(f"{error.reason}")
    except BitcoindRPCError as excinfo:
        pytest.fail(excinfo.value)
    except TimeoutError:
        pytest.fail("Request timed out")

async def createpsbt(wallet, utxos, address, amount, change_address):
    fee = 0.001
    amount_available_for_spend = 0

    for utxo in utxos:
        amount_available_for_spend += utxo["amount"]
    
    change = amount_available_for_spend - amount - fee
    inputs = [
        {"txid": utxo["txid"], "vout": utxo["vout"]} for utxo in utxos
    ]
    return await wallet.createpsbt(
        inputs,
        [{address: 0.1}, {change_address: change}]
    )

@pytest.mark.dependency()
async def test_signer(service_url, funder, multisig_wallet_1, user_wallet_1):
   
    multisig_addr = await multisig_wallet_1.getnewaddress()
    await fund_address(multisig_addr, funder)
    unspent = await multisig_wallet_1.listunspent(7, 100, [multisig_addr])
    if not unspent:
        pytest.fail("failed to fund multisig address")

    funder_addr = await funder.getnewaddress()

    unsigned_psbt = await createpsbt(multisig_wallet_1, [unspent[0]], funder_addr, 0.1, multisig_addr)

    incomplete_psbt = (await user_wallet_1.walletprocesspsbt(unsigned_psbt))["psbt"]

    data = json.dumps({"psbt": incomplete_psbt})
    url = service_url[0]
    res = make_request(data, url)
    if not res["signed"]:
        pytest.fail("failed to sign the psbt: ", unsigned_psbt)

    signed_psbt = res["psbt"]
    raw_hex = (await multisig_wallet_1.finalisepsbt(signed_psbt))["hex"]
    txid =  await multisig_wallet_1.sendrawtransaction(raw_hex)

    await funder.generatetoaddress(10, await funder.getnewaddress())

    # verify transaction
    try:
        tx = await funder.gettransaction(txid)
    except BitcoindRPCError as excinfo:
        pytest.fail("the transaction: ", hex_tx, ", was not broadcasted: ", excinfo)

@pytest.mark.dependency(depends=["test_signer"])
async  def test_spendlimit_policy(service_url, funder, multisig_wallet_1, user_wallet_1):
    # Attempt to spend above daily limit

    unspent = await multisig_wallet_1.listunspent(7, 100)
    if not unspent:
        pytest.fail("failed to fund multisig address")

    funder_addr = await funder.getnewaddress()

    unsigned_psbt = await createpsbt(multisig_wallet_1, [unspent[0]], funder_addr, 0.1, unspent[0]["address"])

    incomplete_psbt = (await user_wallet_1.walletprocesspsbt(unsigned_psbt))["psbt"]
    data = json.dumps({"psbt": incomplete_psbt})
    url = service_url[0]

    res = make_request(data, url)

    if res["signed"]:
        pytest.fail()
