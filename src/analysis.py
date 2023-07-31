from typing import Any, List, TypedDict, Optional

from .errors import (
    PSBTPartialSignatureCountError,
    UnsafePSBTError,
    InsaneTimelock,
    DuplicateKey,
    IncompatibleDescriptor,
    InvalidDescriptor
)

from .bitcoind_rpc_client import BitcoindRPC, BitcoindRPCError
from .bip380.descriptors import (
    Descriptor,
    WshDescriptor,
    DescriptorParsingError
)

from .crypto.hd import HDPrivateKey, HDPublicKey
from .config import Configuration
# from psbt import PSBT


def descriptor_analysis(desc: str, config: Configuration) -> None:
    wsh_desc: WshDescriptor = None
    min_secs: int = 7776000  # Minimum time that should elapse before a user can spend without Resigner
    min_blocks: int = 12960  # Minimum amount of blocks to be created before a user can spend without Resigner

    max_secs: int  # Maximum time that should elapse in unixtime(seconds) before a user can spend without Resigner
    max_blocks:int  # Maximum amount of blocks created before a user can spend without Resigner


    # Example of miniscript policy patterns for use with Resigner
    # and_v(or_c(pk(resigner),v:older(1004)),multi(1,participant_1,participant_2))
    # and_v(v:pk(user),or_d(pk(resigner),older(12960)))

    # We only support p2wsh at this time.
    if desc.startswith("wsh(") and desc.endswith(")"):
        try:
            wsh_desc = Descriptor.from_str(desc)
        except DescriptorParsingError as e:
            raise InvalidDescriptor(e)
    elif desc.startswith("tr(") and desc.endswith(")"):
        #TODO: add taproot support
        raise NotImplementedError("taproot support not implemented")
    elif desc_str.startswith("wpkh(") and desc_str.endswith(")"):
        raise IncompatibleDescriptor("Support for wpkh descriptors does not make sense for Resigner")
    else:
        raise InvalidDescriptor(f"Unsupported descriptors format: {desc}")

    # Require atleast 2 keys: Resigner and some other cosigner
    if len(wsh_desc.keys) < 2:
        raise IncompatibleDescriptor("Requires at least 2 keys in descriptor")

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
            path = service_key.derivation_path()
            if path is None:
                raise IncompatibleDescriptor("Expected Signing key to have a derivation path")
            if not path.kind.is_wildcard():
                raise IncompatibleDescriptor("Signing key derivation path should be a wildcard")
            break;

    if not service_key:
        raise IncompatibleDescriptor("Signing key not in descriptor!")

    # Top-level satisfactions should require a signature. Is this necessary?
    if not wsh_desc.needs_sig:
        raise InvalidDescriptor("Top level sats should require signatures")

    # Check that policy is consistent with Resigner policy. Resigner policy requires that
    # 1. No satisfactions that doesn't require the services' signature exist's in the miniscript 
    # 2. Any other satisfactions to the miniscript be on the condition that a relative block count
    #    unix time has elapsed.

    # All second-level nodes? having sats not requiring a signature should be timelocks.
    # We ignore preimages. Those shouldn't be in the second level anyway? 

    # Lookup first-level node to find time_lock or height_lock node
    for sub in wsh_desc.subs:
        if sub.rel_heightlocks or sub.rel_timelocks:
            config.set(
                {
                    "lock_type": 1 if sub.rel_heightlocks else 2,
                    "lock_value": sub.value
                },

                "wallet"
            )

    key = None
    min_required_sigs = 0
    for sub in wsh_desc.subs:
        if not sub.needs_sig:
            if (not sub.rel_timelocks
                or not sub.rel_heightlocks
                or not sub.abs_timelocks
                or not sub.abs_heightlocks
            ):
                raise IncompatibleDescriptor("All second level miniscript node sats should include\
                    signatures or be timelocks.")

        if sub.rel_heightlocks or sub.rel_timelocks:
            if len(sub.keys) == 1:
                key = sub.keys[0]
                if key.derived_from_xpriv:
                    if not str(service_key) == str(key):
                        raise IncompatibleDescriptor("There are multiple xprivs in descriptor.")
                    if len(sub.subs) == 2:  # Cannot fail now
                        for sub in sub.subs:
                            if sub.rel_heightlocks or sub.rel_timelocks:
                                if sub.rel_heightlocks:
                                    if sub.value < min_secs:
                                        raise IncompatibleDescriptor("minimum nsequence in seconds: {min_secs}.\
                                            But was set to {sub}")
                                if sub.rel_timelocks:
                                    if sub.value < min_blocks:
                                        raise IncompatibleDescriptor("minimum nsequence in seconds: {min_blocks}.\
                                            But was set to {sub}")
                            if sub.needs_sig:
                                # Minimum no of signature required to satisfy miniscript
                                min_required_sigs += 1
                if sub.needs_sig:
                    # Minimum no of signature required to satisfy miniscript
                    min_required_sigs += 1 
    if min_required_sigs > 0:
        config.set({"min_required_sigs": min_required_sigs}, "wallet")


