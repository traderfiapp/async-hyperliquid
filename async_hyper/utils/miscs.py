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
