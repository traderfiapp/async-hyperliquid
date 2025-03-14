import os
from typing import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from dotenv import load_dotenv

from async_hyperliquid.async_hyper import AsyncHyper

env_file = Path(".env.local")
load_dotenv(env_file)


@pytest_asyncio.fixture(loop_scope="session")
async def async_hyper() -> AsyncGenerator[AsyncHyper, None]:
    address = os.getenv("HYPER_ADDRESS")
    api_key = os.getenv("HYPER_API_KEY")
    hyper = AsyncHyper(address, api_key)
    try:
        await hyper.init_metas()
        yield hyper
    finally:
        await hyper.close()
