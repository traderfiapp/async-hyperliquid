from enum import Enum
from typing import Any, List, Tuple, Union, Literal, Optional, TypedDict

from typing_extensions import NotRequired


class Cloid:
    def __init__(self, raw_cloid: str):
        self._raw_cloid: str = raw_cloid
        self._validate()

    def _validate(self) -> None:
        if not self._raw_cloid[:2] == "0x":
            raise TypeError("cloid is not a hex string")
        if not len(self._raw_cloid[2:]) == 32:
            raise TypeError("cloid is not 16 bytes")

    def __str__(self) -> str:
        return str(self._raw_cloid)

    def __repr__(self) -> str:
        return str(self._raw_cloid)

    @staticmethod
    def from_int(cloid: int) -> "Cloid":
        return Cloid(f"{cloid:#034x}")

    @staticmethod
    def from_str(cloid: str) -> "Cloid":
        return Cloid(cloid)

    def to_raw(self) -> str:
        return self._raw_cloid


class SignedAction(TypedDict):
    r: str
    s: str
    v: int


class LimitOrderOptions(TypedDict):
    tif: Literal["Alo", "Ioc", "Gtc"]


class LimitOrderType(TypedDict):
    limit: LimitOrderOptions


class LimitOrder(Enum):
    ALO = {"limit": {"tif": "Alo"}}
    IOC = {"limit": {"tif": "Ioc"}}
    GTC = {"limit": {"tif": "Gtc"}}


class TriggerOrderOptions(TypedDict):
    isMarket: bool
    triggerPx: str
    tpsl: Literal["tp", "sl"]


class TriggerOrderType(TypedDict):
    trigger: TriggerOrderOptions


OrderType = Union[LimitOrderType, TriggerOrderType]


class PlaceOrderRequest(TypedDict):
    coin: str
    is_buy: bool
    sz: float
    limit_px: float
    reduce_only: bool
    order_type: OrderType
    cloid: NotRequired[Cloid]


class CancelOrderRequest(TypedDict):
    coin: str
    oid: str
    cloid: NotRequired[Cloid]


class EncodedOrder(TypedDict):
    a: int  # asset universe index
    b: bool  # is_buy
    p: str  # limit_px
    s: str  # size
    r: bool  # reduce_only
    t: OrderType  # order type
    c: NotRequired[Cloid]  # cloid


class OrderBuilder(TypedDict):
    b: str  # builder address
    f: float


class OrderAction(TypedDict):
    type: Literal["order"]
    orders: List[EncodedOrder]
    grouping: Literal["na", "normalTpsl", "positionTpsl"]
    builder: NotRequired[OrderBuilder]


class Endpoint(str, Enum):
    INFO = "info"
    EXCHANGE = "exchange"


class RateLimit(TypedDict):
    cumVlm: str
    nRequestsUsed: int
    nRequestsCap: int


class Order(TypedDict):
    coin: str
    limitPx: str
    oid: int
    side: Literal["A", "B"]  # A: ask/sell/short, B: bid/buy/long
    sz: str
    timestamp: int


class FrontendOrder(Order):
    isPositionTpsl: bool
    orderType: str  # Maybe Literal["Limit", "Trigger"] is more accurate
    origSz: str
    reduceOnly: bool
    isTrigger: bool
    triggerCondition: str
    triggerPx: str


class FilledOrder(TypedDict):
    coin: str
    sz: str
    px: str
    side: Literal["A", "B"]
    time: int
    startPosition: str
    dir: str
    closedPnl: str
    hash: str
    oid: int
    crossed: bool
    fee: str
    tid: int
    feeToken: str
    builderFee: NotRequired[str]


class OrderStatus(str, Enum):
    OPEN = "open"
    FILLED = "filled"
    CANCELED = "canceled"
    TRIGGERED = "triggered"
    REJECTED = "rejected"
    MARGIN_CANCELED = "marginCanceled"
    VAULT_WITHDRAWAL_CANCELED = "vaultWithdrawalCanceled"
    OPEN_INSTEREST_CAP_CANCELED = "openInterestCapCanceled"
    SELF_TRADE_CANCELED = "selfTradeCanceled"
    REDUCE_ONLY_CANCELED = "reduceOnlyCanceled"
    SIBLING_FILLED_CANCELED = "siblingFilledCanceled"
    DELISTED_CANCELED = "delistedCanceled"
    LIQUIDATED_CANCELED = "liquidatedCanceled"
    SCHEDULED_CANCELED = "scheduledCanceled"


class FilledOrderWithStatus(FrontendOrder):
    tif: str
    cloid: Optional[str]
    children: List[Any]


