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
    utxos: List[Utxos] = []  # Utxos we control
    third_party_utxos: List[Utxos] = []
    recipient: List[Recipient] = []
    fee: int
    can_spend_all_utxo: bool  # if we control a part of the signatures required to spend the utxo 
    contains_partial_signature: bool  # Whether there are existing signatures in the psbt
    can_finalise_transaction: bool  # If Psbt contains enough signatures to be spent after we sign
    safe_to_sign: bool  

    def __init__(self, psbt: str, config: Configuration):
        self._psbt = psbt
        self._config = config

        bitcoin_conf = config.get("bitcoind")
        self._btdc = BitcoindRPC(
            bitcoin_conf["rpc_url"],
            bitcoin_conf["rpc_user"],
            bitcoin_conf["rpc_password"]
        )

    def analyse(self):
        decoded_psbt = self._btdc.decodepsbt(self._psbt)
        decoded_psbt = self._btdc.analysepsbt(self._psbt)
        psbt_vin = decoded_psbt["tx"]["vin"]

        # build utxo list
        for utxo in psbt_vin:
            txout = self._btdc.gettxout(utxo.txid, utxo.vout)

            tx_utxo = {
                        "txid": utxo.txid,
                        "vout": utxo.vout,
                        "value": txout["value"]
                        "safe_to_spend": txout["confirmations"] >= 6 if not txout["coinbase"] else txout["confirmations"] >= 100
                    }

            if txout["scriptPubKey"]["address"] == self._config.get("wallet")["address"]:
                self.utxos.append(tx_utxo)
            else:
                self.third_party_utxos.append(tx_utxo)

        # Get receipients

        psbt_vout = decoded_psbt["tx"]["vout"]
        for vout in psbt_vout:
            recipient = {
                "address": vout["scriptPubKey"]["addresses"][0],  # Some vout contain multiple addresses; we expect only one.
                "value": vout["value"]
            }
            self.recipient.append(recipient)

        
        #self.can_spend_all_utxo

        num_of_sigs = len(decoded_psbt["partial_signatures"])
        self.contains_partial_signature = num_of_sigs > 0

        # TODO: check that psbt contain enough signatures, such that we can finalise the psbt with our signature
        # check that the witness script passes with the available signatures
        # we preferably would not return a psbt with the signing service's signature,
        # if the serialised transaction cannot be validated there after.