import time
from typing import Any, List, Optional, Union, Literal, Dict

import httpx
import orjson


class BitcoindRPCError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message


class BitcoindRPC:
    """
    Bitcoin RPC client.

    We intend to support only the RPC's we need for this project
    <https://developer.bitcoin.org/reference/rpc/index.html>
    """
    def __init__(self, url: str, rpc_user: str, rpc_password: str, **options: Dict):
        self._url = url

        # Configure `httpx.AsyncClient`.
        auth = (rpc_user, rpc_password)
        headers = {"content-type": "application/json"}
        timeout = httpx.Timeout(10.0, read=100)
        limits = httpx.Limits(max_keepalive_connections=0, max_connections=None, keepalive_expiry=0)
        self.client = httpx.Client(auth=auth, headers=headers, timeout=timeout, limits=limits)


    def _exit_(self):
        self.client.close()

    def call(self, method: str, params, **kwargs):
        """
        Initiate JSONRPC call.
        """
        response = self.client.post(
            url=self._url,
            content=orjson.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": int(time.time()),  # Todo: verify id to match the response with the request
                    "method": method,
                    "params": params,
                }
            ),
            **kwargs,
        )
        response_content = orjson.loads(response.content or response._content)

        # close the connection pool
        #self._exit_()
        if response_content["error"] is not None:
            raise BitcoindRPCError(response_content["error"]["code"], response_content["error"]["message"])
        else:
            return response_content["result"]

    def stop(self):
        return self.call("stop", [])

    def getblockchaininfo(self):
        return self.call("getblockchaininfo", [])

    def getbestblockhash(self):
        return self.call("getbestblockhash", [])

    def getblockhash(self, height: int):
        return self.call("getblockhash", [height])

    def getblockcount(self):
        return self.call("getblockcount", [])

    def getblockheader(self, block_hash: str, verbose: bool = True):
        return self.call("getblockheader", [block_hash, verbose])

    def getblockstats(self, hash_or_height: Union[int, str], *keys: str):
        return self.call(
            "getblockstats",
            [hash_or_height, list(keys) or None],
        )

    def getblock(self, block_hash: str, verbosity: Literal[0, 1, 2] = 1):
        return self.call(
            "getblock", [block_hash, verbosity]
        )

    def gettxout(self, txid: str, n: int, include_mempool: Optional[bool] = True):
        return self.call(
            "gettxout",
            [txid, n, include_mempool]
        )

    def listsinceblock(
        self,
        block_hash: str,
        target_confirmations: Optional[int] = 1,
        include_watchonly: Optional[bool] = True,
        include_removed: Optional[bool] = True
    ):
        return self.call(
            "listsinceblock",
            [block_hash, target_confirmations, include_watchonly, include_removed]
        )

    def listunspent(
        self,
        minconf: Optional[int] = 1,
        maxconf: Optional[int] = 9999999,
        addresses: Optional[List] = None,
        query_options: Optional[Dict] = None,
    ):
        return self.call(
            "listunspent",
            [minconf, maxconf, addresses, query_options]
        )

    def scanblocks(
        self,
        action: Literal["start", "stop", "status"],
        scanobjects: Optional[List] = None,
        start_height: Optional[int] = 0,
        stop_height: Optional[int] = None,
        filtertype: Optional[str] = "basic",
        options: Optional[Dict] = None
    ):
        return self.call(
            "scanblocks",
            [action, scanobjects, start_height, stop_height, filtertype, options]
        )

    def getbalance(
        self,
        dummy: Optional[Literal["*"]] = "*",
        minconf: Optional[int] = 0,
        include_watchonly: Optional[bool] = False,  # True for watch-only wallets, otherwise false
        avoid_reuse: Optional[bool] = False  # Only available if avoid_reuse wallet flag is set
    ):
        return self.call(
            "getbalance",
            [dummy, minconf, include_watchonly, avoid_reuse]
        )

    def getwalletinfo(self):
        return self.call("getwalletinfo", [])

    def gettransaction(
        self,
        txid: str,
        include_watchonly: Optional[bool] = True,  # true for watch-only wallets, otherwise false
        verbose: Optional[bool] = False
    ):
        """
        <https://developer.bitcoin.org/reference/rpc/gettransaction.html>
        """
        return self.call(
            "gettransaction",
            [txid, include_watchonly, verbose]
        )

    def getrawtransaction(
        self,
        txid: str,
        verbose: bool = True,
        block_hash: Optional[str] = None,
    ):
        return self.call(
            "getrawtransaction",
            [txid, verbose, block_hash]
        )

    def generatetoaddress(self, nblocks: int, address: str, matrixes: Optional[int]=1000000):
        return self.call(
            "generatetoaddress",
            [nblocks, address, matrixes]
        )

    def createpsbt(
        self,
        inputs: List,
        outputs: List,
        locktime: Optional[int] = 0,
        replaceable: Optional[bool] = False
    ):
        """
        <https://developer.bitcoin.org/reference/rpc/createpsbt.html>
        """

        return self.call(
            "createpsbt",
            [inputs, outputs, locktime, replaceable]
        )

    def walletcreatefundedpsbt(
        self,
        outputs: List,
        inputs: Optional[List] = [],
        locktime: Optional[int] = 0,
        options: Optional[Dict] = {},
        bip32derivs: Optional[bool] = True
    ):
        # Todo: Test
        return self.call(
            "walletcreatefundedpsbt",
            [inputs, outputs]
        )

    def analysepsbt(self, psbt: str):
        return self.call("analyzepsbt", [psbt])

    def combinepsbt(self, *psbts):
        return self.call("combinepsbt", psbts)

    def decodepsbt(self, psbt: str):
        return self.call("decodepsbt", [psbt])

    def finalisepsbt(self, psbt: str, extract: Optional[bool] = True):
        return self.call("finalizepsbt", [psbt, extract])

    def joinpsbt(self, *psbts):
        return self.call("joinpsbts", psbts)

    def utxoupdatepsbt(
        self,
        psbt: str,
        descriptors: Optional[List] = None
    ):
        result = None
        if not descriptors:
            result = self.call("utxoupdatepsbt", [psbt])
        else:
            result = self.call("utxoupdatepsbt", [psbt, descriptors])

        return result

    def walletprocesspsbt(
        self,
        psbt: str,
        sign: Optional[bool] = True,
        sighashtype: Optional[
            Literal[
                "ALL", "NONE", "SINGLE", "ALL|ANYONECANPAY", "NONE|ANYONECANPAY", "SINGLE|ANYONECANPAY"
                ]
            ] = "ALL",
        bip32derivs: Optional[bool] = True
    ):
        """
        <https://developer.bitcoin.org/reference/rpc/walletprocesspsbt.html>
        """
        return self.call(
            "walletprocesspsbt",
            [psbt, sign, sighashtype, bip32derivs]
        )

    def createwallet(
        self,
        wallet_name: str,
        disable_private_keys: Optional[bool] = False,
        blank: Optional[bool] = False,
        passphrase: Optional[str] = "",
        avoid_reuse: Optional[bool] = False,
        descriptors: Optional[bool] = False,
        load_on_startup: Optional[bool] = False 
    ):
        return self.call(
            "createwallet",
            [
                wallet_name,
                disable_private_keys,
                blank,
                passphrase,
                avoid_reuse,
                descriptors,
                load_on_startup
            ]
        )

    def importaddress(
        self,
        address: str,
        label: Optional[str] = None,
        rescan: Optional[bool] = True,
        p2sh: Optional[bool] = False
    ):
        return self.call("importaddress", [address, label, rescan, p2sh])

    def importmulti(self, request: List, options: Optional[Dict] = None):
        return self.call("importmulti", [request, options])

    def importdescriptors(self, request: List):
        return self.call("importdescriptors", [request])

    def getnewaddress(self,
        label: Optional[str] = None,
        address_type: Optional[Literal["legacy, p2sh-segwit", "bech32"]] = None
    ):
        return self.call(
            "getnewaddress",
            [label, address_type]  # TODO: figure out some way to set -rpcwallet
        )

    def getaddressinfo(self, address: str):
        return self.call("getaddressinfo", [address])

    def listwallets(self):
        return self.call("listwallets", [])

    def listwalletdir(self):
        return self.call("listwalletdir", [])

    def listreceivedbyaddress(
        self,
        minconf: Optional[int] = 1,
        include_empty: Optional[bool] = False,
        include_watchonly: Optional[bool] = True,
        address_filter: Optional[str] = None
    ):
        return self.call(
            "listreceivedbyaddress",
            [minconf, include_empty, include_watchonly, address_filter]
        )

    def walletlock(self):
        return self.call("walletlock", [])

    def sendtoaddress(
        self,
        address: str,
        amount: int,
        comment: Optional[str] = "",
        comment_to: Optional[str] = "",
        subtractfeefromamount: Optional[bool] = False,  # default=False
        replaceable: Optional[bool] = True,
        conf_target: Optional[int] = None,
        estimate_mode: Optional[Literal["unset", "economical", "conservative"]] = "unset",  # default="unset"
        avoid_reuse: Optional[bool] = False,
        fee_rate: Optional[int] = None
    ):
        return self.call(
            "sendtoaddress",
            [
                address,
                amount,
                comment,
                comment_to,
                subtractfeefromamount,
                replaceable,
                conf_target,
                estimate_mode,
                avoid_reuse,
                fee_rate
            ]
        )

    def sendrawtransaction(self, hexstring: str, maxfeerate: Optional[Union[int, str]]=0.10):
        return self.call("sendrawtransaction", [hexstring, maxfeerate])