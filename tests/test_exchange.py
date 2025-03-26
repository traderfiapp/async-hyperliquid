import pytest

from async_hyperliquid.async_hyper import LimitOrder


@pytest.mark.asyncio(loop_scope="session")
async def test_update_leverage(async_hyper):
    leverage = 10
    coin = "BTC"
    resp: dict = await async_hyper.update_leverage(leverage, coin)
    assert resp["status"] == "ok"


@pytest.mark.asyncio(loop_scope="session")
async def test_spot_order(async_hyper):
    # coin = "BTC/USDC"
    coin = "@142"  # @142 is the coin name for symbol BTC/USDC
    buy_value = 10 + 0.3
    buy_price = 10_000.0
    buy_sz = buy_value / buy_price
    order_req = {
        "coin": coin,
        "is_buy": True,
        "sz": buy_sz,
        "px": buy_price,
        "is_market": False,
        "order_type": LimitOrder.ALO.value,
    }

    resp: dict = await async_hyper.place_order(**order_req)
    assert resp["status"] == "ok"

    oid = resp["response"]["data"]["statuses"][0]["resting"]["oid"]
    assert oid

    resp = await async_hyper.cancel_order(coin, oid)
    assert resp["status"] == "ok"
    assert resp["response"]["data"]["statuses"][0] == "success"


@pytest.mark.asyncio(loop_scope="session")
async def test_perp_order(async_hyper):
    coin = "BTC"
    buy_value = 10 + 0.3
    buy_price = 10_000.0
    buy_sz = buy_value / buy_price
    order_req = {
        "coin": coin,
        "is_buy": True,
        "sz": buy_sz,
        "px": buy_price,
        "is_market": False,
        "order_type": LimitOrder.ALO.value,
    }

    resp: dict = await async_hyper.place_order(**order_req)
    assert resp["status"] == "ok"
    print(resp)

    oid = resp["response"]["data"]["statuses"][0]["resting"]["oid"]
    assert oid

    resp = await async_hyper.cancel_order(coin, oid)
    assert resp["status"] == "ok"
    assert resp["response"]["data"]["statuses"][0] == "success"
