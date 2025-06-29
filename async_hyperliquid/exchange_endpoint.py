from typing import Any

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
        base_url: str | None = None,
        address: str | None = None,
    ):
        self.account = account
        self.address = address or account.address  # type: ignore
        super().__init__(Endpoint.EXCHANGE, base_url, session)

    async def post_action(
        self,
        action: Any,
        *,
        vault: str | None = None,
        expires: int | None = None,
    ) -> Any:
        assert self.endpoint == Endpoint.EXCHANGE, (
            "only exchange endpoint supports action"
        )

        nonce = get_timestamp_ms()
        signature = sign_action(
            self.account, action, None, nonce, self.base_url == MAINNET_API_URL
        )
        return await self.post_action_with_sig(
            action, signature, nonce, vault=vault, expires=expires
        )

    async def post_action_with_sig(
        self,
        action: Any,
        sig: Any,
        nonce: int,
        *,
        vault: str | None = None,
        expires: int | None = None,
    ) -> Any:
        payloads = {"action": action, "nonce": nonce, "signature": sig}
        if vault:
            payloads["vaultAddress"] = vault
        if expires:
            payloads["expiresAfter"] = expires
        self.logger.debug(f"Post action payloads: {payloads}")
        return await self.post(payloads)
