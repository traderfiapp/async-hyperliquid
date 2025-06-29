import os
from typing import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from dotenv import load_dotenv

from async_hyperliquid.async_hyper import AsyncHyper

env_file = Path(".env.local")
load_dotenv(env_file)


@pytest_asyncio.fixture(loop_scope="session")
async def hl() -> AsyncGenerator[AsyncHyper, None]:
    address = os.getenv("HL_ADDR", "")
    api_key = os.getenv("HL_AK", "")
    is_mainnet = os.getenv("IS_MAINNET", "true").lower() == "true"
    hl = AsyncHyper(address, api_key, is_mainnet)
    try:
        await hl.init_metas()
        yield hl
    finally:
        await hl.close()
