import csv
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def inspect_workbook() -> dict:
    with zipfile.ZipFile(ROOT / "data" / "store_layout.xlsx") as z:
        names = z.namelist()
        return {
            "media": [name for name in names if name.startswith("xl/media/")],
            "drawings": [name for name in names if "drawing" in name.lower()],
            "package_files": len(names),
        }


def inspect_transactions() -> dict:
    orders: set[str] = set()
    order_rev: defaultdict[str, float] = defaultdict(float)
    dept: Counter[str] = Counter()
    brand: Counter[str] = Counter()
    salesperson: Counter[str] = Counter()
    hourly: Counter[int] = Counter()
    rows = 0
    with (ROOT / "data" / "transactions.csv").open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows += 1
            oid = row.get("order_id") or row.get("invoice_number") or "unknown"
            orders.add(oid)
            try:
                order_rev[oid] += float(row.get("total_amount") or row.get("NMV") or 0)
            except ValueError:
                pass
            dept[row.get("dep_name") or "unknown"] += 1
            brand[row.get("brand_name") or "unknown"] += 1
            salesperson[row.get("salesperson_name") or "unknown"] += 1
            if row.get("order_time"):
                hourly[int(row["order_time"].split(":")[0])] += 1
    return {
        "rows": rows,
        "orders": len(orders),
        "revenue": round(sum(order_rev.values()), 2),
        "departments": dept.most_common(8),
        "brands": brand.most_common(8),
        "salespeople": salesperson.most_common(8),
        "hourly": dict(sorted(hourly.items())),
    }


def main() -> None:
    print(json.dumps({"workbook": inspect_workbook(), "transactions": inspect_transactions()}, indent=2))


if __name__ == "__main__":
    main()
