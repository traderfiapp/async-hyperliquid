import time
from typing import Any
from decimal import Decimal


def get_timestamp_ms() -> int:
    return int(time.time() * 1000)


def is_numeric(n: Any) -> bool:
    try:
        Decimal(n)
        return True
    except ValueError:
        return False


def convert_to_numeric(data: Any) -> Any:
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, str) and is_numeric(v):
                data[k] = Decimal(v)
            else:
                data[k] = convert_to_numeric(v)
    elif isinstance(data, list):
        for i in data:
            convert_to_numeric(i)
    return data


def get_float_significant_figures(value: float) -> int:
    if value == 0:
        return 1

    str_value = f"{value:.8g}"

    digits = str_value.replace(".", "").lstrip("0")

    if "e" in digits.lower():
        mantissa = digits.split("e")[0]
        digits = mantissa.rstrip("0")

    return len(digits)


def round_px(px: float, decimals: int) -> float | int:
    f = float(px)
    v = round_float(f, decimals)
    mantissa = get_float_significant_figures(v)
    if mantissa > 5:
        return int(v)
    else:
        return v


def round_float(value: float, decimals: int) -> float:
    v = float(value)
    return round(float(f"{v:.8g}"), decimals)
