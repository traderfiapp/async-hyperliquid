import pytest


@pytest.mark.asyncio(loop_scope="session")
async def test_update_leverage(async_hyper):
    leverage = 10
    btc_name_idx = 0
    resp = await async_hyper.update_leverage(leverage, btc_name_idx)
    print(resp)
    assert resp["status"] == "ok"  # type: ignore
