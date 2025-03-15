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
```

## Quick Start

```python
import asyncio
import os
from async_hyperliquid import AsyncHyper

async def main():
    # Initialize the client
    address = os.getenv("HYPER_ADDRESS")
    api_key = os.getenv("HYPER_API_KEY")
    client = AsyncHyper(address, api_key, is_mainnet=True)

    # Initialize metadata (required before making other calls)
    await client.init_metas()

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

## Environment Variables

Create a `.env.local` file with the following variables:

```
HYPER_ADDRESS=your_ethereum_address
HYPER_API_KEY=your_ethereum_private_key
```

## API Reference

### AsyncHyper

The main client class that provides methods for interacting with the Hyperliquid API.

#### Initialization

```python
client = AsyncHyper(address, api_key, is_mainnet=True)
```

#### Methods

- `init_metas()`: Initialize metadata (required before using other methods)
- `update_leverage(leverage, coin, is_cross=True)`: Update leverage for a specific coin
- `place_order(coin, is_buy, sz, px, is_market=True, **kwargs)`: Place a single order
- `place_orders(orders, builder=None)`: Place multiple orders at once

### Additional Modules

- `InfoAPI`: Access market information endpoints
- `ExchangeAPI`: Access exchange operation endpoints
- `utils`: Various utility functions and constants

## Testing

Tests use pytest and pytest-asyncio. To run tests:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=async_hyperliquid
```

## License

MIT

## Acknowledgements

This library is a community-developed project and is not officially affiliated with Hyperliquid.

## TODO

See the TODO.md file for upcoming features and improvements.
