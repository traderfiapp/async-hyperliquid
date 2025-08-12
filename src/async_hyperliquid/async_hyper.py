import math
from typing import Any, Literal

from aiohttp import ClientSession, ClientTimeout
from eth_account import Account
from hl_web3.info import Info as EVMInfo
from hl_web3.exchange import Exchange as EVMExchange
from hl_web3.utils.constants import HL_RPC_URL, HL_TESTNET_RPC_URL
from eth_account.signers.local import LocalAccount

from async_hyperliquid.info import InfoAPI
from async_hyperliquid.exchange import ExchangeAPI
from async_hyperliquid.async_api import AsyncAPI
from async_hyperliquid.utils.miscs import (
    round_px,
    round_float,
    get_timestamp_ms,
    round_token_amount,
)
from async_hyperliquid.utils.types import (
    Cloid,
    Position,
    SpotMeta,
    OrderType,
    LimitOrder,
    AccountState,
    GroupOptions,
    OrderBuilder,
    PlaceOrderRequest,
    BatchCancelRequest,
    BatchPlaceOrderRequest,
)
from async_hyperliquid.utils.signing import (
    encode_order,
    orders_to_action,
    sign_withdraw_action,
    sign_send_asset_action,
    sign_usd_transfer_action,
    sign_approve_agent_action,
    sign_spot_transfer_action,
    sign_token_delegate_action,
    sign_staking_deposit_action,
    sign_staking_withdraw_action,
    sign_usd_class_transfer_action,
    sign_approve_builder_fee_action,
    sign_convert_to_multi_sig_user_action,
)
from async_hyperliquid.utils.constants import (
    USD_FACTOR,
    HYPE_FACTOR,
    ONE_HOUR_MS,
    MAINNET_API_URL,
    SPOT_ASSET_BASE,
    TESTNET_API_URL,
)
from async_hyperliquid.utils.decorators import private_key_required


