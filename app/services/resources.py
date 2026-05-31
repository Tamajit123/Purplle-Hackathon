from __future__ import annotations

import zipfile
from pathlib import Path

from app.core.settings import Settings
from app.services.transactions import load_transaction_stats


def camera_inventory(root: Path = Path("data/cctv/CCTV Footage")) -> list[dict]:
    if not root.exists():
        return []
    cameras = []
    for file in sorted(root.glob("*.mp4")):
        cameras.append(
            {
                "camera_id": file.stem.replace(" ", "_").upper(),
                "name": file.stem,
                "path": str(file),
                "size_mb": round(file.stat().st_size / (1024 * 1024), 1),
                "status": "ready",
            }
        )
    return cameras


def layout_manifest(path: Path = Path("data/store_layout.xlsx")) -> dict:
    if not path.exists():
        return {"available": False, "asset": None, "embedded_media": 0}
    with zipfile.ZipFile(path) as z:
        media = [name for name in z.namelist() if name.startswith("xl/media/")]
    return {
        "available": True,
        "source": str(path),
        "asset": "/dashboard/assets/store_layout.png" if Path("dashboard/assets/store_layout.png").exists() else None,
        "embedded_media": len(media),
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
        "department_mix": stats.department_mix,
        "brand_mix": stats.brand_mix,
        "salesperson_mix": stats.salesperson_mix,
    }


def resource_summary(settings: Settings) -> dict:
    return {
        "store": {"id": settings.store_id, "name": settings.store_name, "location": "Brigade Road, Bangalore"},
        "transactions": retail_mix(settings),
        "layout": layout_manifest(),
        "cameras": camera_inventory(),
        "evaluation": evaluation_manifest(),
    }
