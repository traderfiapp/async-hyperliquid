from typing import Optional

from aiohttp import ClientSession
from eth_account import Account

from async_hyper.async_api import AsyncAPI
from async_hyper.utils.types import Endpoint


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
        self, action: dict, signature: str, nonce: int
    ) -> dict:
        assert self.endpoint == Endpoint.EXCHANGE, (
            "only exchange endpoint supports action"
        )

        # TODO: to support vault address
        payloads = {
            "action": action,
            "nonce": nonce,
            "signature": signature,
            "vaultAddress": None,  # vault_address if action["type"] != "usdClassTransfer" else None
        }
        return await self.post(payloads)