class InnerOrderWithStatus(TypedDict):
    order: FilledOrderWithStatus
    status: OrderStatus
    statusTimestamp: int


class OrderWithStatus(TypedDict):
    status: Literal["order", "unknowOid"]
    order: NotRequired[InnerOrderWithStatus]


class L2Book(TypedDict):
    px: str
    sz: str
    n: int


class Depth(TypedDict):
    bids: List[L2Book]
    asks: List[L2Book]


class PerpMeta(TypedDict):
    name: str
    szDecimals: int
    maxLeverage: int
    onlyIsolated: NotRequired[bool]
    isDelisted: NotRequired[bool]


class PerpMetaResponse(TypedDict):
    universe: List[PerpMeta]


class PerpMetaCtx(TypedDict):
    dayNtlVlm: str
    funding: str
    impactPxs: List[str]
    markPx: str
    midPx: str
    openInterest: str
    oraclePx: str
    premium: str
    prevDayPx: str


PerpMetaCtxResponse = List[Union[PerpMetaResponse, List[PerpMetaCtx]]]


class AssetFunding(TypedDict):
    allTime: str
    sinceChange: str
    sinceOpen: str


class AssetLeverage(TypedDict):
    rawUsd: str
    type: str
    value: int


class Position(TypedDict):
    coin: str
    cumFunding: AssetFunding
    entryPx: str
    leverage: AssetLeverage
    liquidationPx: str
    marginUsed: str
    maxLeverage: int
    positionValue: str
    returnOnEquity: str
    szi: str
    unrealizedPnl: str


class AssetPosition(TypedDict):
    type: str
    position: Position


class MarginSummary(TypedDict):
    accountValue: str
    totalMarginUsed: str
    totalNtlPos: str
    totalRawUsd: str


class ClearinghouseState(TypedDict):
    assetPositions: List[AssetPosition]
    crosssMaintenanceMarginUsed: str
    crossMarginSummary: MarginSummary
    marginSummary: MarginSummary
    time: int
    withdrawable: str


class UserFundingDelta(TypedDict):
    coin: str
    fundingRate: str
    szi: str
    type: str
    usdc: str


class UserFunding(TypedDict):
    delta: UserFundingDelta
    hash: str
    time: int


class FundingRate(TypedDict):
    coin: str
    fundingRate: str
    premium: str
    time: int


class Token(TypedDict):
    name: str
    index: int
    isCanonical: bool


class TokenPairs(Token):
    tokens: Tuple[int, int]


class SpotMeta(Token):
    szDecimals: int
    weiDecimals: int
    tokenId: str
    evmContract: Optional[str]
    fullName: Optional[str]


class SpotMetaResponse(TypedDict):
    tokens: List[SpotMeta]
    universe: List[TokenPairs]


class SpotMetaCtx(TypedDict):
    dayNtlVlm: str
    markPx: str
    midPx: str
    prevDayPx: str


SpotMetaCtxResponse = List[Union[SpotMetaResponse, List[SpotMetaCtx]]]


class TokenBalance(TypedDict):
    coin: str
    token: int
    hold: str
    total: str
    entryNtl: str


class SpotClearinghouseState(TypedDict):
    balances: List[TokenBalance]


class AccountState(TypedDict):
    perp: ClearinghouseState
    spot: SpotClearinghouseState


class GasAuction(TypedDict):
    startTimeSeconds: int
    durationSeconds: int
    startGas: str
    currentGas: Optional[str]
    endGas: str


class DeployStateSpec(TypedDict):
    name: str
    szDecimals: int
    weiDecimals: int


class DeployState(TypedDict):
    token: int
    spec: DeployStateSpec
    fullName: str
    spots: List[int]
    maxSupply: int
    hyperliquidityGenesisBalance: str
    totalGenesisBalanceWei: str
    userGenesisBalances: List[Tuple[str, str]]
    existingTokenGenesisBalances: List[Tuple[int, str]]


class SpotDeployState(TypedDict):
    states: List[DeployState]
    gasAuction: GasAuction


class TokenGenesis(TypedDict):
    userBalances: List[Tuple[str, str]]
    existingTokenBalances: List[Any]


class TokenDetails(TypedDict):
    name: str
    maxSupply: str
    totalSupply: str
    circulatingSupply: str
    szDecimals: int
    weiDecimals: int
    midPx: str
    markPx: str
    prevDayPx: str
    genesis: List[TokenGenesis]
    deployer: str
    deployGas: str
    deployTime: str
    seededUsdc: str
    nonCirculatingUserBalances: List[Any]
    futureEmissions: str
