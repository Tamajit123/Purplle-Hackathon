from __future__ import annotations

import csv
import json
import shutil
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from app.core.models import EventType, StoreEvent
from app.core.settings import Settings
from app.services.transactions import load_transaction_stats
from app.services.video_pipeline import MotionLineCounter


EVENT_TYPE_MAP = {
    "entry": EventType.ENTRY,
    "exit": EventType.EXIT,
    "zone_entered": EventType.ZONE_ENTER,
    "zone_enter": EventType.ZONE_ENTER,
    "zone_exited": EventType.ZONE_EXIT,
    "zone_exit": EventType.ZONE_EXIT,
    "checkout": EventType.CHECKOUT,
    "billing": EventType.CHECKOUT,
    "anomaly": EventType.ANOMALY,
}


def _parse_ts(row: dict) -> datetime:
    value = row.get("ts") or row.get("event_timestamp") or row.get("event_time")
    if not value:
        return datetime.now().replace(microsecond=0)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)


def _normalise_zone(row: dict) -> str | None:
    zone = row.get("zone_id") or row.get("zone_name") or row.get("zone_type")
    if not zone:
        return None
    zone_value = str(zone).strip().replace(" ", "_").lower()
    if "shelf" in zone_value or "zone" in zone_value or zone_value.endswith("_z01"):
        return "beauty_wall"
    if "billing" in zone_value or "checkout" in zone_value:
        return "billing_counter"
    return zone_value


def _store_archives(settings: Settings) -> list[Path]:
    return sorted(path for path in settings.store_data_root.glob("Store *.zip") if path.is_file())


def _extract_primary_video(archive: Path, output_root: Path) -> Path | None:
    target_root = output_root / archive.stem.replace(" ", "_")
    target_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        mp4s = sorted(name for name in z.namelist() if name.lower().endswith(".mp4"))
        if not mp4s:
            return None
        member = mp4s[0]
        target = target_root / Path(member).name
        if not target.exists():
            with z.open(member) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
        return target


def _load_archive_events(settings: Settings) -> list[StoreEvent]:
    events: list[StoreEvent] = []
    for archive in _store_archives(settings):
        video = _extract_primary_video(archive, settings.store_data_root / "stores")
        if not video:
            continue
        result = MotionLineCounter(settings).process(
            video,
            camera_id=video.stem.replace(" ", "_").upper(),
            max_frames=2500,
            sample_every=10,
        )
        events.extend(result.events)
    return events


def _iter_unique_orders(path: Path):
    seen: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            order_id = row.get("order_id") or row.get("invoice_number")
            if not order_id or order_id in seen:
                continue
            seen.add(order_id)
            yield row


def _build_checkout_events(settings: Settings, visitor_tracks: list[str], checkout_target: int) -> list[StoreEvent]:
    stats = load_transaction_stats(settings.transaction_csv_path)
    if not settings.transaction_csv_path.exists() or not visitor_tracks or checkout_target <= 0:
        return []

    events: list[StoreEvent] = []
    selected_tracks = visitor_tracks[: min(len(visitor_tracks), checkout_target)]
    rows = list(_iter_unique_orders(settings.transaction_csv_path))
    rows = rows[: len(selected_tracks)]
    for idx, (row, track_id) in enumerate(zip(rows, selected_tracks, strict=False)):
        ts = datetime.strptime(f"{row.get('order_date')} {row.get('order_time')}", "%d-%m-%Y %H:%M:%S")
        events.append(
            StoreEvent(
                event_type=EventType.CHECKOUT,
                ts=ts - timedelta(minutes=1 + (idx % 3)),
                store_id=str(row.get("store_id") or settings.store_id),
                camera_id="seed_pos",
                track_id=track_id,
                zone_id="billing_counter",
                confidence=0.88,
                attributes={
                    "invoice_number": row.get("order_id") or row.get("invoice_number"),
                    "brand_name": row.get("brand_name"),
                    "total_amount": row.get("total_amount"),
                    "source": "POS_transactions.csv",
                    "orders_available": stats.order_count,
                },
            )
        )
    return events


def load_sample_events(settings: Settings, limit: int | None = None) -> list[StoreEvent]:
    path = settings.sample_events_path
    if not path.exists():
        return []

    events: list[StoreEvent] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            mapped_type = EVENT_TYPE_MAP.get(str(row.get("event_type", "")).lower())
            if not mapped_type:
                continue

            track_id = row.get("track_id") or row.get("id_token") or row.get("person_id") or f"sample_{len(events) + 1}"
            confidence = row.get("confidence")
            if confidence is None:
                confidence = 0.69 if row.get("is_face_hidden") else 0.84

            events.append(
                StoreEvent(
                    event_type=mapped_type,
                    ts=_parse_ts(row),
                    store_id=str(row.get("store_id") or row.get("store_code") or settings.store_id),
                    camera_id=str(row.get("camera_id") or "sample_events"),
                    track_id=str(track_id),
                    zone_id=_normalise_zone(row),
                    confidence=float(confidence),
                    attributes={
                        "source": path.name,
                        "age_bucket": row.get("age_bucket"),
                        "gender": row.get("gender") or row.get("gender_pred"),
                        "group_id": row.get("group_id"),
                        "role": row.get("zone_type"),
                    },
                )
            )
            if limit is not None and len(events) >= limit:
                break
    return events


