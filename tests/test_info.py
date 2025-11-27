import time
from typing import Any
from datetime import datetime, timezone, timedelta

import pytest

from async_hyperliquid import AsyncHyperliquid
from async_hyperliquid.utils.types import OrderWithStatus


@pytest.mark.asyncio(loop_scope="session")
async def test_metas(hl: AsyncHyperliquid):
    metas: dict[str, Any] = await hl.get_metas()
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
        ("HYPE/USDC", "@107"),
        ("PURR/USDC", "PURR/USDC"),
        ("@142", "@142"),
        ("UBTC/USDC", "@142"),
        ("xyz:XYZ100", "xyz:XYZ100"),
        pytest.param(
            "ETH/USDC",
            None,
            marks=pytest.mark.xfail(
                raises=ValueError, reason="ETH/USDC is not supported"
            ),
        ),
    ],
)
async def test_get_coin_name(
    hl: AsyncHyperliquid, coin: str, name: str
) -> None:
    coin_name = await hl.get_coin_name(coin)
    assert coin_name == name


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "coin, symbol",
    [
        ("BTC", "BTC"),
        ("UBTC/USDC", "UBTC/USDC"),
        ("@142", "UBTC/USDC"),
        ("@107", "HYPE/USDC"),
        ("PURR/USDC", "PURR/USDC"),
        ("xyz:XYZ100", "xyz:XYZ100"),
        pytest.param(
            "ETH/USDC",
            None,
            marks=pytest.mark.xfail(
                raises=ValueError, reason="ETH/USDC is not supported"
            ),
        ),
    ],
)
async def test_get_coin_symbol(
    hl: AsyncHyperliquid, coin: str, symbol: str
) -> None:
    coin_symbol = await hl.get_coin_symbol(coin)
    assert coin_symbol == symbol


@pytest.mark.asyncio(loop_scope="session")
async def test_get_market_price(hl: AsyncHyperliquid):
    price = await hl.get_market_price("BTC")
    print(price)
    # assert price
    price = await hl.get_market_price("UBTC/USDC")
    print(price)
    # assert price


@pytest.mark.asyncio(loop_scope="session")
async def test_get_all_market_prices(hl: AsyncHyperliquid):
    prices = await hl.get_all_market_prices()
    # print(prices)
    assert isinstance(prices, dict)
    assert "@142" in prices


@pytest.mark.asyncio(loop_scope="session")
async def test_coin_utils(hl: AsyncHyperliquid):
    coin_names = hl.coin_names
    for k, v in coin_names.items():
        asset = await hl.get_coin_asset(k)
        symbol = await hl.get_coin_symbol(k)
        coin_name1 = await hl.get_coin_name(k)
        coin_name2 = await hl.get_coin_name(v)
        assert coin_name1 == coin_name2
        print(k, v, asset, symbol, coin_name1, coin_name2)


@pytest.mark.asyncio(loop_scope="session")
async def test_get_order_status(hl: AsyncHyperliquid):
    order_id = 80489878412
    order: OrderWithStatus = await hl.get_order_status(order_id)
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
async def test_get_user_deposits(hl: AsyncHyperliquid):
    start = int((time.time() - 30 * 24 * 3600) * 1000)
    data = await hl.get_latest_deposits(start_time=start)
    assert isinstance(data, list)


@pytest.mark.asyncio(loop_scope="session")
async def test_get_user_positions(hl: AsyncHyperliquid):
    address = "0x91256c49dD025e61E2D3981189bA36907e084c2B"
    data = await hl.get_all_positions(address)
    print(data)
    states = await hl.get_perp_account_state(address)
    print(states)


@pytest.mark.asyncio(loop_scope="session")
async def test_usd_class_transfer(hl: AsyncHyperliquid):
    # transfer perp to spot
    usd_amount = 2
    resp = await hl.usd_class_transfer(usd_amount, to_perp=False)
    assert resp["status"] == "ok"
    # transfer spot to perp
    usd_amount = 1
    resp = await hl.usd_class_transfer(usd_amount, to_perp=True)
    assert resp["status"] == "ok"


@pytest.mark.asyncio(loop_scope="session")
async def test_usd_transfer(hl: AsyncHyperliquid):
    usd_amount = 5
    recipient = ""
    _resp = await hl.usd_transfer(usd_amount, recipient)
    # assert resp["status"] == "ok"


@pytest.mark.asyncio(loop_scope="session")
async def test_user_non_funding(hl: AsyncHyperliquid):
    addr = "0x5bf26001e812ef0a4fcead9c2ca4887b92d7733a"
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1)
    start_ts = int(start.timestamp() * 1000)
    resp = await hl.info.get_user_funding(addr, start_ts, is_funding=False)
    print(resp)
