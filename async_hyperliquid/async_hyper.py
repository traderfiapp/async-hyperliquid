from typing import Any, Dict, List, Literal, Optional

from aiohttp import ClientSession, ClientTimeout
from eth_account import Account

from async_hyperliquid.async_api import AsyncAPI
from async_hyperliquid.utils.types import (
    Cloid,
    Position,
    LimitOrder,
    OrderStatus,
    AccountState,
    EncodedOrder,
    OrderBuilder,
    PlaceOrderRequest,
    CancelOrderRequest,
)
from async_hyperliquid.info_endpoint import InfoAPI
from async_hyperliquid.utils.signing import encode_order, orders_to_action
from async_hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from async_hyperliquid.exchange_endpoint import ExchangeAPI


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
        # TODO: figure out the vault address
        self.vault: Optional[str] = None

    def _init_coin_assets(self) -> None:
        self.coin_assets = {}
        for asset, asset_info in enumerate(self.metas["perps"]["universe"]):
            self.coin_assets[asset_info["name"]] = asset

        for asset_info in self.metas["spots"]["universe"]:
            asset = asset_info["index"] + 10_000
            self.coin_assets[asset_info["name"]] = asset

    def _init_coin_names(self) -> None:
        self.coin_names = {}
        for asset_info in self.metas["perps"]["universe"]:
            self.coin_names[asset_info["name"]] = asset_info["name"]

        for asset_info in self.metas["spots"]["universe"]:
            self.coin_names[asset_info["name"]] = asset_info["name"]
            # For token pairs
            base, quote = asset_info["tokens"]
            base_info = self.metas["spots"]["tokens"][base]
            quote_info = self.metas["spots"]["tokens"][quote]
            base_name = base_info["name"]
            if base_name not in self.coin_names:
                self.coin_names[base_name] = asset_info["name"]

            quote_name = quote_info["name"]
            name = f"{base_name}/{quote_name}"
            if name not in self.coin_names:
                self.coin_names[name] = asset_info["name"]

            # Specific for UBTC
            ubtc_name = f"BTC/{quote_name}"
            if base_name == "UBTC" and ubtc_name not in self.coin_names:
                self.coin_names[ubtc_name] = asset_info["name"]

        # USDC is the stable coin, it's a measure of value, always $1

    def _init_asset_sz_decimals(self) -> None:
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
        coin_name = await self.get_coin_name(coin)

        if coin_name not in self.coin_assets:
            raise ValueError(f"Coin {coin}({coin_name}) not found")

        return self.coin_assets[coin_name]

    async def get_coin_symbol(self, coin: str) -> str:
        if not hasattr(self, "coin_symbols") or not self.coin_symbols:
            await self.init_metas()
            self.coin_symbols = {
                v: k
                for k, v in self.coin_names.items()
                if not k.startswith("@")
            }
        coin_name = await self.get_coin_name(coin)
        return self.coin_symbols[coin_name]

    async def get_coin_sz_decimals(self, coin: str) -> int:
        coin_name = await self.get_coin_name(coin)
        asset = await self.get_coin_asset(coin_name)

        return self.asset_sz_decimals[asset]

    async def get_token_id(self, coin: str) -> str:
        coin_name = await self.get_coin_name(coin)
        spot_metas: Dict[str, Any] = self.metas["spots"]
        for coin_info in spot_metas["universe"]:
            if coin_name == coin_info["name"]:
                base, _quote = coin_info["tokens"]
                return spot_metas["tokens"][base]["tokenId"]

        return None

    async def get_market_price(self, coin: str) -> float:
        coin_name = await self.get_coin_name(coin)
        market_prices = await self.get_all_market_prices()
        return market_prices[coin_name]

    async def get_all_market_prices(
        self, market: Literal["spot", "perp", "all"] = "all"
    ) -> Dict[str, float]:
        is_spot = market == "spot"
        is_perp = market == "perp"
        is_all = market == "all"

        prices = {}

        await self.init_metas()
        if is_spot or is_all:
            spot_data = await self._info.get_spot_meta_ctx()
        if is_perp or is_all:
            perp_data = await self._info.get_perp_meta_ctx()

        for coin, asset in self.coin_assets.items():
            if asset < 10_000 and (is_perp or is_all):  # perp or all
                prices[coin] = float(perp_data[1][asset]["markPx"])
            if asset >= 10_000 and (is_spot or is_all):  # spot or all
                asset -= 10_000
                prices[coin] = float(spot_data[1][asset]["markPx"])
        return prices

    async def get_account_state(self, address: str = None) -> AccountState:
        if not address:
            address = self.address

        perp = await self._info.get_perp_clearinghouse_state(address)
        spot = await self._info.get_spot_clearinghouse_state(address)

        return {"perp": perp, "spot": spot}

    async def get_account_portfolio(self, address: str = None) -> List[Any]:
        if not address:
            address = self.address

        return await self._info.get_user_portfolio(address)

    async def get_order_status(
        self, order_id: int, address: str = None
    ) -> OrderStatus:
        if not address:
            address = self.address
        return await self._info.get_order_status(order_id, address)

    async def update_leverage(
        self, leverage: int, coin: str, is_cross: bool = True
    ):
        action = {
            "type": "updateLeverage",
            "asset": await self.get_coin_asset(coin),
            "isCross": is_cross,
            "leverage": leverage,
        }

        return await self._exchange.post_action(action)

    async def place_orders(
        self,
        orders: List[PlaceOrderRequest],
        builder: Optional[OrderBuilder] = None,
    ):
        encoded_orders: List[EncodedOrder] = []
        for order in orders:
            asset = await self.get_coin_asset(order["coin"])
            encoded_orders.append(encode_order(order, asset))

        if builder:
            builder["b"] = builder["b"].lower()
        action = orders_to_action(encoded_orders, builder)

        return await self._exchange.post_action(action)

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
            market_price = await self.get_market_price(coin)
            px = await self._slippage_price(
                coin, is_buy, slippage, market_price
            )
            # Market order is an aggressive Limit Order IoC
            order_type = LimitOrder.IOC.value

        coin_name = await self.get_coin_name(coin)

        order_req = {
            "coin": coin_name,
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

    async def cancel_order(self, coin: str, oid: int | str):
        name = await self.get_coin_name(coin)
        if not isinstance(oid, int):
            oid = int(oid)
        cancel_req = {"coin": name, "oid": oid}
        return await self.cancel_orders([cancel_req])

    async def cancel_orders(self, orders: List[CancelOrderRequest]):
        # TODO: support cloid
        action = {
            "type": "cancel",
            "cancels": [
                {
                    "a": await self.get_coin_asset(order["coin"]),
                    "o": order["oid"],
                }
                for order in orders
            ],
        }

        return await self._exchange.post_action(action, self.vault)

    async def modify_order(self):
        # TODO: implement modify order
        pass

    async def set_referrer_code(self, code: str):
        action = {"type": "setReferrer", "code": code}
        return await self._exchange.post_action(action)

    async def get_all_positions(self, address: str = None) -> List[Position]:
        if not address:
            address = self.address

        resp = await self._info.get_perp_clearinghouse_state(address)
        positions = [p["position"] for p in resp["assetPositions"]]
        return positions

    async def close_all_positions(self) -> None:
        positions = await self.get_all_positions()
        for position in positions:
            await self.close_position(position["coin"])

    async def close_position(self, coin: str) -> None:
        positions = await self.get_all_positions()
        target = {}
        for position in positions:
            if coin == position["coin"]:
                target = position

        if not target:
            raise ValueError(
                "User({self.address}) doesn't have position for {coin}"
            )

        size = float(target["szi"])
        price = await self.get_market_price(coin)
        if not price:
            raise ValueError(f"Failed to retrieve market price for {coin}")

        close_order = {
            "coin": coin,
            "is_buy": size < 0,
            "sz": abs(size),
            "px": price,
            "is_market": True,
            "reduce_only": True,
        }

        await self.place_order(**close_order)

    def get_leverage_from_positions(
        self, positions: List[Position]
    ) -> Dict[str, int]:
        leverages = {}
        for position in positions:
            coin = position["coin"]
            leverage = position["leverage"]["value"]
            leverages[coin] = leverage

        return leverages
