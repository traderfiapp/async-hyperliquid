import pytest

from async_hyper.async_hyper import LimitOrder


@pytest.mark.asyncio(loop_scope="session")
async def test_update_leverage(async_hyper):
    leverage = 10
    btc_name_idx = 0
    resp: dict = await async_hyper.update_leverage(leverage, btc_name_idx)
    assert resp["status"] == "ok"


@pytest.mark.asyncio(loop_scope="session")
async def test_spot_order(async_hyper):
    buy_value = 10 + 0.3
    buy_price = 10_000.0
    buy_sz = buy_value / buy_price
    order_req = {
        "coin": "BTC/USDC",
        "is_buy": True,
        "sz": buy_sz,
        "px": buy_price,
        "is_market": False,
        "order_type": LimitOrder.ALO.value,
    }

    resp: dict = await async_hyper.place_order(**order_req)
    assert resp["status"] == "ok"
    assert resp["response"]["data"]["statuses"][0]["resting"]["oid"]  # type: ignore


@pytest.mark.asyncio(loop_scope="session")
async def test_perp_order(async_hyper):
    buy_value = 10 + 0.3
    buy_price = 10_000.0
    buy_sz = buy_value / buy_price
    order_req = {
        "coin": "BTC",
        "is_buy": True,
        "sz": buy_sz,
        "px": buy_price,
        "is_market": False,
        "order_type": LimitOrder.ALO.value,
    }

    resp: dict = await async_hyper.place_order(**order_req)
    assert resp["status"] == "ok"
