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


class PSBTError(Exception):
    pass


class UnsafePSBTError(PSBTError):
    def __init__(self, psbt: str, message = "PSBT failed to meet requirements for signing"):
        self.message = message
        self.psbt = psbt


class PSBTPartialSignatureCountError(PSBTError):
    def __init__(self, message = "PSBT contains fewer partial signatures than required"):
        self.message = message


class UtxoError(PSBTError):
    def __init__(self, txid: str, vout: int, message: str = None):
        self.message = message or "UTXO specified in the input appears to have been spent"
        self.txid = txid
        self.vout = vout


class ServerError(Exception):
    def __init__(self, message):
        self.message = message


class DBError(Exception):
    def __init__(self, message):
        self.message = message