def generate_seed_events(settings: Settings, max_orders: int | None = None) -> list[StoreEvent]:
    """Create deterministic review data from the supplied store footage and POS rows."""

    video_events = _load_archive_events(settings)
    if video_events:
        visitor_tracks = sorted({event.track_id for event in video_events if event.event_type == EventType.ENTRY})
        checkout_target = max(2, len(visitor_tracks) // 3)
        checkout_events = _build_checkout_events(settings, visitor_tracks, checkout_target)
        events = sorted([*video_events, *checkout_events], key=lambda event: event.ts)
        if not any(event.event_type == EventType.ANOMALY for event in events):
            events.append(
                StoreEvent(
                    event_type=EventType.ANOMALY,
                    ts=events[-1].ts + timedelta(minutes=1),
                    store_id=settings.store_id,
                    camera_id="seed_summary",
                    track_id="system",
                    confidence=0.71,
                    attributes={
                        "reason": "pos_checkout_sample_below_transaction_volume",
                        "sampled_checkouts": len(checkout_events),
                        "detected_visitors": len(visitor_tracks),
                    },
                )
            )
        return events if max_orders is None else events[:max_orders]

    sample_events = load_sample_events(settings, limit=max_orders)
    if sample_events:
        visitor_tracks = sorted({event.track_id for event in sample_events if event.event_type == EventType.ENTRY})
        checkout_events = _build_checkout_events(settings, visitor_tracks, max(2, len(visitor_tracks) // 3))
        events = sorted([*sample_events, *checkout_events], key=lambda event: event.ts)
        if not any(event.event_type == EventType.ANOMALY for event in events) and events:
            events.append(
                StoreEvent(
                    event_type=EventType.ANOMALY,
                    ts=events[-1].ts + timedelta(minutes=1),
                    store_id=settings.store_id,
                    camera_id="seed_summary",
                    track_id="system",
                    confidence=0.67,
                    attributes={"reason": "sample_event_stream_requires_checkout_balance"},
                )
            )
        return events if max_orders is None else events[:max_orders]

    path = settings.transaction_csv_path
    if not path.exists():
        now = datetime.now().replace(microsecond=0)
        return [
            StoreEvent(event_type=EventType.ENTRY, ts=now, store_id=settings.store_id, track_id="walkin_0001"),
            StoreEvent(
                event_type=EventType.EXIT,
                ts=now + timedelta(minutes=8),
                store_id=settings.store_id,
                track_id="walkin_0001",
            ),
        ]

    events: list[StoreEvent] = []
    seen_orders: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            order_id = row.get("order_id") or row.get("invoice_number")
            if not order_id or order_id in seen_orders:
                continue
            seen_orders.add(order_id)
            if max_orders is not None and len(seen_orders) > max_orders:
                break

            ts = datetime.strptime(f"{row.get('order_date')} {row.get('order_time')}", "%d-%m-%Y %H:%M:%S")
            track_id = f"cust_{order_id}"
            entry_ts = ts - timedelta(minutes=8 + (len(seen_orders) % 9))
            zone = (row.get("dep_name") or "beauty_wall").replace(" ", "_").lower()
            events.extend(
                [
                    StoreEvent(
                        event_type=EventType.ENTRY,
                        ts=entry_ts,
                        store_id=settings.store_id,
                        camera_id="seed_csv",
                        track_id=track_id,
                        confidence=0.82,
                        attributes={"source_order_id": order_id},
                    ),
                    StoreEvent(
                        event_type=EventType.ZONE_ENTER,
                        ts=entry_ts + timedelta(minutes=2),
                        store_id=settings.store_id,
                        camera_id="seed_csv",
                        track_id=track_id,
                        zone_id="beauty_wall" if zone in {"skin", "makeup"} else zone,
                        confidence=0.72,
                    ),
                    StoreEvent(
                        event_type=EventType.CHECKOUT,
                        ts=ts - timedelta(minutes=1),
                        store_id=settings.store_id,
                        camera_id="seed_csv",
                        track_id=track_id,
                        zone_id="billing_counter",
                        confidence=0.78,
                        attributes={"invoice_number": row.get("invoice_number")},
                    ),
                    StoreEvent(
                        event_type=EventType.EXIT,
                        ts=ts + timedelta(minutes=3 + (len(seen_orders) % 4)),
                        store_id=settings.store_id,
                        camera_id="seed_csv",
                        track_id=track_id,
                        confidence=0.8,
                    ),
                ]
            )

    if events:
        events.append(
            StoreEvent(
                event_type=EventType.ANOMALY,
                ts=events[-1].ts + timedelta(minutes=1),
                store_id=settings.store_id,
                camera_id="seed_csv",
                track_id="system",
                confidence=0.67,
                attributes={"reason": "review_seed_contains_pos_derived_tracks"},
            )
        )
    return events
