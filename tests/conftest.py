import os
import sys
import time
import pytest
import shutil
import tempfile
import subprocess

from httpx import ConnectError

from ..src import Configuration
from ..src import BitcoindRPC, BitcoindRPCError
from ..src.main import create_app, init_db, setup_logging
from ..src.daemon import sync_utxos
from ..src.policy import (
    Policy,
    PolicyHandler,
    PolicyException,
    SpendLimit
)

from ..src.models import (
    Utxos,
    SpentUtxos,
    SignedSpends,
    AggregateSpends
)

from .test_framework.utils import fund_address, createpsbt, reset_aggregate_spends

CONFIG_FILE = "config_test.toml"
BTC_RPC_PORT = 18443
BITCOIN_DIRNAME = ".test_bitcoin"

@pytest.fixture(scope="session")
def run_bitcoind(config):
    # Run bitcoind in a separate folder
    os.makedirs(BITCOIN_DIRNAME, exist_ok=True)

    bitcoind = os.getenv("BITCOIND", "bitcoind")

    shutil.copy(os.path.join(os.path.dirname(__file__), "bitcoin.conf"), BITCOIN_DIRNAME)
    subprocess.Popen([bitcoind, f"--datadir={BITCOIN_DIRNAME}"])

    bitcoind = config.get("bitcoind")
    btd_client = BitcoindRPC(bitcoind["rpc_url"], bitcoind["bitcoind_rpc_user"], bitcoind["bitcoind_rpc_password"])

    # Check bitcoind is running
    while True:
        try:
            blckchaininfo = btd_client.getblockchaininfo()
            print("checking if bitcoind is running: blockchaininfo: ", blckchaininfo)
            break
        except ConnectError as e:
            print("retrying bitcoind rpc after ConnectError")
            time.sleep(2)
        except BitcoindRPCError as e:
            print("retrying bitcoind rpc after BitcoindRPCError:", e)
            time.sleep(2)

    yield

    btd_client.stop()
    shutil.rmtree(BITCOIN_DIRNAME)

@pytest.fixture(scope="session")
def config():
    return Configuration(os.path.join(os.path.dirname(__file__),CONFIG_FILE))

@pytest.fixture(scope="session", autouse=True)
def app(config, resigner_wallet, resigner_change_wallet):
    db_fd, db_path = tempfile.mkstemp()
    os.environ["RESIGNER_DB_URL"] = db_path

    logger = setup_logging()
    policy_handler = PolicyHandler()
    policy_handler.register_policy(
        [
            SpendLimit(config),
        ]
    )

    config.set({"client": resigner_wallet}, "bitcoind")
    config.set({"change_client": resigner_change_wallet}, "bitcoind")

    config.set({"logger": logger})

    app = create_app(config, policy_handler)
    app.config.update({
        "TESTING": True,
    })
    init_db()
    yield app
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture(scope="function", autouse=True)
def client(app, sync_db):
    return app.test_client()

@pytest.fixture(scope="function")
def reset_db():
    reset_aggregate_spends()
    Utxos.delete()
    SpentUtxos.delete()
    SignedSpends.delete()

@pytest.fixture(scope="function", autouse=True)
def sync_db(resigner_wallet, reset_db):
    sync_utxos(resigner_wallet)

@pytest.fixture(scope="session", autouse=True)
def funder(config, run_bitcoind):
    bitcoind = config.get("bitcoind")
    btd_client = BitcoindRPC(bitcoind["rpc_url"], bitcoind["bitcoind_rpc_user"], bitcoind["bitcoind_rpc_password"])
    wallet_name = "testwallet"
   
    wallets = btd_client.listwalletdir()["wallets"]

    if not any(wallet["name"] == wallet_name for wallet in wallets):
        btd_client.createwallet(wallet_name, False, False, "", False, True)

    btd_client._url=f"{bitcoind['rpc_url']}/wallet/{wallet_name}"
    address = btd_client.getnewaddress()

    # Mine enough blocks so coinbases are mature and we have enough funds to run everything
    balance = btd_client.getbalance(minconf=101)
    if balance < 50 :
        btd_client.generatetoaddress(101, address)

    yield btd_client
    pass

