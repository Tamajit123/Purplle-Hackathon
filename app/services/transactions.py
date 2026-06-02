from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class TransactionStats:
    row_count: int
    order_count: int
    revenue: float
    hourly_orders: dict[int, int]
    brand_mix: dict[str, int]
    store_mix: dict[str, int]


def _as_float(value: str | None) -> float:
    try:
        return float(value or 0)
    except ValueError:
        return 0.0


def load_transaction_stats(path: Path) -> TransactionStats:
    if not path.exists():
        return TransactionStats(0, 0, 0.0, {}, {}, {})

    orders: dict[str, float] = defaultdict(float)
    hours: Counter[int] = Counter()
    brands: Counter[str] = Counter()
    stores: Counter[str] = Counter()
    row_count = 0

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            row_count += 1
            order_id = row.get("order_id") or row.get("invoice_number") or "unknown"
            orders[order_id] += _as_float(row.get("total_amount") or row.get("NMV"))
            brands[row.get("brand_name") or "unknown"] += 1
            stores[row.get("store_id") or "unknown"] += 1
            t = row.get("order_time")
            if t:
                try:
                    hours[datetime.strptime(t, "%H:%M:%S").hour] += 1
                except ValueError:
                    pass

    return TransactionStats(
        row_count=row_count,
        order_count=len(orders),
        revenue=round(sum(orders.values()), 2),
        hourly_orders=dict(sorted(hours.items())),
        brand_mix=dict(brands.most_common(10)),
        store_mix=dict(stores.most_common(10)),
    )
