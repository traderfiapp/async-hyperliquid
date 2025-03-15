import logging
from types import TracebackType
from typing import Optional
from traceback import TracebackException

from aiohttp import ClientSession

from async_hyperliquid.utils.constants import MAINNET_API_URL


class AsyncAPI:
    def __init__(
        self, endpoint: str, base_url: str = None, session: ClientSession = None
    ):
        self.endpoint = endpoint
        self.base_url = base_url or MAINNET_API_URL
        self.session = session
        self.logger = logging.getLogger(__name__)

    # for async with AsyncAPI() as api usage
    async def __aenter__(self) -> "AsyncAPI":
        return self

    async def __aexit__(
        self,
        exc_type: Exception,
        exc_val: TracebackException,
        traceback: TracebackType,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()

    async def post(self, payloads: Optional[dict] = None) -> dict:
        payloads = payloads or {}
        req_path = f"{self.base_url}/{self.endpoint.value}"
        self.logger.debug(f"POST {req_path} {payloads}")
        async with self.session.post(req_path, json=payloads) as resp:
            resp.raise_for_status()
            try:
                return await resp.json()
            except Exception as e:
                self.logger.error(f"Error parsing JSON response: {e}")
                return await resp.text()
