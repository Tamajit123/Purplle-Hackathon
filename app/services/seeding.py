from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

from app.core.models import EventType, StoreEvent
from app.core.settings import Settings


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
    """Create deterministic review data from POS rows when videos are not staged.

    This is deliberately tied to the supplied CSV, so changing the input changes the
    visitor and checkout pattern. It keeps docker-compose useful on machines where
    the 680 MB CCTV zip is still sitting in Downloads.
    """
    sample_events = load_sample_events(settings, limit=max_orders)
    if sample_events:
        return sample_events

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
