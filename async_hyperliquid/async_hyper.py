import math
from typing import Any, Literal

from aiohttp import ClientSession, ClientTimeout
from eth_account import Account

from async_hyperliquid.async_api import AsyncAPI
from async_hyperliquid.utils.miscs import (
    round_px,
    round_float,
    get_timestamp_ms,
)
from async_hyperliquid.utils.types import (
    Cloid,
    Position,
    OrderType,
    LimitOrder,
    UserFunding,
    AccountState,
    GroupOptions,
    OrderBuilder,
    OrderWithStatus,
    PlaceOrderRequest,
    BatchCancelRequest,
    CancelOrderRequest,
    ClearinghouseState,
    UserNonFundingDelta,
    BatchPlaceOrderRequest,
    SpotClearinghouseState,
)
from async_hyperliquid.info_endpoint import InfoAPI
from async_hyperliquid.utils.signing import (
    encode_order,
    orders_to_action,
    sign_usd_transfer_action,
    sign_usd_class_transfer_action,
)
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
        self.metas: dict[str, Any] = {}
        # TODO: figure out the vault address
        self.vault: str | None = None

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
            quote_name = quote_info["name"]
            name = f"{base_name}/{quote_name}"
            if name not in self.coin_names:
                self.coin_names[name] = asset_info["name"]

        self.coin_symbols = {
            v: k for k, v in self.coin_names.items() if not k.startswith("@")
        }

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
        if not hasattr(self, "coin_names") or coin not in self.coin_names:
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
        coin_name = await self.get_coin_name(coin)
        return self.coin_symbols[coin_name]

    async def get_coin_sz_decimals(self, coin: str) -> int:
        coin_name = await self.get_coin_name(coin)
        asset = await self.get_coin_asset(coin_name)

        return self.asset_sz_decimals[asset]

    async def get_token_id(self, coin: str) -> str | None:
        coin_name = await self.get_coin_name(coin)
        spot_metas: dict[str, Any] = self.metas["spots"]
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
    ) -> dict[str, float]:
        is_spot = market == "spot"
        is_perp = market == "perp"
        is_all = market == "all"

        prices = {}

        await self.init_metas()
        spot_data = None
        perp_data = None
        if is_spot or is_all:
            spot_data = await self._info.get_spot_meta_ctx()
        if is_perp or is_all:
            perp_data = await self._info.get_perp_meta_ctx()

        for coin, asset in self.coin_assets.items():
            if (
                asset < 10_000
                and (is_perp or is_all)
                and isinstance(perp_data, list)
            ):  # perp or all
                prices[coin] = float(perp_data[1][asset]["markPx"])
            if (
                asset >= 10_000
                and (is_spot or is_all)
                and isinstance(spot_data, list)
            ):  # spot or all
                asset -= 10_000
                prices[coin] = float(spot_data[1][asset]["markPx"])
        return prices

    async def get_perp_account_state(
        self, address: str | None = None
    ) -> ClearinghouseState:
        if not address:
            address = self.address

        return await self._info.get_perp_clearinghouse_state(address)

    async def get_spot_account_state(
        self, address: str | None = None
    ) -> SpotClearinghouseState:
        if not address:
            address = self.address
        return await self._info.get_spot_clearinghouse_state(address)

    async def get_account_state(
        self, address: str | None = None
    ) -> AccountState:
        if not address:
            address = self.address

        perp = await self.get_perp_account_state(address)
        spot = await self.get_spot_account_state(address)

        return {"perp": perp, "spot": spot}

    async def get_account_portfolio(
        self, address: str | None = None
    ) -> list[Any]:
        if not address:
            address = self.address

        return await self._info.get_user_portfolio(address)

    async def get_latest_ledgers(
        self,
        ledger_type: str = "deposit",
        address: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[UserNonFundingDelta]:
        if not start_time:
            now = get_timestamp_ms()
            one_hour = 60 * 60 * 1000  # one hour in millis
            start_time = now - one_hour
        if not address:
            address = self.address
        data = await self._info.get_user_funding(
            address, start_time, end_time=end_time, is_funding=False
        )
        return [d for d in data if d["delta"]["type"] == ledger_type]  # type: ignore

    async def get_latest_deposits(
        self,
        address: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[UserFunding]:
        return await self.get_latest_ledgers(
            "deposit", address, start_time, end_time
        )  # type: ignore

    async def get_latest_withdraws(
        self,
        address: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[UserFunding]:
        return await self.get_latest_ledgers(
            "withdraw", address, start_time, end_time
        )  # type: ignore

    async def get_latest_transfers(
        self,
        address: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[UserFunding]:
        return await self.get_latest_ledgers(
            "accountClassTransfer", address, start_time, end_time
        )  # type: ignore

    async def get_user_open_orders(
        self, address: str | None = None, is_frontend: bool = False
    ):
        if not address:
            address = self.address
        return await self._info.get_user_open_orders(address, is_frontend)

    async def get_order_status(
        self, order_id: int, address: str | None = None
    ) -> OrderWithStatus:
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

    async def update_isolated_margin(self, usd: float, coin: str):
        usd_in_units = usd * 10**6
        if abs(round(usd_in_units) - usd_in_units) >= 1e-3:
            raise ValueError(
                f"USD amount precision error: Value {usd} cannot be accurately"
            )
        amount = math.floor(usd_in_units)
        action = {
            "type": "updateIsolatedMargin",
            "asset": await self.get_coin_asset(coin),
            "isBuy": True,
            "ntli": amount,
        }

        return await self._exchange.post_action(action)

    async def place_orders(
        self,
        orders: list[PlaceOrderRequest],
        grouping: GroupOptions = "na",
        builder: OrderBuilder | None = None,
        vault: str | None = None,
        expires: int | None = None,
    ):
        encoded_orders = [encode_order(o) for o in orders]

        if builder:
            builder["b"] = builder["b"].lower()

        action = orders_to_action(encoded_orders, grouping, builder)

        return await self._exchange.post_action(
            action, vault=vault, expires=expires
        )

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
        px_decimals = (6 if not is_spot else 8) - sz_decimals
        return round_float(px, px_decimals)

    async def _round_sz_px(
        self, coin: str, sz: float, px: float
    ) -> tuple[int, float, float]:
        asset = await self.get_coin_asset(coin)
        is_spot = asset >= 10_000
        sz_decimals = await self.get_coin_sz_decimals(coin)
        px_decimals = (6 if not is_spot else 8) - sz_decimals
        return asset, round_float(sz, sz_decimals), round_px(px, px_decimals)

    async def place_order(
        self,
        coin: str,
        is_buy: bool,
        sz: float,
        px: float,
        is_market: bool = True,
        *,
        ro: bool = False,
        order_type: OrderType = LimitOrder.IOC.value,  # type: ignore
        cloid: Cloid | None = None,
        slippage: float = 0.01,  # Default slippage is 1%
        builder: OrderBuilder | None = None,
    ):
        if is_market:
            market_price = await self.get_market_price(coin)
            slippage_factor = (1 + slippage) if is_buy else (1 - slippage)
            px = market_price * slippage_factor
            # Market order is an aggressive Limit Order IoC
            order_type = LimitOrder.IOC.value  # type: ignore

        asset, sz, px = await self._round_sz_px(coin, sz, px)

        order_req: PlaceOrderRequest = {
            "asset": asset,
            "is_buy": is_buy,
            "sz": sz,
            "px": px,
            "ro": ro,
            "order_type": order_type,
            "cloid": cloid,
        }

        return await self.place_orders([order_req], builder=builder)

    async def batch_place_orders(
        self,
        orders: BatchPlaceOrderRequest,
        *,
        grouping: GroupOptions = "na",
        is_market: bool = False,
        slippage: float = 0.01,  # Default slippage is 1%
        builder: OrderBuilder | None = None,
        vault: str | None = None,
        expires: int | None = None,
    ):
        reqs = []
        if is_market:
            reqs = await self._get_batch_market_orders(orders, slippage)
        else:
            for o in orders:
                asset, sz, px = await self._round_sz_px(
                    o["coin"], o["sz"], o["px"]
                )
                req = {**o, "asset": asset, "sz": sz, "px": px}
                reqs.append(req)

        return await self.place_orders(
            reqs,
            grouping=grouping,
            builder=builder,
            vault=vault,
            expires=expires,
        )

    async def _get_batch_market_orders(
        self,
        orders: BatchPlaceOrderRequest,
        slippage: float = 0.01,  # Default slippage is 1%
    ) -> list[PlaceOrderRequest]:
        reqs = []
        market_prices = await self.get_all_market_prices()
        order_type = LimitOrder.IOC.value
        for o in orders:
            coin = o["coin"]
            market_price = market_prices[coin]
            slippage_factor = (1 + slippage) if o["is_buy"] else (1 - slippage)
            px = market_price * slippage_factor
            asset, sz, px = await self._round_sz_px(coin, o["sz"], px)
            req = {
                **o,
                "asset": asset,
                "sz": sz,
                "px": px,
                "order_type": order_type,
            }
            reqs.append(req)
        return reqs

    async def cancel_order(self, coin: str, oid: int):
        cancel_req: CancelOrderRequest = {"coin": coin, "oid": int(oid)}
        return await self.cancel_orders([cancel_req])

    async def batch_cancel_orders(self, cancels: BatchCancelRequest):
        reqs: list = [{"coin": c[0], "oid": int(c[1])} for c in cancels]
        return await self.cancel_orders(reqs)

    async def cancel_orders(
        self,
        orders: list[CancelOrderRequest],
        *,
        vault: str | None = None,
        expires: int | None = None,
    ):
        action = {
            "type": "cancel",
            "cancels": [
                {
                    "a": await self.get_coin_asset(order["coin"]),
                    "o": order["oid"].to_raw()
                    if isinstance(order["oid"], Cloid)
                    else order["oid"],
                }
                for order in orders
            ],
        }

        if vault is None:
            vault = self.vault

        return await self._exchange.post_action(
            action, vault=vault, expires=expires
        )

    async def modify_order(
        self,
        oid: int | Cloid,
        coin: str,
        is_buy: bool,
        sz: float,
        px: float,
        ro: bool,
        order_type: OrderType,
        cloid: Cloid | None = None,
    ):
        asset, sz, px = await self._round_sz_px(coin, sz, px)
        modify = {
            "oid": oid,
            "order": {
                "asset": asset,
                "is_buy": is_buy,
                "sz": sz,
                "px": px,
                "ro": ro,
                "order_type": order_type,
                "cloid": cloid,
            },
        }
        return await self.batch_modify_orders([modify])

    async def batch_modify_orders(self, modify_req: list):
        modifies = [
            {
                "oid": m["oid"].to_raw()
                if isinstance(m["oid"], Cloid)
                else m["oid"],
                "order": encode_order(m["order"]),
            }
            for m in modify_req
        ]
        action = {"type": "batchModify", "modifies": modifies}
        return await self._exchange.post_action(action)

    async def set_referrer_code(self, code: str):
        action = {"type": "setReferrer", "code": code}
        return await self._exchange.post_action(action)

    async def get_all_positions(
        self, address: str | None = None
    ) -> list[Position]:
        if not address:
            address = self.address

        resp = await self._info.get_perp_clearinghouse_state(address)
        positions = [p["position"] for p in resp["assetPositions"]]
        return positions

    async def close_all_positions(self):
        positions = await self.get_all_positions()
        if not positions:
            raise ValueError(f"User({self.address}) has no positions.")
        orders = []
        for p in positions:
            coin = p["coin"]
            szi = float(p["szi"])
            order = {
                "coin": coin,
                "is_buy": szi < 0,
                "sz": abs(szi),
                "px": 0,
                "ro": True,
            }
            orders.append(order)

        return await self.batch_place_orders(orders, is_market=True)

    async def close_position(self, coin: str):
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
            "ro": True,
        }

        return await self.place_order(**close_order)

    async def usd_class_transfer(self, amount: float, to_perp: bool = False):
        nonce = get_timestamp_ms()
        str_amount = str(amount)
        # current not support for vault address
        action = {
            "type": "usdClassTransfer",
            "amount": str_amount,
            "toPerp": to_perp,
            "nonce": nonce,
        }
        sig = sign_usd_class_transfer_action(
            self.account, action, self.base_url == MAINNET_API_URL
        )
        return await self._exchange.post_action_with_sig(action, sig, nonce)

    async def usd_transfer(self, amount: float, recipient: str):
        nonce = get_timestamp_ms()
        action = {
            "type": "usdSend",
            "amount": str(amount),
            "destination": recipient,
            "time": nonce,
        }
        is_mainnet = self.base_url == MAINNET_API_URL
        sig = sign_usd_transfer_action(self.account, action, is_mainnet)
        return await self._exchange.post_action_with_sig(action, sig, nonce)

    def get_leverage_from_positions(
        self, positions: list[Position]
    ) -> dict[str, int]:
        leverages = {}
        for position in positions:
            coin = position["coin"]
            leverage = position["leverage"]["value"]
            leverages[coin] = leverage

        return leverages

    async def place_twap(
        self,
        coin: str,
        is_buy: bool,
        sz: float,
        minutes: int,
        ro: bool = False,
        randomize: bool = False,
        *,
        vault: str | None = None,
        expires: int | None = None,
    ):
        asset, sz, _ = await self._round_sz_px(coin, sz, 0)
        action = {
            "type": "twapOrder",
            "twap": {
                "a": asset,
                "b": is_buy,
                "s": str(sz),
                "r": ro,
                "m": minutes,
                "t": randomize,
            },
        }
        return await self._exchange.post_action(
            action, vault=vault, expires=expires
        )

    async def cancel_twap(self, coin: str, twap_id: int):
        action = {
            "type": "twapCancel",
            "a": await self.get_coin_asset(coin),
            "t": twap_id,
        }
        return await self._exchange.post_action(action)
