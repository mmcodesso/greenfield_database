from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import numpy as np
import pandas as pd

from CharlesRiver_dataset.settings import GenerationContext


def next_id(context: GenerationContext, table_name: str) -> int:
    current = context.counters[table_name]
    context.counters[table_name] += 1
    return current


def format_doc_number(prefix: str, year: int, sequence: int) -> str:
    return f"{prefix}-{year}-{sequence:06d}"


def money(value: float | Decimal) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def qty(value: float | Decimal, places: str = "0.01") -> float:
    return float(Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_UP))


def random_date_in_month(rng: np.random.Generator, year: int, month: int) -> pd.Timestamp:
    start = pd.Timestamp(year=year, month=month, day=1)
    end = start + pd.offsets.MonthEnd(1)
    days = (end - start).days
    return start + pd.Timedelta(days=int(rng.integers(0, days + 1)))


def weighted_choice(rng: np.random.Generator, values: list[Any], weights: list[float]) -> Any:
    probs = np.array(weights, dtype=float)
    probs = probs / probs.sum()
    return rng.choice(values, p=probs)
