import time
from typing import Any, List, Optional, Type, Union

import httpx
import orjson


class BitcoinRPC:
    """
    Bitcoin RPC client.

    We intend to support only the RPC's we need for this project
    """

    def __init__(self, url: str, rpc_user: str, rpc_password: str, **options: Any):
        self._url = url
        
        #Configure `httpx.AsyncClient`. 
        auth = (rpc_user, rpc_password)
        headers = {"content-type": "application/json"}

        self.client = httpx.AsyncClient(auth=auth, headers=headers)


    async def __async_exit__():
        await self.client.aclose()

    async def async_call(self, method: str, params):
        """
        Initiate JSONRPC call.
        """
        req = self.client.post(
            url=self.url,
            content=orjson.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": int(time.time()), # Todo: verify id to match the response with the request
                    "method": method,
                    "params": params,
                }
            ),
            **kwargs,
        )
        resp = orjson.loads((await req).content)

        if resp["error"] is not None:
            raise RPCError(resp["error"]["code"], resp["error"]["message"])
        else:
            return resp["result"]

    async def getblockchaininfo(self):
        return await self.async_call("getblockchaininfo", [])

    async def getbestblockhash(self) -> BestBlockHash:
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

    async def getrawtransaction(self, txid: str,
        verbose: bool = True,
        block_hash: Optional[str] = None,
        timeout: Optional[float] = 5.0,
    ):
        return await self.async_call(
            "getrawtransaction",
            [txid, verbose, block_hash],
            timeout=httpx.Timeout(timeout))

    async def analysepsbt(self,):
        pass

    async def combinepsbt(self,):
        pass

    async def decodepsbt(self,):
        pass

    async def finalisepsbt(self,):
        pass

    async def joinpsbt(self,):
        pass

    async def utxoupdate(self,):
        pass

    async def processpsbt(self,):
        pass


