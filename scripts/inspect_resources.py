import csv
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def inspect_store_archives() -> dict:
    archives = {}
    for archive_path in sorted(ROOT.glob("data/Store *.zip")):
        with zipfile.ZipFile(archive_path) as z:
            names = z.namelist()
            archives[archive_path.name] = {
                "package_files": len(names),
                "layout_images": [name for name in names if name.lower().endswith(".png")],
                "cameras": [name for name in names if name.lower().endswith(".mp4")],
            }
    return archives


def inspect_transactions() -> dict:
    orders: set[str] = set()
    order_rev: defaultdict[str, float] = defaultdict(float)
    brand: Counter[str] = Counter()
    store: Counter[str] = Counter()
    hourly: Counter[int] = Counter()
    rows = 0
    with (ROOT / "data" / "POS_transactions.csv").open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows += 1
            oid = row.get("order_id") or row.get("invoice_number") or "unknown"
            orders.add(oid)
            try:
                order_rev[oid] += float(row.get("total_amount") or row.get("NMV") or 0)
            except ValueError:
                pass
            brand[row.get("brand_name") or "unknown"] += 1
            store[row.get("store_id") or "unknown"] += 1
            if row.get("order_time"):
                hourly[int(row["order_time"].split(":")[0])] += 1
    return {
        "rows": rows,
        "orders": len(orders),
        "revenue": round(sum(order_rev.values()), 2),
        "brands": brand.most_common(8),
        "stores": store.most_common(8),
        "hourly": dict(sorted(hourly.items())),
    }


def main() -> None:
    print(json.dumps({"store_archives": inspect_store_archives(), "transactions": inspect_transactions()}, indent=2))


if __name__ == "__main__":
    main()