@pytest.fixture(scope="session", autouse=True)
def resigner_wallet(config, funder):
    bitcoind = config.get("bitcoind")
    btd_client = BitcoindRPC(bitcoind["rpc_url"], bitcoind["bitcoind_rpc_user"], bitcoind["bitcoind_rpc_password"])
    wallet_name = "resigner_wallet"

    wallets = (btd_client.listwalletdir())["wallets"]

    if not any(wallet["name"] == wallet_name for wallet in wallets):
        btd_client.createwallet(wallet_name, False, True, "", False, True)

        btd_client._url=f"{bitcoind['rpc_url']}/wallet/{wallet_name}"

        descriptors = [
            "wsh(and_v(v:pk(tpubD6NzVbkrYhZ4WVLXUV8feb3wGeDj7ifwFCprLS5mMgod52gHEhdf5eRbHLfKpK7Quev91HYkP1TzooEM9jzY331ViXWzDbeWc4hFy9QdS3R/1/*),or_d(pk(tprv8ZgxMBicQKsPcu7atsTZmCB59KA6mhFr4TyKBghM7Tqu3cNHxVD2S2KFoth2b7c9tZsD3PetrANdQ8oc5KUw3KcZr273Vgxrd1dTzyGepSG/1/*),older(12960))))#acuwcxfl",
            "wsh(and_v(v:pk(tpubD6NzVbkrYhZ4WVLXUV8feb3wGeDj7ifwFCprLS5mMgod52gHEhdf5eRbHLfKpK7Quev91HYkP1TzooEM9jzY331ViXWzDbeWc4hFy9QdS3R/0/*),or_d(pk(tprv8ZgxMBicQKsPcu7atsTZmCB59KA6mhFr4TyKBghM7Tqu3cNHxVD2S2KFoth2b7c9tZsD3PetrANdQ8oc5KUw3KcZr273Vgxrd1dTzyGepSG/0/*),older(12960))))#uayvvntz"
        ]

        request = [
                        {
                'desc': descriptors[0],
                'active': True,
                'range': [0, 1000],
                'next_index': 0,
                'timestamp': 'now',
                'internal': True
            },
            {
                'desc': descriptors[1],
                'active': True,
                'range': [0, 1000],
                'next_index': 0,
                'timestamp': 'now'
            }

        ]

        res = btd_client.importdescriptors(request)
    else:
        btd_client._url=f"{bitcoind['rpc_url']}/wallet/{wallet_name}"


    iterator = 0
    while iterator < 10:
        addr = btd_client.getnewaddress()
        fund_address(addr, funder, 0.2)
        unspent = btd_client.listunspent(7, 100, [addr])
        if not unspent:
            pytest.fail("failed to fund resigner wallet")
        iterator += 1

    yield btd_client
    pass

@pytest.fixture(scope="session", autouse=True)
def resigner_change_wallet(config, funder):
    bitcoind = config.get("bitcoind")
    btd_client = BitcoindRPC(bitcoind["rpc_url"], bitcoind["bitcoind_rpc_user"], bitcoind["bitcoind_rpc_password"])
    wallet_name = "resigner_change_wallet"

    wallets = (btd_client.listwalletdir())["wallets"]

    if not any(wallet["name"] == wallet_name for wallet in wallets):
        btd_client.createwallet(wallet_name, False, True, "", False, True)

        btd_client._url=f"{bitcoind['rpc_url']}/wallet/{wallet_name}"
        desc = "wsh(and_v(v:pk(tpubD6NzVbkrYhZ4WVLXUV8feb3wGeDj7ifwFCprLS5mMgod52gHEhdf5eRbHLfKpK7Quev91HYkP1TzooEM9jzY331ViXWzDbeWc4hFy9QdS3R/1/*),or_d(pk(tprv8ZgxMBicQKsPcu7atsTZmCB59KA6mhFr4TyKBghM7Tqu3cNHxVD2S2KFoth2b7c9tZsD3PetrANdQ8oc5KUw3KcZr273Vgxrd1dTzyGepSG/1/*),older(12960))))#acuwcxfl"

        request = [
            {
                'desc': desc,
                'active': True,
                'range': [0, 1000],
                'next_index': 0,
                'timestamp': 'now'
            }
        ]

        res = btd_client.importdescriptors(request)
    else:
        btd_client._url=f"{bitcoind['rpc_url']}/wallet/{wallet_name}"

    yield btd_client
    pass

