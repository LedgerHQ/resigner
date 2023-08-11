import os
import sys
import time
from multiprocessing import Process

import pytest

from ..src import Configuration
from ..src import BitcoindRPC, BitcoindRPCError
from ..src import local_main

CONFIG_FILES = [
    "config_test.toml"
]

PORTS = [
    7767
]

@pytest.fixture(scope="session", autouse=True)
def setup_resigner_for_tests():     
    services = []
    iterator = 0

    for file, port in zip(CONFIG_FILES, PORTS):
            os.environ["RESIGNER_CONFIG_PATH"] = f"{os.getcwd()}/tests/{file}"
            service = Process(target=local_main, args=(True, port))
            service.start()
            services.append(service)
    yield None
    print(f"Terminating services: {len(services)}")
    for service in services:
        service.join()
        service.terminate()
        service.close()

@pytest.fixture(scope="session", autouse=True)
def  service_url():
    return [f"http://127.0.0.1:{port}/process-psbt" for port in PORTS]

@pytest.fixture(scope="function")
def config():
    return Configuration(f"{os.getcwd()}/tests/{CONFIG_FILES[0]}")

@pytest.fixture(scope="function")
async def bitcoind(config):
    bitcoind = config.get("bitcoind")
    btcd = BitcoindRPC(bitcoind["rpc_url"], bitcoind["bitcoind_rpc_user"], bitcoind["bitcoind_rpc_password"])
    return btcd

@pytest.fixture(scope="function", autouse=True)
async def funder(config):
    bitcoind = config.get("bitcoind")
    btcd = BitcoindRPC(bitcoind["rpc_url"], bitcoind["bitcoind_rpc_user"], bitcoind["bitcoind_rpc_password"])
    wallet_name = "testwallet"
   
    wallets = (await btcd.listwalletdir())["wallets"]

    print(wallets, file=sys.stderr)

    if not any(wallet["name"] == wallet_name for wallet in wallets):
        await btcd.createwallet(wallet_name, False, False, "", False, True)

    btcd._url=f"{bitcoind['rpc_url']}/wallet/{wallet_name}"
    address = await btcd.getnewaddress()
    #await btcd.generatetoaddress(101, address)

    yield btcd
    pass

@pytest.fixture(scope="function")
async def multisig_wallet_1(config):
    bitcoind = config.get("bitcoind")
    btcd = BitcoindRPC(bitcoind["rpc_url"], bitcoind["bitcoind_rpc_user"], bitcoind["bitcoind_rpc_password"])
    wallet_name = "multisig_wallet_1"

    wallets = (await btcd.listwalletdir())["wallets"]

    if not any(wallet["name"] == wallet_name for wallet in wallets):
        await btcd.createwallet(wallet_name, False, True, "", False, True)

        btcd._url=f"{bitcoind['rpc_url']}/wallet/{wallet_name}"
        wallet = config.get("wallet")
        desc = wallet["desc"]

        request = [
            {
                'desc': desc,
                'active': True,
                'range': [0, 1000],
                'next_index': 0,
                'timestamp': 'now'
            }
        ]

        res = await btcd.importdescriptors(request)
    else:
        btcd._url=f"{bitcoind['rpc_url']}/wallet/{wallet_name}"

    yield btcd
    pass

@pytest.fixture(scope="function")
async def user_wallet_1(config):
    bitcoind = config.get("bitcoind")
    btcd = BitcoindRPC(bitcoind["rpc_url"], bitcoind["bitcoind_rpc_user"], bitcoind["bitcoind_rpc_password"])
    wallet_name = "user_wallet_1"

    wallets = (await btcd.listwalletdir())["wallets"]

    if not any(wallet["name"] == wallet_name for wallet in wallets):
        await btcd.createwallet(wallet_name, False, True, "", False, True)

        btcd._url=f"{bitcoind['rpc_url']}/wallet/{wallet_name}"

        desc = "wsh(and_v(v:pk(tprv8ZgxMBicQKsPd2JjaqU5FBPphchnxPV2fuE53v3TwR1EEYRWcJp4u9oj7E7VeGouzveBssGRrw8QRMevu2oBgPgWVy5CUAz8HU1AFCWnmiQ/0/*),or_d(pk(tpubD6NzVbkrYhZ4WN9NnX8AAbqBiLg2w2Skdma6UCjeXjeHt6d4at2ccWw7z4TRkdP6JzbTHiUn4Cyv8QcztoGXooUsP2Dud1AHLyUsCf1ekPU/0/*),older(12960))))#fj0wq55q"
        request = [
            {'desc': desc, 'active': True, 'range': [0, 1000], 'next_index': 0, 'timestamp': 'now'}
        ]

        await btcd.importdescriptors(request)
    else:
        btcd._url=f"{bitcoind['rpc_url']}/wallet/{wallet_name}"

    yield btcd
    pass


