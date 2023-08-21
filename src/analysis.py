from typing import Any, List, TypedDict, Optional
import sys
import logging

from .errors import (
    PSBTPartialSignatureCountError,
    UnsafePSBTError,
    UtxoError,
)

from .bitcoind_rpc_client import BitcoindRPC, BitcoindRPCError
from .crypto.hd import HDPrivateKey, HDPublicKey
from .config import Configuration
from .models import (
    Utxos,
    SpentUtxos,
    SignedSpends,
    AggregateSpends
)

SATS = 100000000

logger = logging.getLogger("resigner")

class UtxosType(TypedDict):
    txid: str
    vout: int
    value: int
    hex: str
    # Extra information for signer?
    can_be_spent_without_resigner: bool
    safe_to_spend: bool


class RecipientType(TypedDict):
    address: List
    value: int
    is_changeaddress: bool
    ismine: bool


class ResignerPsbt:
    psbt_str: str
    utxos: List[UtxosType] = []  # Utxos we control
    third_party_utxos: List[UtxosType] = []
    recipient: List[RecipientType] = []
    fee: int
    can_spend_all_utxo: bool  # if we control a part of the signatures required to spend the utxo 
    can_finalise_transaction: bool  # If Psbt contains enough signatures to be spent after we sign 
    safe_to_sign: bool
    def __init__(
        self,
        psbt: str,
        utxos: UtxosType,
        third_party_utxos: UtxosType,
        recipient: RecipientType,
        amount_sats: int,
        fee: int,
        safe_to_sign: Optional[bool] = False
    ):
        self.psbt_str = psbt
        self.utxos = utxos
        self.third_party_utxos = third_party_utxos
        self.recipient = recipient
        self.amount_sats = amount_sats
        self.fee = fee
        self.safe_to_sign = safe_to_sign



def analyse_psbt_from_base64_str(psbt: str, config: Configuration) -> ResignerPsbt:
    btd_client = config.get("bitcoind")["client"]
    btd_change_client = config.get("bitcoind")["change_client"]

    decoded_psbt =  btd_client.decodepsbt(psbt)
    psbt_vin = decoded_psbt["tx"]["vin"]

    # for key, value in decoded_psbt["tx"].items():
    
    utxos: List[Utxos] = []  # Utxos we control
    third_party_utxos: List[Utxos] = []
    recipient: List[Recipient] = []

    # build utxo list
    for utxo in psbt_vin:
        txout =  btd_client.gettxout(utxo["txid"], utxo["vout"])
        if not txout:
            logger.error(f"UTXO txid:{utxo['txid']}, vout: {utxo['vout']}, appears to have been spent")
            raise UtxoError(utxo["txid"], utxo["vout"])
        # Get relative lock
        tx_utxo = {
                    "txid": utxo["txid"],
                    "vout": utxo["vout"],
                    "value": txout["value"],
                    "safe_to_spend": (txout["confirmations"] >= 6) if not txout["coinbase"] else (txout["confirmations"] >= 100)
        }

        # Check that the utxo is in the db.
        # TODO: We should check that the utxo isn't really ours, just incase we aren't completely synced with the blockchain
        coin = Utxos.get([], {"txid": utxo["txid"], "vout": utxo["vout"]})
        if coin:
            utxos.append(tx_utxo)
            # Check if tx is replaces an already signed but uncomfirmed tx (some version of Replace-by-fee(RBF))
            spentutxo = SpentUtxos.get([], {"txid": utxo["txid"], "vout": utxo["vout"]})
            if spentutxo:
                SpentUtxos.delete({"psbt_id": spentutxo[0]["psbt_id"]})
                prv_signed_psbt = SignedSpends.get([], {"id": spentutxo[0]["psbt_id"]})
                logger.info("PSBT: %s...%s replaces a previously signed psbt: %s...%s",\
                    psbt[0:9], psbt[-10:], prv_signed_psbt["signed_psbt"][0:9], prv_signed_psbt["signed_psbt"][-10:])
                if prv_signed_psbt:
                    SignedSpends.delete({"id": spentutxo[0]["psbt_id"]})
                    agg_spend = AggregateSpends.get([])[0]
                    AggregateSpends.update(
                        {
                            "unconfirmed_daily_spends": agg_spend["unconfirmed_daily_spends"] - prv_signed_psbt[0]["amount_sats"],
                            "unconfirmed_weekly_spends": agg_spend["unconfirmed_weekly_spends"] - prv_signed_psbt[0]["amount_sats"],
                            "unconfirmed_monthly_spends": agg_spend["unconfirmed_monthly_spends"] - prv_signed_psbt[0]["amount_sats"]
                        }
                    )

        else:
            third_party_utxos.append(tx_utxo)

    # Get receipients
    spend_amount = 0
    psbt_vout = decoded_psbt["tx"]["vout"]
    for vout in psbt_vout:
        address = vout["scriptPubKey"]["address"]
        addr_info = btd_client.getaddressinfo(address)
        ismine = addr_info["ismine"]
        is_changeaddress = False

        if not addr_info["ismine"]:
            changeaddr_info = btd_change_client.getaddressinfo(address)
            if changeaddr_info["ismine"]:
                logger.info("address: %s is a change address", address)
                is_changeaddress = True
                ismine = True
            else:
                spend_amount += vout["value"]

        recv = {
            "address": address,  # Some vout contain multiple addresses; we expect only one.
            "value": vout["value"],
            "is_changeaddress": is_changeaddress,
            "ismine": ismine
        }
        recipient.append(recv)

    safe_to_sign = all(utxo["safe_to_spend"] for utxo in utxos)
    if not safe_to_sign:
        logger("PSBT: %s...%s contains unconfirmed UTXOS in it's input", psbt[0:9], psbt[-10:])
        raise UnsafePSBTError(psbt, "PSBT contains unconfirmed or unsafe UTXOS in it's input")

    fee = None
    if "fee" in decoded_psbt:
        fee = decoded_psbt["fee"]

    return ResignerPsbt(
            psbt,
            utxos,
            third_party_utxos,
            recipient,
            spend_amount*SATS,
            fee,
            safe_to_sign
        )
