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
    department_mix: dict[str, int]
    brand_mix: dict[str, int]
    salesperson_mix: dict[str, int]


def _as_float(value: str | None) -> float:
    try:
        return float(value or 0)
    except ValueError:
        return 0.0


def load_transaction_stats(path: Path) -> TransactionStats:
    if not path.exists():
        return TransactionStats(0, 0, 0.0, {}, {}, {}, {})

    orders: dict[str, float] = defaultdict(float)
    hours: Counter[int] = Counter()
    departments: Counter[str] = Counter()
    brands: Counter[str] = Counter()
    staff: Counter[str] = Counter()
    row_count = 0

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            row_count += 1
            order_id = row.get("order_id") or row.get("invoice_number") or "unknown"
            orders[order_id] += _as_float(row.get("total_amount") or row.get("NMV"))
            departments[row.get("dep_name") or "unknown"] += 1
            brands[row.get("brand_name") or "unknown"] += 1
            staff[row.get("salesperson_name") or "unknown"] += 1
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
        department_mix=dict(departments.most_common(10)),
        brand_mix=dict(brands.most_common(10)),
        salesperson_mix=dict(staff.most_common(10)),
    )
