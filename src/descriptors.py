from typing import Any, List, Optional

from bitcoind_rpc_client import BitcoindRPC, BitcoindRPCError
from bip380.descriptors import Descriptor, WshDescriptor, SatisfactionMaterial, DescriptorParsingError
from crypto.hd import HDPrivateKey, HDPublicKey


class DescriptorError(Exception):
    pass


class InsaneTimelock(DescriptorError):
    def __init__(self, message = "Timelock specified in miniscript is unreasonable"):
        self.message = message


class DuplicateKey(DescriptorError):
    def __init__(self, message="Duplicate keys exist in Descriptor"):
        self.message = message


class IncompatibleDescriptor(DescriptorError):
    def __init__(self, message="Descriptor policy specified is incompatible with Resigner"):
        self.message = message


class InvalidDescriptor(DescriptorError):
    """Basically every other error generated from bip380"""

    def __init__(self, message):
        self.message = message


def descriptor_analysis(desc: str):
    wsh_desc: WshDescriptor = None

    # We only support p2wsh at this time.
    if desc.startswith("wsh(") and desc.endswith(")"):
        wsh_desc = Descriptor.from_str(desc)
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
    for key in wsh_desc:
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

    # Check that policy is consistent with Resigner policy. Resigner policy requires that
    # 1. No satisfactions that doesn't require the services' key exist in the miniscript 
    # 2. Any other satisfactions to the miniscript be on the condition that a relative block count
    #    unix time has elapsed.

    # Top-level satisfactions should require a signature. Is this necessary?
    if not wsh_desc.needs_sig:
        raise InvalidDescriptor("Top level sats should require signatures")

    # All second-level nodes? having sats not requiring a signature should be timelocks.
    # We ignore preimages. Those shouldn't be in the second level anyway? 

    for sub in wsh_desc.subs:
        if not sub.needs_sig:
            if (not sub.rel_timelocks
                or not sub.rel_heightlocks
                or not sub.abs_timelocks
                or not sub.abs_heightlocks
            ):
            raise IncompatibleDescriptor("All second level miniscript node sats should include\
                signatures or be timelocks.")

