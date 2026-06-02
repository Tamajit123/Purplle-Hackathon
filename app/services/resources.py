from __future__ import annotations

import zipfile
from pathlib import Path

from app.core.settings import Settings
from app.services.transactions import load_transaction_stats


def discover_store_archives(root: Path) -> list[Path]:
    return sorted([path for path in root.glob("Store *.zip") if path.is_file()])


def _store_slug(archive: Path) -> str:
    return archive.stem.lower().replace(" ", "_")


def ensure_layout_asset(archive: Path) -> str | None:
    asset_dir = Path("dashboard/assets/stores") / _store_slug(archive)
    asset_dir.mkdir(parents=True, exist_ok=True)
    asset_path = asset_dir / "layout.png"
    if asset_path.exists():
        return f"/dashboard/assets/stores/{_store_slug(archive)}/layout.png"

    with zipfile.ZipFile(archive) as z:
        layout_candidates = [name for name in z.namelist() if name.lower().endswith(".png")]
        if not layout_candidates:
            return None
        asset_path.write_bytes(z.read(layout_candidates[0]))
    return f"/dashboard/assets/stores/{_store_slug(archive)}/layout.png"


def camera_inventory(archive: Path) -> list[dict]:
    if not archive.exists():
        return []
    cameras: list[dict] = []
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            if name.lower().endswith(".mp4"):
                filename = Path(name).name
                cameras.append(
                    {
                        "camera_id": Path(filename).stem.replace(" ", "_").upper(),
                        "name": Path(filename).stem,
                        "path": f"{archive.name}::{name}",
                        "size_mb": round(z.getinfo(name).file_size / (1024 * 1024), 1),
                        "status": "ready",
                    }
                )
    return cameras


def layout_manifest(settings: Settings) -> dict:
    archives = discover_store_archives(settings.store_data_root)
    stores = []
    for archive in archives:
        with zipfile.ZipFile(archive) as z:
            cameras = [name for name in z.namelist() if name.lower().endswith(".mp4")]
            layouts = [name for name in z.namelist() if name.lower().endswith(".png")]
        stores.append(
            {
                "store": archive.stem,
                "archive": str(archive),
                "asset": ensure_layout_asset(archive),
                "camera_count": len(cameras),
                "layout_count": len(layouts),
                "cameras": camera_inventory(archive),
            }
        )
    active = stores[0] if stores else None
    return {
        "available": bool(stores),
        "source": str(archives[0]) if archives else None,
        "asset": active["asset"] if active else None,
        "stores": stores,
        "active_store": active["store"] if active else None,
        "cameras": active["cameras"] if active else [],
        "zones_configured": ["entrance_gate", "beauty_wall", "billing_counter"],
    }


def evaluation_manifest(path: Path = Path("data/evaluation_framework.pdf")) -> dict:
    return {
        "available": path.exists(),
        "source": str(path),
        "acceptance_gate": [
            "docker compose up runs without manual intervention",
            "/metrics endpoint returns a valid response",
            "detection pipeline produces structured events",
            "DESIGN.md and CHOICES.md are present",
            "system remains stable during basic execution",
        ],
        "scoring": [
            {"area": "Detection Pipeline", "weight": 30},
            {"area": "API and Business Logic", "weight": 35},
            {"area": "Production Readiness", "weight": 20},
            {"area": "Engineering Thinking", "weight": 15},
        ],
    }


def retail_mix(settings: Settings) -> dict:
    stats = load_transaction_stats(settings.transaction_csv_path)
    return {
        "rows": stats.row_count,
        "orders": stats.order_count,
        "revenue": stats.revenue,
        "hourly_orders": stats.hourly_orders,
        "brand_mix": stats.brand_mix,
        "store_mix": stats.store_mix,
    }


def resource_summary(settings: Settings) -> dict:
    return {
        "store": {"id": settings.store_id, "name": settings.store_name, "location": "Brigade Road, Bangalore"},
        "transactions": retail_mix(settings),
        "layout": layout_manifest(settings),
        "evaluation": evaluation_manifest(),
    }
