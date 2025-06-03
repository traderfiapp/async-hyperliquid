import time
from typing import Any, Dict

import pytest
import json

from async_hyperliquid.utils.types import OrderWithStatus


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
async def test_coin_utils(async_hyper):
    # coin_names = async_hyper.coin_names
    # for k, v in coin_names.items():
    #     asset = await async_hyper.get_coin_asset(k)
    #     symbol = await async_hyper.get_coin_symbol(k)
    #     coin_name1 = await async_hyper.get_coin_name(k)
    #     coin_name2 = await async_hyper.get_coin_name(v)
    #     assert coin_name1 == coin_name2
    #     print(k, v, asset, symbol, coin_name1, coin_name2)
    coin_names = async_hyper.coin_names
    info = {}
    for k, v in coin_names.items():
        if k.startswith("@"):
            continue

        if k.endswith("/USDC"):
            continue

        decimals = await async_hyper.get_coin_sz_decimals(k)
        print(k, decimals)
        info[k] = decimals
    # decimals = async_hyper.asset_sz_decimals
    print(json.dumps(info))


@pytest.mark.asyncio(loop_scope="session")
async def test_get_order_status(async_hyper):
    order_id = 80489878412
    order: OrderWithStatus = await async_hyper.get_order_status(order_id)
    expected = {
        "status": "order",
        "order": {
            "order": {
                "coin": "SOL",
                "side": "B",
                "limitPx": "125.51",
                "sz": "0.0",
                "oid": 80489878412,
                "timestamp": 1742278993933,
                "triggerCondition": "N/A",
                "isTrigger": False,
                "triggerPx": "0.0",
                "children": [],
                "isPositionTpsl": False,
                "reduceOnly": False,
                "orderType": "Limit",
                "origSz": "1.78",
                "tif": "Ioc",
                "cloid": None,
            },
            "status": "filled",
            "statusTimestamp": 1742278993933,
        },
    }
    assert order == expected


@pytest.mark.asyncio(loop_scope="session")
async def test_get_user_deposits(async_hyper):
    start = int((time.time() - 30 * 24 * 3600) * 1000)
    data = await async_hyper.get_latest_deposits(start_time=start)
    assert isinstance(data, list)


@pytest.mark.asyncio(loop_scope="session")
async def test_get_user_positions(async_hyper):
    address = "0x91256c49dD025e61E2D3981189bA36907e084c2B"
    data = await async_hyper.get_all_positions(address)
    print(data)
    states = await async_hyper.get_perp_account_state(address)
    print(states)
