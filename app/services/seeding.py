from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path

from app.core.models import EventType, StoreEvent
from app.core.settings import Settings


def generate_seed_events(settings: Settings, max_orders: int = 90) -> list[StoreEvent]:
    """Create deterministic review data from POS rows when videos are not staged.

    This is deliberately tied to the supplied CSV, so changing the input changes the
    visitor and checkout pattern. It keeps docker-compose useful on machines where
    the 680 MB CCTV zip is still sitting in Downloads.
    """
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
            if len(seen_orders) > max_orders:
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
