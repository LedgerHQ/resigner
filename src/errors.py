from typing import Any, Optional

class NotImplementedError(Exception):
    def __init__(self, msg: Optional[str]= "Feature NotImplemented"):
        self.message = msg


class PSBTSerializationError(Exception):
    def __init__(self, msg: Optional[str] = "Failed to serialise psbt"):
        self.message = msg 


class BadArgumentError(Exception):
    def __init__(self, msg: Optional[str], arg: Any):
        self.message = msg


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


class PSBTError(Exception):
    pass


class UnsafePSBTError(PSBTError):
    def __init__(self, message = "PSBT failed to meet requirements for signing"):
        self.message = message


class PSBTPartialSignatureCountError(PSBTError):
    def __init__(self, message = "PSBT contains fewer partial signatures than required"):
        self.message = message

class UtxoError(PSBTError):
    def __init__(self, message = "UTXO not found in mempool"):
        self.message = message

class ServerError(Exception):
    def __init__(self, message):
        self.message = message
