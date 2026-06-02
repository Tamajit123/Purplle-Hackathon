from __future__ import annotations

import json
import zipfile
from pathlib import Path

from app.core.settings import Settings
from app.services.transactions import load_transaction_stats


MANIFEST_PATH = Path("config/store_manifest.json")


def discover_store_assets(root: Path = Path("dashboard/assets/stores")) -> list[Path]:
    return sorted([path for path in root.glob("store_*") if path.is_dir()])


def discover_store_archives(root: Path) -> list[Path]:
    return sorted([path for path in root.glob("Store *.zip") if path.is_file()])


def _store_name(asset_dir: Path) -> str:
    return asset_dir.name.replace("_", " ").title()


def _store_slug(asset_dir: Path) -> str:
    return asset_dir.name.lower().replace(" ", "_")


def camera_inventory(archive: Path | None) -> list[dict]:
    if not archive or not archive.exists():
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


def load_store_manifest(path: Path = MANIFEST_PATH) -> list[dict]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    stores = []
    for store in payload.get("stores", []):
        asset = store.get("layout_asset")
        asset_path = Path(str(asset).lstrip("/")) if asset else None
        cameras = store.get("cameras", [])
        stores.append(
            {
                "id": store.get("id"),
                "store": store.get("store"),
                "focus": store.get("focus"),
                "archive": None,
                "asset": asset if asset_path and asset_path.exists() else None,
                "camera_count": len(cameras),
                "layout_count": 1 if asset_path and asset_path.exists() else 0,
                "zones": store.get("zones", []),
                "cameras": cameras,
            }
        )
    return stores


def layout_manifest(settings: Settings) -> dict:
    manifest_stores = load_store_manifest()
    asset_dirs = discover_store_assets()
    archives = discover_store_archives(settings.store_data_root)
    archive_by_store = {archive.stem.lower().replace(" ", "_"): archive for archive in archives}
    stores = []

    for store in manifest_stores:
        archive = archive_by_store.get(store["id"])
        archive_cameras = camera_inventory(archive)
        cameras = archive_cameras or store["cameras"]
        stores.append(
            {
                **store,
                "archive": str(archive) if archive else None,
                "camera_count": len(cameras),
                "cameras": cameras,
            }
        )

    known_ids = {store.get("id") for store in stores}
    for asset_dir in asset_dirs:
        if asset_dir.name in known_ids:
            continue
        asset_path = asset_dir / "layout.png"
        archive = archive_by_store.get(asset_dir.name)
        camera_list = camera_inventory(archive)
        stores.append(
            {
                "id": _store_slug(asset_dir),
                "store": _store_name(asset_dir),
                "focus": "Discovered local store asset",
                "archive": str(archive) if archive else None,
                "asset": f"/dashboard/assets/stores/{asset_dir.name}/layout.png" if asset_path.exists() else None,
                "camera_count": len(camera_list),
                "layout_count": 1 if asset_path.exists() else 0,
                "zones": ["entry_gate", "beauty_wall", "billing_counter"],
                "cameras": camera_list,
            }
        )
    active = stores[0] if stores else None
    return {
        "available": bool(stores),
        "source": str(active["archive"]) if active and active["archive"] else None,
        "asset": active["asset"] if active else None,
        "stores": stores,
        "store_count": len(stores),
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
