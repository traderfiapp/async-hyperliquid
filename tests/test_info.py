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
        ("@142", "@142"),
        ("UBTC/USDC", "@142"),
        ("UBTC", "@142"),
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
@pytest.mark.parametrize(
    "coin, symbol",
    [
        ("BTC", "BTC"),
        ("BTC/USDC", "BTC/USDC"),
        ("@142", "BTC/USDC"),
        ("@107", "HYPE/USDC"),
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
async def test_get_coin_symbol(async_hyper, coin: str, symbol: str) -> None:
    coin_symbol = await async_hyper.get_coin_symbol(coin)
    assert coin_symbol == symbol


@pytest.mark.asyncio(loop_scope="session")
async def test_get_market_price(async_hyper):
    price = await async_hyper.get_market_price("BTC")
    assert price
    price = await async_hyper.get_market_price("BTC/USDC")
    assert price


@pytest.mark.asyncio(loop_scope="session")
async def test_get_all_market_prices(async_hyper):
    prices = await async_hyper.get_all_market_prices()
    assert isinstance(prices, dict)
    assert "@142" in prices


@pytest.mark.asyncio(loop_scope="session")
async def test_abcdefg(async_hyper):
    coin_names = async_hyper.coin_names
    for k, v in coin_names.items():
        asset = await async_hyper.get_coin_asset(k)
        symbol = await async_hyper.get_coin_symbol(k)
        coin_name1 = await async_hyper.get_coin_name(k)
        coin_name2 = await async_hyper.get_coin_name(v)
        assert coin_name1 == coin_name2
        print(k, v, asset, symbol, coin_name1, coin_name2)
