from typing import Optional

from aiohttp import ClientSession
from eth_account import Account

from async_hyperliquid.async_api import AsyncAPI
from async_hyperliquid.utils.miscs import get_timestamp_ms
from async_hyperliquid.utils.types import Endpoint
from async_hyperliquid.utils.signing import sign_action
from async_hyperliquid.utils.constants import MAINNET_API_URL


class ExchangeAPI(AsyncAPI):
    def __init__(
        self,
        account: Account,
        session: ClientSession,
        base_url: Optional[str] = None,
        address: str = None,
    ):
        self.account = account
        self.address = address or account.address
        super().__init__(Endpoint.EXCHANGE, base_url, session)

    async def post_action(
        self, action: dict, vault: Optional[str] = None
    ) -> dict:
        assert self.endpoint == Endpoint.EXCHANGE, (
            "only exchange endpoint supports action"
        )

        nonce = get_timestamp_ms()
        signature = sign_action(
            self.account, action, None, nonce, self.base_url == MAINNET_API_URL
        )
        vault_address = vault if action["type"] != "usdClassTransfer" else None
        payloads = {
            "action": action,
            "nonce": nonce,
            "signature": signature,
            "vaultAddress": vault_address,
        }
        return await self.post(payloads)
