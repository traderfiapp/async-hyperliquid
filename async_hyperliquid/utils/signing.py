from typing import Any, List
from decimal import Decimal

import msgpack
from eth_account import Account
from eth_utils.crypto import keccak
from eth_account.messages import encode_typed_data
from eth_utils.conversions import to_hex

from async_hyperliquid.utils.types import (
    OrderType,
    OrderAction,
    EncodedOrder,
    GroupOptions,
    OrderBuilder,
    SignedAction,
    PlaceOrderRequest,
)
from async_hyperliquid.utils.constants import (
    USD_SEND_SIGN_TYPES,
    USD_CLASS_TRANSFER_SIGN_TYPES,
)


def address_to_bytes(address: str) -> bytes:
    return bytes.fromhex(address[2:] if address.startswith("0x") else address)


def hash_action(action, vault, nonce) -> bytes:
    data = msgpack.packb(action)
    data += nonce.to_bytes(8, "big")

    if vault is None:
        data += b"\x00"
    else:
        data += b"\x01"
        data += bytes.fromhex(vault.removeprefix("0x"))
    return keccak(data)


def sign_inner(wallet: Account, data: dict) -> SignedAction:
    encodes = encode_typed_data(full_message=data)
    signed = wallet.sign_message(encodes)
    return {
        "r": to_hex(signed["r"]),
        "s": to_hex(signed["s"]),
        "v": signed["v"],
    }


def sign_action(
    wallet: Account,
    action: dict,
    active_pool: str | None,
    nonce: int,
    is_mainnet: bool,
) -> SignedAction:
    h = hash_action(action, active_pool, nonce)
    msg = {"source": "a" if is_mainnet else "b", "connectionId": h}
    data = {
        "domain": {
            "chainId": 1337,
            "name": "Exchange",
            "verifyingContract": "0x0000000000000000000000000000000000000000",
            "version": "1",
        },
        "types": {
            "Agent": [
                {"name": "source", "type": "string"},
                {"name": "connectionId", "type": "bytes32"},
            ],
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
        },
        "primaryType": "Agent",
        "message": msg,
    }
    return sign_inner(wallet, data)


def round_float(x: float) -> str:
    rounded = f"{x:.8f}"
    if abs(float(rounded) - x) >= 1e-12:
        raise ValueError("round_float causes rounding", x)

    if rounded == "-0":
        rounded = "0"
    normalized = Decimal(rounded).normalize()
    return f"{normalized:f}"


def ensure_order_type(order_type: OrderType) -> OrderType:
    if "limit" in order_type:
        return {"limit": order_type["limit"]}
    elif "trigger" in order_type:
        return {
            "trigger": {
                "isMarket": order_type["trigger"]["isMarket"],
                "triggerPx": round_float(
                    float(order_type["trigger"]["triggerPx"])
                ),
                "tpsl": order_type["trigger"]["tpsl"],
            }
        }

    raise ValueError("Invalid order type", order_type)


def encode_order(order: PlaceOrderRequest) -> EncodedOrder:
    encoded_order: EncodedOrder = {
        "a": order["asset"],
        "b": order["is_buy"],
        "p": round_float(order["px"]),
        "s": round_float(order["sz"]),
        "r": order["ro"],
        "t": ensure_order_type(order["order_type"]),
    }

    if order.get("cloid", None) is not None:
        encoded_order["c"] = order["cloid"].to_raw()  # type: ignore

    return encoded_order


def orders_to_action(
    encoded_orders: List[EncodedOrder],
    grouping: GroupOptions = "na",
    builder: OrderBuilder | None = None,
) -> OrderAction:
    action: OrderAction = {
        "type": "order",
        "orders": encoded_orders,
        "grouping": grouping,
    }
    if builder:
        action["builder"] = builder
    return action


def user_signed_payload(primary_type, payload_types, action):
    chain_id = int(action["signatureChainId"], 16)
    return {
        "domain": {
            "name": "HyperliquidSignTransaction",
            "version": "1",
            "chainId": chain_id,
            "verifyingContract": "0x0000000000000000000000000000000000000000",
        },
        "types": {
            primary_type: payload_types,
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
        },
        "primaryType": primary_type,
        "message": action,
    }


def sign_user_signed_action(
    wallet: Account,
    action: dict,
    payload_types: List[dict],
    primary_type: str,
    is_mainnet: bool,
):
    action["signatureChainId"] = "0x66eee"
    action["hyperliquidChain"] = "Mainnet" if is_mainnet else "Testnet"
    data = user_signed_payload(primary_type, payload_types, action)
    return sign_inner(wallet, data)


def sign_usd_transfer_action(wallet: Account, action, is_mainnet: bool):
    return sign_user_signed_action(
        wallet,
        action,
        USD_SEND_SIGN_TYPES,
        "HyperliquidTransaction:UsdSend",
        is_mainnet,
    )


def sign_usd_class_transfer_action(
    wallet: Account, action: Any, is_mainnet: bool
):
    return sign_user_signed_action(
        wallet,
        action,
        USD_CLASS_TRANSFER_SIGN_TYPES,
        "HyperliquidTransaction:UsdClassTransfer",
        is_mainnet,
    )
