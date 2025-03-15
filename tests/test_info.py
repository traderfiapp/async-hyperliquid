from typing import Any, Dict

import pytest


@pytest.mark.asyncio(loop_scope="session")
async def test_metas(async_hyper):
    metas: Dict[str, Any] = async_hyper.metas
    assert "perps" in metas

    perp_metas = metas["perps"]
    assert "universe" in perp_metas

    assert "spots" in metas
    spot_metas = metas["spots"]
    assert "tokens" in spot_metas
    assert "universe" in spot_metas


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "coin, name",
    [
        ("BTC/USDC", "@142"),
        ("HYPE/USDC", "@107"),
        ("PURR/USDC", "PURR/USDC"),
        pytest.param(
            "ETH/USDC",
            None,
            marks=pytest.mark.xfail(
                raises=ValueError, reason="ETH/USDC is not supported"
            ),
        ),
    ],
)
async def test_get_coin_name(async_hyper, coin: str, name: str) -> None:
    coin_name = await async_hyper.get_coin_name(coin)
    assert coin_name == name


@pytest.mark.asyncio(loop_scope="session")
async def test_get_market_price(async_hyper):
    price = await async_hyper.get_market_price("BTC")
    assert price
    price = await async_hyper.get_market_price("BTC/USDC", is_perp=False)
    assert price
