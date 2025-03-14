from typing import Any, Dict, List, Optional

from aiohttp import ClientSession, ClientTimeout
from eth_account import Account

from async_hyper.async_api import AsyncAPI
from async_hyper.utils.miscs import get_timestamp_ms
from async_hyper.utils.types import (
    Cloid,
    LimitOrder,
    EncodedOrder,
    OrderBuilder,
    OrderRequest,
)
from async_hyper.info_endpoint import InfoAPI
from async_hyper.utils.signing import (
    sign_action,
    encode_order,
    orders_to_action,
)
from async_hyper.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from async_hyper.exchange_endpoint import ExchangeAPI


class AsyncHyper(AsyncAPI):
    def __init__(self, address: str, api_key: str, is_mainnet: bool = True):
        self.address = address
        self.is_mainnet = is_mainnet
        self.account = Account.from_key(api_key)
        self.session = ClientSession(timeout=ClientTimeout(connect=3))
        self.base_url = MAINNET_API_URL if is_mainnet else TESTNET_API_URL
        self._info = InfoAPI(self.base_url, self.session)
        self._exchange = ExchangeAPI(
            self.account, self.session, self.base_url, address=self.address
        )
        self.metas: Optional[Dict[str, Any]] = None

    def _init_coin_assets(self):
        self.coin_assets = {}
        for asset, asset_info in enumerate(self.metas["perps"]["universe"]):
            self.coin_assets[asset_info["name"]] = asset

        for asset_info in self.metas["spots"]["universe"]:
            asset = asset_info["index"] + 10_000
            self.coin_assets[asset_info["name"]] = asset

    def _init_coin_names(self):
        self.coin_names = {}
        for asset_info in self.metas["perps"]["universe"]:
            self.coin_names[asset_info["name"]] = asset_info["name"]

        for asset_info in self.metas["spots"]["universe"]:
            self.coin_names[asset_info["name"]] = asset_info["name"]
            # For token pairs
            base, quote = asset_info["tokens"]
            base_info = self.metas["spots"]["tokens"][base]
            quote_info = self.metas["spots"]["tokens"][quote]
            base_name = (
                base_info["name"] if base_info["name"] != "UBTC" else "BTC"
            )
            quote_name = quote_info["name"]
            name = f"{base_name}/{quote_name}"
            if name not in self.coin_names:
                self.coin_names[name] = asset_info["name"]

    def _init_asset_sz_decimals(self):
        self.asset_sz_decimals = {}
        for asset, asset_info in enumerate(self.metas["perps"]["universe"]):
            self.asset_sz_decimals[asset] = asset_info["szDecimals"]

        for asset_info in self.metas["spots"]["universe"]:
            asset = asset_info["index"] + 10_000
            base, _quote = asset_info["tokens"]
            base_info = self.metas["spots"]["tokens"][base]
            self.asset_sz_decimals[asset] = base_info["szDecimals"]

    async def get_metas(self, perp_only: bool = False) -> dict:
        perp_meta = await self._info.get_perp_meta()
        if perp_only:
            return {"perps": perp_meta, "spots": []}

        spot_meta = await self._info.get_spot_meta()

        return {"perps": perp_meta, "spots": spot_meta}

    async def init_metas(self):
        if not hasattr(self, "metas") or not self.metas:
            self.metas = await self.get_metas()

        if not self.metas.get("perps") or not self.metas["perps"]:
            self.metas["perps"] = await self._info.get_perp_meta()

        if not self.metas.get("spots") or not self.metas["spots"]:
            self.metas["spots"] = await self._info.get_spot_meta()

        if not hasattr(self, "coin_assets") or not self.coin_assets:
            self._init_coin_assets()

        if not hasattr(self, "coin_names") or not self.coin_names:
            self._init_coin_names()

        if not hasattr(self, "asset_sz_decimals") or not self.asset_sz_decimals:
            self._init_asset_sz_decimals()

    async def get_coin_name(self, coin: str) -> str:
        await self.init_metas()

        if coin not in self.coin_names:
            raise ValueError(f"Coin {coin} not found")

        return self.coin_names[coin]

    async def get_coin_asset(self, coin: str) -> int:
        await self.init_metas()

        if coin not in self.coin_assets:
            raise ValueError(f"Coin {coin} not found")

        return self.coin_assets[coin]

    async def get_coin_sz_decimals(self, coin: str) -> int:
        await self.init_metas()

        asset = await self.get_coin_asset(coin)

        return self.asset_sz_decimals[asset]

    async def get_token_id(self, coin: str) -> str:
        coin_name = await self.get_coin_name(coin)
        spot_metas: Dict[str, Any] = self.metas["spots"]
        for coin_info in spot_metas["universe"]:
            if coin_name == coin_info["name"]:
                base, _quote = coin_info["tokens"]
                return spot_metas["tokens"][base]["tokenId"]

        return None

    async def update_leverage(
        self, leverage: int, coin: str, is_cross: bool = True
    ):
        nonce = get_timestamp_ms()
        action = {
            "type": "updateLeverage",
            "asset": await self.get_coin_asset(coin),
            "isCross": is_cross,
            "leverage": leverage,
        }
        sig = sign_action(self.account, action, None, nonce, True)

        return await self._exchange.post_action(action, sig, nonce)

    async def place_orders(
        self, orders: List[OrderRequest], builder: Optional[OrderBuilder] = None
    ):
        print(orders)
        encoded_orders: List[EncodedOrder] = []
        for order in orders:
            asset = await self.get_coin_asset(order["coin"])
            print(asset)
            encoded_orders.append(encode_order(order, asset))

        nonce = get_timestamp_ms()
        if builder:
            builder["b"] = builder["b"].lower()
        action = orders_to_action(encoded_orders, builder)

        # TODO: the third arg is vault_address, which is None for now
        sig = sign_action(self.account, action, None, nonce, self.is_mainnet)

        return await self._exchange.post_action(action, sig, nonce)

    async def _slippage_price(
        self, coin: str, is_buy: bool, slippage: float, px: float
    ) -> float:
        coin_name = await self.get_coin_name(coin)
        if not px:
            all_mids = await self._info.get_all_mids()
            px = float(all_mids[coin_name])

        asset = await self.get_coin_asset(coin)
        is_spot = asset >= 10_000
        sz_decimals = await self.get_coin_sz_decimals(coin)
        px *= (1 + slippage) if is_buy else (1 - slippage)
        return round(
            float(f"{px:.5g}"), (6 if not is_spot else 8) - sz_decimals
        )

    async def place_order(
        self,
        coin: str,
        is_buy: bool,
        sz: float,
        px: float,
        is_market: bool = True,
        *,
        order_type: dict = LimitOrder.IOC.value,
        reduce_only: bool = False,
        cloid: Optional[Cloid] = None,
        slippage: float = 0.01,  # Default slippage is 1%
        builder: Optional[OrderBuilder] = None,
    ):
        if is_market:
            px = self._slippage_price(coin, is_buy, slippage, px)
            # Market order is an aggressive Limit Order IoC
            order_type = LimitOrder.IOC
            reduce_only = False

        name = await self.get_coin_name(coin)

        order_req = {
            "coin": name,
            "is_buy": is_buy,
            "sz": sz,
            "limit_px": px,
            "order_type": order_type,
            "reduce_only": reduce_only,
            "cloid": cloid,
        }

        if cloid:
            order_req["cloid"] = cloid

        return await self.place_orders([order_req], builder=builder)

    async def cancel_order(self):
        # TODO: implement cancel order
        pass

    async def modify_order(self):
        # TODO: implement modify order
        pass

    async def close_all_positions(self):
        # TODO: implement close all positions
        pass

    async def close_position(self, coin: str):
        # TODO: implement close position
        pass
