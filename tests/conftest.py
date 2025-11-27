import os
from typing import AsyncGenerator

import pytest_asyncio

from async_hyperliquid import AsyncHyperliquid


def get_is_mainnet() -> bool:
    from dotenv import load_dotenv
    from pathlib import Path

    env_file = Path(".env.local")
    load_dotenv(env_file)
    return os.getenv("IS_MAINNET", "true").lower() == "true"


@pytest_asyncio.fixture(loop_scope="session")
async def hl() -> AsyncGenerator[AsyncHyperliquid, None]:
    address = os.getenv("HL_ADDR", "")
    api_key = os.getenv("HL_AK", "")
    is_mainnet = get_is_mainnet()
    hl = AsyncHyperliquid(address, api_key, is_mainnet)
    try:
        await hl.init_metas()
        yield hl
    finally:
        await hl.close()
