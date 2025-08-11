from typing import Any

from aiohttp import ClientSession

from async_hyperliquid.async_api import AsyncAPI
from async_hyperliquid.utils.types import (
    Depth,
    Candles,
    Endpoint,
    Referral,
    UserFees,
    UserRole,
    Portfolio,
    RateLimit,
    UserFills,
    VaultInfo,
    Delegations,
    SubAccounts,
    FundingRates,
    TokenDetails,
    UserFundings,
    VaultDeposits,
    CandleInterval,
    StakingHistory,
    StakingRewards,
    StakingSummary,
    TwapSliceFills,
    UserOpenOrders,
    ActiveAssetData,
    OrderWithStatus,
    SpotDeployState,
    AssetFundingInfo,
    HistoricalOrders,
    PerpDeployStatus,
    PerpMetaResponse,
    SpotMetaResponse,
    ClearinghouseState,
    PerpMetaCtxResponse,
    SpotMetaCtxResponse,
    SpotClearinghouseState,
)


class InfoAPI(AsyncAPI):
    def __init__(self, base_url: str, session: ClientSession):
        super().__init__(Endpoint.INFO, base_url, session)

    async def get_all_mids(self) -> dict[str, int]:
        payloads = {"type": "allMids"}
        return await self.post(payloads)

    async def get_user_open_orders(
        self, address: str, is_frontend: bool = False, dex: str = ""
    ) -> UserOpenOrders:
        payloads = {
            "type": "frontendOpenOrders" if is_frontend else "openOrders",
            "user": address,
        }
        return await self.post(payloads)

    async def get_user_fills(
        self,
        address: str,
        aggregated: bool = False,
        *,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> UserFills:
        payloads = {
            "type": "userFillsByTime" if start_time else "userFills",
            "user": address,
            "aggregateByTime": aggregated,
        }
        if start_time:
            payloads["startTime"] = start_time
            payloads["endTime"] = end_time
        return await self.post(payloads)

    async def get_user_rate_limit(self, address: str) -> RateLimit:
        payloads = {"type": "userRateLimit", "user": address}
        return await self.post(payloads)

    async def get_order_status(
        self, order_id: str | int, address: str
    ) -> OrderWithStatus:
        payloads = {"type": "orderStatus", "user": address, "oid": order_id}
        return await self.post(payloads)

    async def get_depth(
        self, coin: str, level: int | None = None, mantissa: int | None = None
    ) -> list[Depth]:
        payloads: dict[str, Any] = {"type": "l2Book", "coin": coin}
        if level:
            payloads["nSigFigs"] = level
        if level and level == 5 and mantissa:
            payloads["mantissa"] = mantissa
        return await self.post(payloads)

    async def get_candles(
        self, coin: str, interval: CandleInterval, start: int, end: int
    ) -> Candles:
        req = {
            "coin": coin,
            "interval": interval.value,
            "startTime": start,
            "endTime": end,
        }
        payloads = {"type": "candleSnapshot", "req": req}
        return await self.post(payloads)

    async def check_user_builder_fee(self, user: str, builder: str) -> int:
        payloads = {"type": "maxBuilderFee", "user": user, "builder": builder}
        return await self.post(payloads)

    async def get_user_order_history(self, address: str) -> HistoricalOrders:
        payloads = {"type": "historicalOrders", "user": address}
        return await self.post(payloads)

    async def get_user_twap_fills(self, address: str) -> TwapSliceFills:
        payloads = {"type": "userTwapSliceFills", "user": address}
        return await self.post(payloads)

    async def get_user_subaccounts(self, address: str) -> SubAccounts:
        payloads = {"type": "subAccounts", "user": address}
        return await self.post(payloads)

    async def get_vault_info(
        self, address: str, user: str | None = None
    ) -> VaultInfo:
        payloads = {"type": "vaultDetails", "vaultAddress": address}
        if user:
            payloads["user"] = user
        return await self.post(payloads)

    async def get_user_vault_deposits(self, address: str) -> VaultDeposits:
        payloads = {"type": "userVaultEquities", "user": address}
        return await self.post(payloads)

    async def get_user_role(self, address: str) -> UserRole:
        payloads = {"type": "userRole", "user": address}
        return await self.post(payloads)

    async def get_user_portfolio(self, address: str) -> Portfolio:
        payloads = {"type": "portfolio", "user": address}
        return await self.post(payloads)

    async def get_user_referral(self, address: str) -> Referral:
        payloads = {"type": "referral", "user": address}
        return await self.post(payloads)

    async def get_user_fees(self, address: str) -> UserFees:
        payloads = {"type": "userFees", "user": address}
        return await self.post(payloads)

    async def get_user_delegations(self, address: str) -> Delegations:
        payloads = {"type": "delegations", "user": address}
        return await self.post(payloads)

    async def get_user_staking(self, address: str) -> Delegations:
        payloads = {"type": "delegations", "user": address}
        return await self.post(payloads)

    async def get_user_staking_summary(self, address: str) -> StakingSummary:
        payloads = {"type": "delegatorSummary", "user": address}
        return await self.post(payloads)

    async def get_user_staking_history(self, address: str) -> StakingHistory:
        payloads = {"type": "delegatorHistory", "user": address}
        return await self.post(payloads)

    async def get_user_staking_rewards(self, address: str) -> StakingRewards:
        payloads = {"type": "delegatorRewards", "user": address}
        return await self.post(payloads)

    # Perpetuals
    async def get_perp_meta(self) -> PerpMetaResponse:
        payloads = {"type": "meta"}
        return await self.post(payloads)

    async def get_perp_meta_ctx(self) -> PerpMetaCtxResponse:
        payloads = {"type": "metaAndAssetCtxs"}
        return await self.post(payloads)

    async def get_perp_clearinghouse_state(
        self, address: str
    ) -> ClearinghouseState:
        payloads = {"type": "clearinghouseState", "user": address}
        return await self.post(payloads)

    async def get_user_funding(
        self,
        address: str,
        start_time: int,
        end_time: int | None = None,
        is_funding: bool = True,
    ) -> UserFundings:
        payloads = {
            "type": "userFunding"
            if is_funding
            else "userNonFundingLedgerUpdates",
            "user": address,
            "startTime": start_time,
            "endTime": end_time,
        }
        return await self.post(payloads)

    async def get_funding_rates(
        self, coin: str, start_time: int, end_time: int | None = None
    ) -> FundingRates:
        payloads = {
            "type": "fundingHistory",
            "coin": coin,
            "startTime": start_time,
            "endTime": end_time,
        }
        return await self.post(payloads)

    async def get_predicted_funding(self) -> AssetFundingInfo:
        payloads = {"type": "predictedFundings"}
        return await self.post(payloads)

    async def get_perps_at_open_interest_cap(self) -> list[str]:
        payloads = {"type": "perpsAtOpenInterestCap"}
        return await self.post(payloads)

    async def get_perp_deploy_status(self) -> PerpDeployStatus:
        payloads = {"type": "perpDeployAuctionStatus"}
        return await self.post(payloads)

    async def get_user_active_asset_data(
        self, address: str, coin: str
    ) -> ActiveAssetData:
        payloads = {"type": "activeAssetData", "user": address, "coin": coin}
        return await self.post(payloads)

    # Spot
    async def get_spot_meta(self) -> SpotMetaResponse:
        payloads = {"type": "spotMeta"}
        return await self.post(payloads)

    async def get_spot_meta_ctx(self) -> SpotMetaCtxResponse:
        payloads = {"type": "spotMetaAndAssetCtxs"}
        return await self.post(payloads)

    async def get_user_token_balances(
        self, address: str
    ) -> SpotClearinghouseState:
        payloads = {"type": "spotClearinghouseState", "user": address}
        return await self.post(payloads)

    async def get_spot_clearinghouse_state(
        self, address: str
    ) -> SpotClearinghouseState:
        payloads = {"type": "spotClearinghouseState", "user": address}
        return await self.post(payloads)

    async def get_spot_deploy_state(self, address: str) -> SpotDeployState:
        payloads = {"type": "spotDeployState", "user": address}
        return await self.post(payloads)

    async def get_token_info(self, token_id: str) -> TokenDetails:
        payloads = {"type": "tokenDetails", "tokenId": token_id}
        return await self.post(payloads)