@pytest.fixture(scope="session")
def user_wallet_1(config):
    bitcoind = config.get("bitcoind")
    btd_client = BitcoindRPC(bitcoind["rpc_url"], bitcoind["bitcoind_rpc_user"], bitcoind["bitcoind_rpc_password"])
    wallet_name = "user_wallet_1"

    wallets = (btd_client.listwalletdir())["wallets"]

    if not any(wallet["name"] == wallet_name for wallet in wallets):
        btd_client.createwallet(wallet_name, False, True, "", False, True)

        btd_client._url=f"{bitcoind['rpc_url']}/wallet/{wallet_name}"

        desc = "wsh(and_v(v:pk(tprv8ZgxMBicQKsPd2JjaqU5FBPphchnxPV2fuE53v3TwR1EEYRWcJp4u9oj7E7VeGouzveBssGRrw8QRMevu2oBgPgWVy5CUAz8HU1AFCWnmiQ/0/*),or_d(pk(tpubD6NzVbkrYhZ4WN9NnX8AAbqBiLg2w2Skdma6UCjeXjeHt6d4at2ccWw7z4TRkdP6JzbTHiUn4Cyv8QcztoGXooUsP2Dud1AHLyUsCf1ekPU/0/*),older(12960))))#fj0wq55q"
        request = [
            {'desc': desc, 'active': True, 'range': [0, 1000], 'next_index': 0, 'timestamp': 'now'}
        ]

        btd_client.importdescriptors(request)
    else:
        btd_client._url=f"{bitcoind['rpc_url']}/wallet/{wallet_name}"

    yield btd_client
    pass

@pytest.fixture(scope="session")
def user_change_wallet_1(config):
    bitcoind = config.get("bitcoind")
    btd_client = BitcoindRPC(bitcoind["rpc_url"], bitcoind["bitcoind_rpc_user"], bitcoind["bitcoind_rpc_password"])
    wallet_name = "user_change_wallet_1"

    wallets = (btd_client.listwalletdir())["wallets"]

    if not any(wallet["name"] == wallet_name for wallet in wallets):
        btd_client.createwallet(wallet_name, False, True, "", False, True)

        btd_client._url=f"{bitcoind['rpc_url']}/wallet/{wallet_name}"

        desc = "wsh(and_v(v:pk(tprv8ZgxMBicQKsPd2JjaqU5FBPphchnxPV2fuE53v3TwR1EEYRWcJp4u9oj7E7VeGouzveBssGRrw8QRMevu2oBgPgWVy5CUAz8HU1AFCWnmiQ/1/*),or_d(pk(tpubD6NzVbkrYhZ4WN9NnX8AAbqBiLg2w2Skdma6UCjeXjeHt6d4at2ccWw7z4TRkdP6JzbTHiUn4Cyv8QcztoGXooUsP2Dud1AHLyUsCf1ekPU/1/*),older(12960))))#ghhv5pka"
        request = [
            {'desc': desc, 'active': True, 'range': [0, 1000], 'next_index': 0, 'timestamp': 'now'}
        ]

        btd_client.importdescriptors(request)
    else:
        btd_client._url=f"{bitcoind['rpc_url']}/wallet/{wallet_name}"

    yield btd_client
    pass