class AsyncHyper(AsyncAPI):
    address: str
    is_mainnet: bool
    account: LocalAccount
    session: ClientSession
    base_url: str
    metas: dict[str, Any]
    vault: str | None

    coin_assets: dict[str, int]
    coin_names: dict[str, str]
    spot_tokens: dict[str, SpotMeta]
    asset_sz_decimals: dict[int, int]

    enable_evm: bool
    evm_info: EVMInfo
    evm_exchange: EVMExchange

    def __init__(
        self,
        address: str,
        api_key: str,
        is_mainnet: bool = True,
        enable_evm: bool = False,
        evm_rpc_url: str | None = None,
        private_key: str | None = None,
    ):
        self.address = address
        self.is_mainnet = is_mainnet
        self.account = Account.from_key(api_key)
        self.session = ClientSession(timeout=ClientTimeout(connect=3))
        self.base_url = MAINNET_API_URL if is_mainnet else TESTNET_API_URL
        self._info = InfoAPI(self.base_url, self.session)
        self._exchange = ExchangeAPI(
            self.account, self.session, self.base_url, address=self.address
        )
        self.metas = {}
        self.spot_tokens = {}
        self.vault = None

        if enable_evm:
            self._init_evm_client(private_key, evm_rpc_url)

    def _init_evm_client(
        self, private_key: str | None, rpc_url: str | None = None
    ):
        if rpc_url is None:
            rpc_url = HL_RPC_URL if self.is_mainnet else HL_TESTNET_RPC_URL

        self.evm_info = EVMInfo(rpc_url)

        if private_key is None:
            if self.account.address != self.address:
                raise ValueError(
                    "EVM Exchange client can not init without private key"
                )
            else:
                private_key = self.account.key.hex()

        self.evm_exchange = EVMExchange(rpc_url, private_key)

    def _init_coin_assets(self):
        self.coin_assets = {}
        self.spot_tokens = {}

        for asset, asset_info in enumerate(self.metas["perps"]["universe"]):
            self.coin_assets[asset_info["name"]] = asset

        for asset_info in self.metas["spots"]["universe"]:
            asset_name = asset_info["name"]
            asset = asset_info["index"] + SPOT_ASSET_BASE
            self.coin_assets[asset_name] = asset
            token_idx = asset_info["tokens"][0]
            self.spot_tokens[asset_name] = self.metas["spots"]["tokens"][
                token_idx
            ]

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
            base_name = base_info["name"]
            quote_name = quote_info["name"]
            name = f"{base_name}/{quote_name}"
            if name not in self.coin_names:
                self.coin_names[name] = asset_info["name"]

        self.coin_symbols = {
            v: k for k, v in self.coin_names.items() if not k.startswith("@")
        }

    def _init_asset_sz_decimals(self):
        self.asset_sz_decimals = {}
        for asset, asset_info in enumerate(self.metas["perps"]["universe"]):
            self.asset_sz_decimals[asset] = asset_info["szDecimals"]

        for asset_info in self.metas["spots"]["universe"]:
            asset = asset_info["index"] + SPOT_ASSET_BASE
            base, _quote = asset_info["tokens"]
            base_info = self.metas["spots"]["tokens"][base]
            self.asset_sz_decimals[asset] = base_info["szDecimals"]

    async def get_metas(self, perp_only: bool = False):
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

    async def get_coin_name(self, coin: str):
        if not hasattr(self, "coin_names") or coin not in self.coin_names:
            await self.init_metas()

        if coin not in self.coin_names:
            raise ValueError(f"Coin {coin} not found")

        return self.coin_names[coin]

    async def get_coin_asset(self, coin: str):
        coin_name = await self.get_coin_name(coin)

        if coin_name not in self.coin_assets:
            raise ValueError(f"Coin {coin}({coin_name}) not found")

        return self.coin_assets[coin_name]

    async def get_coin_symbol(self, coin: str):
        coin_name = await self.get_coin_name(coin)
        return self.coin_symbols[coin_name]

    async def get_coin_sz_decimals(self, coin: str):
        coin_name = await self.get_coin_name(coin)
        asset = await self.get_coin_asset(coin_name)
        return self.asset_sz_decimals[asset]

    async def get_token_info(self, coin: str):
        coin_name = await self.get_coin_name(coin)
        return self.spot_tokens[coin_name]

    async def get_token_id(self, coin: str):
        token_info = await self.get_token_info(coin)
        if not token_info:
            raise ValueError(f"Token {coin} not found")

        return token_info["tokenId"]

    async def get_market_price(self, coin: str):
        coin_name = await self.get_coin_name(coin)
        market_prices = await self.get_all_market_prices()
        return market_prices[coin_name]

    async def get_all_market_prices(
        self, market: Literal["spot", "perp", "all"] = "all"
    ):
        is_spot = market == "spot"
        is_perp = market == "perp"
        is_all = market == "all"

        prices: dict[str, float] = {}

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
                prices[coin] = float(perp_data[1][asset]["markPx"])  # type: ignore
            if (
                asset >= 10_000
                and (is_spot or is_all)
                and isinstance(spot_data, list)
            ):  # spot or all
                asset -= 10_000
                prices[coin] = float(spot_data[1][asset]["markPx"])  # type: ignore
        return prices

    async def get_perp_account_state(self, address: str | None = None):
        if not address:
            address = self.address

        return await self._info.get_perp_clearinghouse_state(address)

    async def get_spot_account_state(self, address: str | None = None):
        if not address:
            address = self.address
        return await self._info.get_spot_clearinghouse_state(address)

    async def get_account_state(self, address: str | None = None):
        account_state: AccountState = {"perp": {}, "spot": {}}  # type: ignore
        if not address:
            address = self.address

        account_state["perp"] = await self.get_perp_account_state(address)
        account_state["spot"] = await self.get_spot_account_state(address)

        return account_state

    async def get_account_portfolio(self, address: str | None = None):
        if not address:
            address = self.address

        return await self._info.get_user_portfolio(address)

    async def get_latest_ledgers(
        self,
        ledger_type: str = "deposit",
        address: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
    ):
        if not start_time:
            now = get_timestamp_ms()
            one_hour = ONE_HOUR_MS
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
    ):
        return await self.get_latest_ledgers(
            "deposit", address, start_time, end_time
        )

    async def get_latest_withdraws(
        self,
        address: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
    ):
        return await self.get_latest_ledgers(
            "withdraw", address, start_time, end_time
        )

    async def get_latest_transfers(
        self,
        address: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
    ):
        return await self.get_latest_ledgers(
            "accountClassTransfer", address, start_time, end_time
        )

    async def get_user_open_orders(
        self, address: str | None = None, is_frontend: bool = False
    ):
        if not address:
            address = self.address
        return await self._info.get_user_open_orders(address, is_frontend)

    async def get_order_status(self, order_id: int, address: str | None = None):
        if not address:
            address = self.address
        return await self._info.get_order_status(order_id, address)

    # Exchange API
    async def _slippage_price(
        self, coin: str, is_buy: bool, slippage: float, px: float
    ):
        coin_name = await self.get_coin_name(coin)
        if not px:
            all_mids = await self._info.get_all_mids()
            px = float(all_mids[coin_name])

        asset = await self.get_coin_asset(coin)
        is_spot = asset >= SPOT_ASSET_BASE
        sz_decimals = await self.get_coin_sz_decimals(coin)
        px *= (1 + slippage) if is_buy else (1 - slippage)
        px_decimals = (6 if not is_spot else 8) - sz_decimals
        return round_float(px, px_decimals)

    async def _round_sz_px(self, coin: str, sz: float, px: float):
        asset = await self.get_coin_asset(coin)
        is_spot = asset >= SPOT_ASSET_BASE
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
    ):
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

    async def cancel_order(
        self,
        coin: str,
        oid: int,
        *,
        vault: str | None = None,
        expires: int | None = None,
    ):
        return await self.cancel_orders(
            [(coin, int(oid))], vault=vault, expires=expires
        )

    async def batch_cancel_orders(
        self,
        cancels: BatchCancelRequest,
        *,
        vault: str | None = None,
        expires: int | None = None,
    ):
        return await self.cancel_orders(cancels, vault=vault, expires=expires)

    async def cancel_orders(
        self,
        cancels: BatchCancelRequest,
        *,
        vault: str | None = None,
        expires: int | None = None,
    ):
        action = {
            "type": "cancel",
            "cancels": [
                {"a": await self.get_coin_asset(coin), "o": oid}
                for coin, oid in cancels
            ],
        }

        if vault is None:
            vault = self.vault

        return await self._exchange.post_action(
            action, vault=vault, expires=expires
        )

    async def cancel_by_cloid(
        self,
        coin: str,
        cloid: Cloid,
        *,
        vault: str | None = None,
        expires: int | None = None,
    ):
        return await self.batch_cancel_by_cloid(
            [(coin, cloid)], vault=vault, expires=expires
        )

    async def batch_cancel_by_cloid(
        self,
        cancels: list[tuple[str, Cloid]],
        *,
        vault: str | None = None,
        expires: int | None = None,
    ):
        action = {
            "type": "cancelByCloid",
            "cancels": [
                {
                    "asset": await self.get_coin_asset(coin),
                    "cloid": cloid.to_raw(),
                }
                for coin, cloid in cancels
            ],
        }
        if vault is None:
            vault = self.vault

        return await self._exchange.post_action(
            action, vault=vault, expires=expires
        )

    async def schedule_cancel(
        self,
        time: int | None = None,
        *,
        vault: str | None = None,
        expires: int | None = None,
    ):
        action = {"type": "scheduleCancel", "time": time}
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
        *,
        vault: str | None = None,
        expires: int | None = None,
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
        return await self.batch_modify_orders(
            [modify], vault=vault, expires=expires
        )

    async def batch_modify_orders(
        self,
        modify_req: list[dict],
        *,
        vault: str | None = None,
        expires: int | None = None,
    ):
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
        return await self._exchange.post_action(
            action, vault=vault, expires=expires
        )

    async def update_leverage(
        self,
        leverage: int,
        coin: str,
        is_cross: bool = True,
        *,
        vault: str | None = None,
        expires: int | None = None,
    ):
        action = {
            "type": "updateLeverage",
            "asset": await self.get_coin_asset(coin),
            "isCross": is_cross,
            "leverage": leverage,
        }

        return await self._exchange.post_action(
            action, vault=vault, expires=expires
        )

    async def update_isolated_margin(
        self,
        usd: float,
        coin: str,
        *,
        vault: str | None = None,
        expires: int | None = None,
    ):
        usd_in_units = usd * USD_FACTOR
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

        return await self._exchange.post_action(
            action, vault=vault, expires=expires
        )

    async def set_referrer_code(self, code: str):
        action = {"type": "setReferrer", "code": code}
        return await self._exchange.post_action(action)

    @private_key_required
    async def usd_transfer(self, amount: float, dest: str):
        nonce = get_timestamp_ms()
        action = {
            "type": "usdSend",
            "amount": round_token_amount(amount, 2),
            "destination": dest,
            "time": nonce,
        }
        is_mainnet = self.base_url == MAINNET_API_URL
        sig = sign_usd_transfer_action(self.account, action, is_mainnet)
        return await self._exchange.post_action_with_sig(action, sig, nonce)

    @private_key_required
    async def spot_transfer(self, coin: str, amount: float, dest: str):
        token_info = await self.get_token_info(coin)
        token_name = token_info["name"]
        token_id = token_info["tokenId"]
        wei_decimals = token_info["weiDecimals"]
        token = f"{token_name}:{token_id}"
        nonce = get_timestamp_ms()
        action = {
            "type": "spotSend",
            "destination": dest,
            "token": token,
            "amount": round_token_amount(amount, wei_decimals),
            "time": nonce,
        }
        sig = sign_spot_transfer_action(self.account, action, self.is_mainnet)
        return await self._exchange.post_action_with_sig(action, sig, nonce)

    @private_key_required
    async def initiate_withdrawal(self, amount: float):
        nonce = get_timestamp_ms()
        action = {
            "type": "withdraw3",
            "amount": round_token_amount(amount, 2),
            "time": nonce,
            "destination": self.address,
        }
        sig = sign_withdraw_action(self.account, action, self.is_mainnet)
        return await self._exchange.post_action_with_sig(action, sig, nonce)

    @private_key_required
    async def usd_class_transfer(self, amount: float, to_perp: bool = False):
        nonce = get_timestamp_ms()
        action = {
            "type": "usdClassTransfer",
            "amount": round_token_amount(amount, 2),
            "toPerp": to_perp,
            "nonce": nonce,
        }
        sig = sign_usd_class_transfer_action(
            self.account, action, self.base_url == MAINNET_API_URL
        )
        return await self._exchange.post_action_with_sig(action, sig, nonce)

    @private_key_required
    async def send_asset(
        self,
        coin: str,
        amount: float,
        dest: str,
        source_dex: str,
        dest_dex: str,
        sub_account: str = "",
    ):
        token_info = await self.get_token_info(coin)
        token_name = token_info["name"]
        token_id = token_info["tokenId"]
        wei_decimals = token_info["weiDecimals"]
        token = f"{token_name}:{token_id}"
        nonce = get_timestamp_ms()
        action = {
            "type": "sendAsset",
            "token": token,
            "amount": round_token_amount(amount, wei_decimals),
            "destination": dest,
            "sourceDex": source_dex,
            "destinationDex": dest_dex,
            "fromSubAccount": sub_account,
            "nonce": nonce,
        }
        sig = sign_send_asset_action(self.account, action, self.is_mainnet)
        return await self._exchange.post_action_with_sig(action, sig, nonce)

    @private_key_required
    async def staking_deposit(self, amount: float):
        amount_in_wei = int(math.floor(amount * HYPE_FACTOR))
        nonce = get_timestamp_ms()
        action = {"type": "cDeposit", "wei": amount_in_wei, "nonce": nonce}
        sig = sign_staking_deposit_action(self.account, action, self.is_mainnet)
        return await self._exchange.post_action_with_sig(action, sig, nonce)

    @private_key_required
    async def staking_withdraw(self, amount: float):
        amount_in_wei = int(math.floor(amount * HYPE_FACTOR))
        nonce = get_timestamp_ms()
        action = {"type": "cWithdraw", "wei": amount_in_wei, "nonce": nonce}
        sig = sign_staking_withdraw_action(
            self.account, action, self.is_mainnet
        )
        return await self._exchange.post_action_with_sig(action, sig, nonce)

    @private_key_required
    async def token_delegate(
        self, validator: str, amount: float, is_undelegate: bool = False
    ):
        # HYPE decimals is 8
        amount_in_wei = int(math.floor(amount * HYPE_FACTOR))
        nonce = get_timestamp_ms()
        action = {
            "type": "tokenDelegate",
            "validator": validator,
            "wei": amount_in_wei,
            "isUndelegate": is_undelegate,
            "nonce": nonce,
        }
        sig = sign_token_delegate_action(self.account, action, self.is_mainnet)
        return await self._exchange.post_action_with_sig(action, sig, nonce)

    @private_key_required
    async def vault_transfer(
        self, vault: str, amount: float, is_deposit: bool = True
    ):
        usd_amount = int(math.floor(amount * USD_FACTOR))
        action = {
            "type": "vaultTransfer",
            "vaultAddress": vault,
            "isDeposit": is_deposit,
            "usd": usd_amount,
        }
        return await self._exchange.post_action(action)

    async def approve_agent(self, agent: str, name: str | None = None):
        nonce = get_timestamp_ms()
        action = {
            "type": "approveAgent",
            "agentAddress": agent,
            "agentName": name or "",
            "nonce": nonce,
        }
        sig = sign_approve_agent_action(self.account, action, self.is_mainnet)
        if name is None:
            del action["agentName"]

        return await self._exchange.post_action_with_sig(action, sig, nonce)

    async def approve_builder_fee(self, max_fee_rate: float, builder: str):
        nonce = get_timestamp_ms()
        action = {
            "type": "approveBuilderFee",
            "maxFeeRate": f"{max_fee_rate:.3%}",
            "builder": builder,
            "nonce": nonce,
        }
        sig = sign_approve_builder_fee_action(
            self.account, action, self.is_mainnet
        )
        return await self._exchange.post_action_with_sig(action, sig, nonce)

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
        sz_str = str(sz).rstrip("0").rstrip(".")
        action = {
            "type": "twapOrder",
            "twap": {
                "a": asset,
                "b": is_buy,
                "s": sz_str,
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

    async def convert_to_multi_sig_user(self, users: list[str], threshold: int):
        nonce = get_timestamp_ms()
        signers = {"authorizedUsers": sorted(users), "threshold": threshold}
        action = {
            "type": "convertToMultiSigUser",
            "signers": signers,
            "nonce": nonce,
        }
        sig = sign_convert_to_multi_sig_user_action(
            self.account, action, self.is_mainnet
        )
        return await self._exchange.post_action_with_sig(action, sig, nonce)

    async def reserve_request_weight(
        self, weight: int, *, expires: int | None = None
    ):
        action = {"type": "reserveRequestWeight", "weight": weight}
        return await self._exchange.post_action(action, expires=expires)

    async def use_big_block(self, enable: bool):
        action = {"type": "evmUserModify", "usingBigBlocks": enable}
        return await self._exchange.post_action(action)

    async def get_all_positions(self, address: str | None = None):
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

    def get_leverage_from_positions(self, positions: list[Position]):
        leverages = {}
        for position in positions:
            coin = position["coin"]
            leverage = position["leverage"]["value"]
            leverages[coin] = leverage

        return leverages
