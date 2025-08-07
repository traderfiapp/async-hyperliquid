# Async Hyperliquid

An asynchronous Python client for interacting with the Hyperliquid API using `aiohttp`.

## Overview

This library provides an easy-to-use asynchronous interface for the Hyperliquid cryptocurrency exchange, supporting both mainnet and testnet environments. It handles API interactions, request signing, and data processing for both perpetual futures and spot trading.

## Features

- Asynchronous API communication using `aiohttp`
- Support for both mainnet and testnet environments
- Message signing for authenticated endpoints
- Trading operations for both perpetual futures and spot markets
- Comprehensive type hints for better IDE integration

## Installation

```bash
# Using pip
pip install async-hyperliquid

# Using Poetry
poetry add async-hyperliquid

# Using uv
uv add async-hyperliquid
```

## Quick Start

```python
import asyncio
import os
from async_hyperliquid.async_hyper import AsyncHyper

async def main():
    # Initialize the client
    address = os.getenv("HYPER_ADDRESS")
    api_key = os.getenv("HYPER_API_KEY")
    # Test on testnet
    client = AsyncHyper(address, api_key, is_mainnet=False)

    # Place a market order
    response = await client.place_order(
        coin="BTC",
        is_buy=True,
        sz=0.001,
        px=0,  # For market orders, price is ignored
        is_market=True
    )

    print(response)

    # Clean up
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

Or if you perfer context way:

```python
import asyncio
import os
from async_hyperliquid.async_hyper import AsyncHyper

async def main():
    # Initialize the client
    address = os.getenv("HYPER_ADDRESS")
    api_key = os.getenv("HYPER_API_KEY")
    # Test on testnet
    async with AsyncHyper(address, api_key, is_mannet=False) as client:
        # place an market order open a BTC Long position
        resp = await client.place_order(coin="BTC", is_buy=True, sz=0.0001, px=0, is_market=True)
        print(resp)

if __name__ == "__main__":
    asyncio.run(main())

```

### Place TP/SL orders

```python
    coin = "BTC"
    is_buy = True
    sz = 0.001
    px = 105_000
    tp_px = px + 5_000
    sl_px = px - 5_000
    o1 = {
        "coin": coin,
        "is_buy": is_buy,
        "sz": sz,
        "px": px,
        "ro": False,
        "order_type": LimitOrder.ALO.value,
    }
    # Take profit
    tp_order_type = {
        "trigger": {"isMarket": False, "triggerPx": tp_px, "tpsl": "tp"}
    }
    o2 = {
        "coin": coin,
        "is_buy": not is_buy,
        "sz": sz,
        "px": px,
        "ro": True,
        "order_type": tp_order_type,
    }
    # Stop loss
    sl_order_type = {
        "trigger": {"isMarket": False, "triggerPx": sl_px, "tpsl": "sl"}
    }
    o3 = {
        "coin": coin,
        "is_buy": not is_buy,
        "sz": sz,
        "px": px,
        "ro": True,
        "order_type": sl_order_type,
    }

    # Place a market order to open position
    resp = await client.batch_place_orders([o1], is_market=True)
    print("\nBatch place market orders response: ", resp)
    assert resp["status"] == "ok"

    # Position TP/SL orders: position must be opened, otherwise it would failed
    orders = [o2, o3]
    resp = await client.batch_place_orders(orders, grouping="positionTpsl")
    print("Batch place orders with 'positionTpsl' response: ", resp)
    assert resp["status"] == "ok"

    # Close all positions
    resp = await client.close_all_positions()
    print("Close all positions response: ", resp)
    assert resp["status"] == "ok"

    # Normal TP/SL orders: main order and tp/sl must exists, each coin's normal
    # TP/SL orders can not batch with other coins', i.e. one coin one request.
    orders = [o1, o2, o3]
    resp = await client.batch_place_orders(orders, grouping="normalTpsl")
    print("Batch place orders with 'normalTpsl' response: ", resp)

    # Retrieve user opened orders
    orders = await client.get_user_open_orders(is_frontend=True)
    cancels = []
    for o in orders:
        coin = o["coin"]
        oid = o["oid"]
        cancels.append((coin, oid))
    resp = await client.batch_cancel_orders(cancels)
    print("Batch cancel orders response: ", resp)
```

For detailed usage, please check the test cases under `test/` directory.

## Environment Variables

Create a `.env.local` file with the following variables:

```
HYPER_ADDRESS=your_ethereum_address
HYPER_API_KEY=your_ethereum_private_key or api key generate hyperliquid website
```

## Testing

Tests use pytest and pytest-asyncio. To run tests:

```bash
uv pip install -e .

# Run all tests
pytest

# Run with coverage
pytest --cov=async_hyperliquid
```

## License

MIT

## Acknowledgements

This library is a community-developed project and is not officially affiliated with Hyperliquid.
