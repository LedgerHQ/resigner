from typing import Any, List, TypedDict, Optional
import sys
import logging

from .errors import (
    PSBTPartialSignatureCountError,
    UnsafePSBTError,
    InsaneTimelock,
    DuplicateKey,
    IncompatibleDescriptor,
    InvalidDescriptor,
    UtxoError,
)

from .bitcoind_rpc_client import BitcoindRPC, BitcoindRPCError
from .bip380.descriptors import (
    Descriptor,
    WshDescriptor,
    DescriptorParsingError
)

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

def descriptor_analysis(config: Configuration) -> None:
    MIN_LOCKTIME_SECS: int = 7776000  # Minimum time that should elapse before a user can spend without Resigner
    MIN_LOCKTIME_HEIGHT: int = 12960  # Minimum amount of blocks to be created before a user can spend without Resigner
    MAX_LOCKTIME_SECS: int  # Maximum time that should elapse in unixtime(seconds) before a user can spend without Resigner
    MAX_LOCKTIME_HEIGHT:int  # Maximum amount of blocks created before a user can spend without Resigner

    desc = config.get("wallet")["desc"]
    wsh_desc: WshDescriptor = None

    # Example of miniscript policy patterns for use with Resigner
    # and_v(or_c(pk(resigner),v:older(1004)),multi(1,participant_1,participant_2))
    # and_v(v:pk(user),or_d(pk(resigner),older(12960)))

    # We only support p2wsh at this time.
    if desc.startswith("wsh("):
        try:
            wsh_desc = Descriptor.from_str(desc)
        except DescriptorParsingError as e:
            raise InvalidDescriptor(e)
    elif desc.startswith("tr("):
        #TODO: add taproot support
        raise NotImplementedError("taproot support not implemented")
    elif desc.startswith("wpkh("):
        raise IncompatibleDescriptor("Support for wpkh descriptors does not make sense for Resigner")
    else:
        raise InvalidDescriptor(f"Unsupported descriptors format: {desc}")

    # Require atleast 2 keys: Resigner and some other cosigner
    if len(wsh_desc.keys) < 2:
        raise IncompatibleDescriptor("Requires at least 2 keys in descriptor")

    logger.info("wallet descriptor: %s", wsh_desc)
    # Check for duplicate keys
    dupkeys = []
    keys = []
    for key in wsh_desc.keys:
        key_str = str(key)
        if key_str not in keys:
            keys.append(key_str)
        else:
            dupkeys.append(key_str)

    if len(dupkeys) > 0:
        raise DuplicateKey("Duplicate Keys exist in Descriptor: {wsh_desc}\nKeys: {dupkeys}")

    # Atleast one of the keys in the descriptor should be a wildcard, to allow for new addresses
    # to created deterministically. The Xpub corresponding to Resigner's key should be a wildcard key
    #in the form [84h/0h/0h]xpub/0/* or xpub/84h/0h/0h/0/*, so that every participant can generate a new address irrespective
    # of resigner or other participants.
    # Note: Resigners key in the descriptor we import would be an Xpriv, but we pass a descriptor with
    # an xpub to other participants.
    service_key = None  # our key
    for key in wsh_desc.keys:
        if key.derived_from_xpriv:
            service_key = key
            path = service_key.path  # derivation_path()
            if path is None:
                raise IncompatibleDescriptor("Expected Signing key to have a derivation path")
            if not path.kind.is_wildcard():
                raise IncompatibleDescriptor("Signing key derivation path should be a wildcard")
            break;

    if not service_key:
        raise IncompatibleDescriptor("Signing key not in descriptor!")

    # Top-level satisfactions should require a signature. Is this necessary?
    if not wsh_desc.witness_script.needs_sig:
        raise InvalidDescriptor("Top level sats should require signatures")

    # Check that policy is consistent with Resigner policy. Resigner policy requires that
    # 1. No satisfactions that doesn't require the services' signature exist's in the miniscript 
    # 2. Any other satisfactions to the miniscript be on the condition that a relative block count
    #    unix time has elapsed.

    # All second-level nodes? having sats not requiring a signature should be timelocks.
    # We ignore preimages. Those shouldn't be in the second level anyway? 

    # The resigner miniscript can have "andor", "and", "or" top level fragment, hence algorithm
    # for analysing the miniscript is as follows:
    # 1. "andor": if first condition fails, the execute 3rd condition else execute second condition.
    # Hence if service key is in first node or second node, then the third node has the relative lock condition 
    # 2. "and": top level nodes are "or" and "andor". service key and relative lock condition
    # are in the same node fragment
    # 3. "or": top level nodes are "and" and "andor". The rules for the fragment above apply

    def has_service_key(sub):
        for key in sub.keys:
            if key.derived_from_xpriv:
                return True
        return False

    def  get_relative_lock_node(sub):
        if sub.rel_heightlocks or sub.rel_timelocks:
            for sub_l in sub.subs:
                if sub_l.__repr__().startswith("older("):
                    return sub_l
        else:
            return None

    def get_relative_lock_node_andor(sub):
        if sub.__repr__().startswith("andor"):
            if has_service_key(sub.subs[0]) or has_service_key(sub.subs[1]):
                node = get_relative_lock_node(sub.subs[2])
                if not node:
                    return parse_node(sub.subs[2])
                return node
            elif sub.subs[2].rel_timelocks or sub.subs[2].rel_heightlocks:
                return parse_node(sub.subs[2])
            else:
                raise IncompatibleDescriptor("Inconsistent miniscript")

    def get_relative_lock_node_and(sub):
        if sub.__repr__().startswith("and"):
            for sub_l in sub.subs:
                if has_service_key(sub_l) and (sub_l.rel_timelocks or sub_l.rel_heightlocks):
                    if sub_l.__repr__().startswith("andor"):
                        return get_relative_lock_node_andor(sub_l)
                    elif  sub_l.__repr__().startswith("or"):
                        return parse_node(sub_l)
        return None

                        
    def parse_node(node):
        if not node:
            return node

        if node.__repr__().startswith("and_"):
            return get_relative_lock_node_and(node)
        elif node.__repr__().startswith("andor"):
            return get_relative_lock_node_andor(node)
        elif node.__repr__().startswith("or_"):
            # We should avoid such circuitous miniscript
            sub1 = parse_node(node.subs[0])
            sub2 = parse_node(node.subs[1])

            return sub1 if sub1 else sub2
        else:
            if node.__repr__().startswith("older"):
                return node
            elif node.rel_heightlocks or node.rel_timelocks:
                return parse_node(node)

    rel_lock_sub = parse_node(wsh_desc.witness_script)
    if not rel_lock_sub:
        raise IncompatibleDescriptor(f"Could not find the node containing time lock")

    if rel_lock_sub.rel_heightlocks or rel_lock_sub.rel_timelocks:
        if rel_lock_sub.rel_heightlocks:
            if rel_lock_sub.value < MIN_LOCKTIME_HEIGHT:
                raise IncompatibleDescriptor(f"minimum locktime in blocks: {MIN_LOCKTIME_HEIGHT}. "\
                        f"But was set to {rel_lock_sub.value}")
        if rel_lock_sub.rel_timelocks:
            if rel_lock_sub.value < MIN_LOCKTIME_SECS:
                raise IncompatibleDescriptor(f"minimum locktime in seconds: {MIN_LOCKTIME_SECS}. "\
                        "But was set to {rel_lock_sub.value}")
        # Cannot fail now
        if rel_lock_sub.__repr__().startswith("older("):
            config.set(
                {
                    "lock_type": 1 if rel_lock_sub.rel_heightlocks else 2,
                    "lock_value": rel_lock_sub.value
                },
                "wallet"
            )

    key = None
    min_required_sigs = 0
    for sub in wsh_desc.witness_script.subs:
        if not sub.needs_sig:
            if (not sub.rel_timelocks and not sub.rel_heightlocks):
                raise IncompatibleDescriptor(
                    "All second level miniscript node sats should include signatures or be timelocks."
                    )

        if sub.rel_heightlocks or sub.rel_timelocks:
            if len(sub.keys) == 1:
                key = sub.keys[0]
                if key.derived_from_xpriv:
                    if not str(service_key) == str(key):
                        raise IncompatibleDescriptor("There are multiple xprivs in descriptor.")
                    if len(sub.subs) == 2:  # Cannot fail now
                        for sub in sub.subs:
                            if sub.needs_sig:
                                # Minimum no of signature required to satisfy miniscript
                                min_required_sigs += 1
                if sub.needs_sig:
                    # Minimum no of signature required to satisfy miniscript
                    min_required_sigs += 1

    logger.info("Minimum signatures required to satisfy descriptor: %d", min_required_sigs)
    if min_required_sigs > 0:
        config.set({"min_required_sigs": min_required_sigs}, "wallet")


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

    wallet = config.get("wallet")
    lock_value = None
    if "lock_value" in wallet:
        lock_value = wallet["lock_value"] if wallet["lock_type"] == 1 else (wallet["lock_value"]/(60*10))
    # build utxo list
    for utxo in psbt_vin:
        txout =  btd_client.gettxout(utxo["txid"], utxo["vout"])
        if not txout:
            raise UtxoError(f"UTXO txid:{utxo['txid']}, vout: utxo['vout'], appears to have been spent")
        # Get relative lock
        lock_value = lock_value
        tx_utxo = {
                    "txid": utxo["txid"],
                    "vout": utxo["vout"],
                    "value": txout["value"],
                    "safe_to_spend": (txout["confirmations"] >= 6) if not txout["coinbase"] else (txout["confirmations"] >= 100),
                    "can_be_spent_without_resigner": False if lock_value is None else (lock_value >= txout["confirmations"])
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
        
    #self.can_spend_all_utxo

    #num_of_sigs = len(decoded_psbt["partial_signatures"])
    #min_required_sigs = wallet["min_required_sigs"]

    safe_to_sign = all(utxo["safe_to_spend"] for utxo in utxos)
    if not safe_to_sign:
        logger("PSBT: %s...%s contains unconfirmed UTXOS in it's input", psbt[0:9], psbt[-10:])
        raise UnsafePSBTError

    fee = None
    if "fee" in decoded_psbt:
        fee = decoded_psbt["fee"]
    # TODO: check that psbt contain enough signatures, such that we can finalise the psbt with our signature
    # check that the witness script passes with the available signatures
    # we preferably would not return a psbt with the signing service's signature,
    # if the serialised transaction cannot be validated there after.

    # Resigner miniscript has a condition allowing coins to be spent after a certain period of time
    # We shouldn't sign the psbt if the coins can already be spent with resigner and if it contains enough
    # partial signatures to facilitate spends. This would require signing inputs independently which might not
    # be possible with bitcoind 

    return ResignerPsbt(
            psbt,
            utxos,
            third_party_utxos,
            recipient,
            spend_amount*SATS,
            fee,
            safe_to_sign
        )