class Utxos(TypedDict):
    txid: str
    vout: int
    value: int
    partial_signatures: List
    hex: str
    # Extra information for signer?
    can_be_spent_without_resigner: bool
    safe_to_spend: bool


class Recipient(TypedDict):
    address: List
    value: int


class ResignerPsbt:
    psbt_str: str
    utxos: List[Utxos] = []  # Utxos we control
    third_party_utxos: List[Utxos] = []
    recipient: List[Recipient] = []
    fee: int
    can_spend_all_utxo: bool  # if we control a part of the signatures required to spend the utxo 
    can_finalise_transaction: bool  # If Psbt contains enough signatures to be spent after we sign 

    def __init__(
        self,
        psbt: str,
        utxos: Utxos,
        third_party_utxos: Utxos,
        recipient: Recipient,
        amount_sats: int,
        fee: int
    ):
        self.psbt_str = psbt
        self.utxos = utxos
        self.third_party_utxos = third_party_utxos
        self.recipient = recipient
        self.amount_sats = amount_sats
        self.fee = fee



async def analyse_psbt_from_base64_str(psbt: str, config: Configuration) -> ResignerPsbt:
    bitcoind = config.get("bitcoind")
    btdc = BitcoindRPC(
        bitcoind["rpc_url"],
        bitcoind["bitcoind_rpc_user"],
        bitcoind["bitcoind_rpc_password"]
    )

    decoded_psbt = btdc.decodepsbt(psbt)
    analysed_psbt = btdc.analysepsbt(psbt)
    psbt_vin = decoded_psbt["tx"]["vin"]
    psbt_inputs = decoded_psbt["input"]

    utxos: List[Utxos] = []  # Utxos we control
    third_party_utxos: List[Utxos] = []
    recipient: List[Recipient] = []

    wallet = config.get("wallet")

    # build utxo list
    for utxo, tx_input in psbt_vin, psbt_inputs:
        txout = btdc.gettxout(utxo.txid, utxo.vout)
        
        # Ensure lock value is in blocks
        lock_value = wallet["lock_value"] if wallet["lock_type"] == 1 else (wallet["lock_value"]/(60*10))
        
        tx_utxo = {
                    "txid": utxo.txid,
                    "vout": utxo.vout,
                    "value": txout["value"],
                    "safe_to_spend": (txout["confirmations"] >= 6) if not txout["coinbase"] else (txout["confirmations"] >= 100),
                    "can_be_spent_without_resigner": (lock_value >= txout["confirmations"])
        }

        # Todo: make this work with deterministic addresses
        if txout["scriptPubKey"]["address"] == config.get("wallet")["address"]:
                utxos.append(tx_utxo)
        else:
                third_party_utxos.append(tx_utxo)

    # Get receipients
    spend_amount = 0
    psbt_vout = decoded_psbt["tx"]["vout"]
    for vout in psbt_vout:
        spend_amount += vout["value"]
        recipient = {
            "address": vout["scriptPubKey"]["addresses"][0],  # Some vout contain multiple addresses; we expect only one.
            "value": vout["value"]
        }
        recipient.append(recipient)

        
    #self.can_spend_all_utxo

    num_of_sigs = len(decoded_psbt["partial_signatures"])
    min_required_sigs = wallet["min_required_sigs"]

    safe_to_sign = False if not min_required_sigs else num_of_sigs >= min_required_sigs
    if not safe_to_sign:
        raise UnsafePSBTError

    # TODO: check that psbt contain enough signatures, such that we can finalise the psbt with our signature
    # check that the witness script passes with the available signatures
    # we preferably would not return a psbt with the signing service's signature,
    # if the serialised transaction cannot be validated there after.

    # Resigner miniscript has a condition allowing coins to be spent after a certain period of time
    # We shouldn't sign the psbt if the coins can already be spent with resigner and if it contains enough
    # partial signatures to facilitate spends. This would require signing inputs independently which might not
    # be possible with bitcoind 

    return ResignerPsbt(psbt, utxos, third_party_utxos, recipient,spend_amount*100000000, decoded_psbt["fee"])
