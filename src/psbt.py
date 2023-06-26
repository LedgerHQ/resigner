from typing import TypedDict, List

from config import Configuration
from bitcoind_rpc_client import BitcoindRPC, BitcoindRPCError

class Utxos(TypedDict):
    txid: str
    vout: int
    value: int

    # Extra information for signer?
    can_spend: bool
    safe_to_spend: bool


class Recipient(TypedDict):
    address: List
    value: int


class Psbt:
    _psbt: str
    _config: Configuration
    utxos: List[Utxos]
    recipient: List[Recipient]
    can_spend_all_utxo: bool  # if we control a part of the signatures required to spend the utxo 
    contains_partial_signature: bool  # Whether there are existing signatures in the psbt
    can_finalise_transaction: bool  # If Psbt contains enough signatures to be spent after we sign
    safe_to_sign: bool  #

    def __init__(self, psbt: str, config: Configuration):
        self._psbt = psbt
        self._config = config

        self._btdc = BitcoindRPC(config.get("bitcoind_config")["url"], config["bitcoind_rpc_user"], config["bitcoind_rpc_password"])

    def analyse(self):
        dec_psbt = btdc.decodepsbt(self._psbt)

        # TODO:
        pass 