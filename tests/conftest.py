import os

import pytest

from ..src.bitcoind_rpc_client import BitcoindRPC, BitcoindRPCError

@pytest.fixture(scope="session", params=["http://127.0.0.1:18443"])
def bitcoind_rpc_client(request)
    rpcuser = os.getenv('RESIGNER_RPC_USER')
    rpcpassword = os.getenv('RESIGNER_RPC_PASSWORD')
    pass