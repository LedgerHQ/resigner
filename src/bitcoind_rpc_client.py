import time
from typing import Any, List, Optional, Union, Literal, Dict

import httpx
import orjson


class BitcoinRPCError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message


class BitcoinRPC:
    """
    Bitcoin RPC client.

    We intend to support only the RPC's we need for this project
    <https://developer.bitcoin.org/reference/rpc/index.html>
    """
    def __init__(self, url: str, rpc_user: str, rpc_password: str, **options: Any):
        self._url = url

        # Configure `httpx.AsyncClient`.
        auth = (rpc_user, rpc_password)
        headers = {"content-type": "application/json"}

        self.client = httpx.AsyncClient(auth=auth, headers=headers)

    async def __async_exit__(self):
        await self.client.aclose()

    async def async_call(self, method: str, params, **kwargs):
        """
        Initiate JSONRPC call.
        """
        req = self.client.post(
            url=self.url,
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
        resp = orjson.loads((await req).content)

        if resp["error"] is not None:
            raise BitcoinRPCError(resp["error"]["code"], resp["error"]["message"])
        else:
            return resp["result"]

    async def getblockchaininfo(self):
        return await self.async_call("getblockchaininfo", [])

    async def getbestblockhash(self):
        return await self.async_call("getbestblockhash", [])

    async def getblockhash(self, height: int):
        return await self.async_call("getblockhash", [height])

    async def getblockcount(self):
        return await self.async_call("getblockcount", [])

    async def getblockheader(self, block_hash: str, verbose: bool = True):
        return await self.async_call("getblockheader", [block_hash, verbose])

    async def getblockstats(self, hash_or_height: Union[int, str], *keys: str, timeout: Optional[float] = 5.0):
        return await self.async_call(
            "getblockstats",
            [hash_or_height, list(keys) or None],
            timeout=httpx.Timeout(timeout),
        )

    async def getblock(self, block_hash: str, verbosity: Literal[0, 1, 2] = 1, timeout: Optional[float] = 5.0):
        return await self.async_call(
            "getblock", [block_hash, verbosity], timeout=httpx.Timeout(timeout)
        )

    async def getrawtransaction(
        self,
        txid: str,
        verbose: bool = True,
        block_hash: Optional[str] = None,
        timeout: Optional[float] = 5.0,
    ):
        return await self.async_call(
            "getrawtransaction",
            [txid, verbose, block_hash],
            timeout=httpx.Timeout(timeout)
        )

    async def createpsbt(
        self,
        inputs: List,
        outputs: List,
        locktime: Optional[int] = 0,
        replaceable: Optional[bool] = False,
        timeout: Optional[float] = 5.0
    ):
        """
        <https://developer.bitcoin.org/reference/rpc/createpsbt.html>
        """

        return await self.async_call(
            "createpsbt",
            [inputs, outputs, locktime, replaceable],
            timeout=httpx.Timeout(timeout)
        )

    async def analysepsbt(self, psbt: str):
        return await self.async_call("analyzepsbt", [psbt])

    async def combinepsbt(self, *psbts):
        return await self.async_call("combinepsbt", psbts)

    async def decodepsbt(self, psbt: str):
        return await self.async_call("decodepsbt", [psbt])

    async def finalisepsbt(self, psbt: str, extract: Optional[bool] = True):
        return await self.async_call("finalizepsbt", [psbt, extract])

    async def joinpsbt(self, *psbts):
        return await self.async_call("joinpsbts", psbts)

    async def utxoupdatepsbt(self, psbt: str, descriptors: Optional[List] = None, timeout: Optional[float] = 5.0):
        result = None
        if not descriptors:
            result = await self.async_call("utxoupdatepsbt", [psbt], timeout=httpx.Timeout(timeout))
        else:
            result = await self.async_call("utxoupdatepsbt", [psbt, descriptors], timeout=httpx.Timeout(timeout))

        return result

    async def walletprocesspsbt(
        self,
        psbt: str,
        sign: Optional[bool] = True,
        sighashtype: Optional[
            Literal[
                "ALL", "NONE", "SINGLE", "ALL|ANYONECANPAY", "NONE|ANYONECANPAY", "SINGLE|ANYONECANPAY"
                ]
            ] = "ALL",
        bip32derivs: Optional[bool] = True,
        timeout: Optional[float] = 5.0
    ):
        """
        <https://developer.bitcoin.org/reference/rpc/walletprocesspsbt.html>
        """
        return await self.async_call(
            "walletprocesspsbt",
            [psbt, sign, sighashtype, bip32derivs],
            timeout=httpx.Timeout(timeout)
        )

    async def gettransaction(
        self,
        txid: str,
        include_watchonly: Optional[bool] = True,  # true for watch-only wallets, otherwise false
        verbose: Optional[bool] = False,
        timeout: Optional[float] = 5.0
    ):
        """
        <https://developer.bitcoin.org/reference/rpc/gettransaction.html>
        """
        return await self.async_call(
            "gettransaction",
            [txid, include_watchonly, verbose],
            timeout=httpx.Timeout(timeout)
            )

    async def getbalance(
        self,
        dummy: Optional[Literal["*"]] = "*",
        minconf: Optional[int] = 0,
        include_watchonly: Optional[bool] = True,  # True for watch-only wallets, otherwise false
        avoid_reuse: Optional[bool] = True  # Only available if avoid_reuse wallet flag is set
    ):
        return await self.async_call(
            "getbalance",
            [dummy, minconf, include_watchonly, avoid_reuse]
        )

    async def getwalletinfo(self):
        return await self.async_call("getwalletinfo", [])

    async def walletlock(self):
        return await self.async_call("walletlock", [])

    async def walletcreatefundedpsbt(
        self,
        outputs: List,
        inputs: Optional[List] = [],
        locktime: Optional[int] = 0,
        options: Optional[Dict] = {},
        bip32derivs: Optional[bool] = True,
        timeout: Optional[float] = 5.0
    ):
        # Todo: Test
        return await self.async_call(inputs, outputs, locktime, options, bip32derivs, timeout=httpx.Timeout(timeout))
