from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from app.core.models import EventType, MetricSummary, StoreEvent
from app.core.settings import Settings
from app.services.transactions import TransactionStats


def _rounded(value: float) -> float:
    return round(value, 3)


def compute_metrics(events: list[StoreEvent], tx: TransactionStats, settings: Settings) -> MetricSummary:
    entries = [e for e in events if e.event_type == EventType.ENTRY]
    exits = [e for e in events if e.event_type == EventType.EXIT]
    checkouts = [e for e in events if e.event_type == EventType.CHECKOUT]
    anomalies = [e for e in events if e.event_type == EventType.ANOMALY]
    tracks = defaultdict(dict)
    for event in events:
        if event.event_type in (EventType.ENTRY, EventType.EXIT):
            tracks[event.track_id][event.event_type.value] = event.ts

    dwell_minutes: list[float] = []
    for track in tracks.values():
        if "entry" in track and "exit" in track and track["exit"] >= track["entry"]:
            dwell_minutes.append((track["exit"] - track["entry"]).total_seconds() / 60)

    visitors = len({event.track_id for event in entries})
    active = max(visitors - len(exits), 0)
    checkout_count = len({event.track_id for event in checkouts})
    conversion = checkout_count / visitors if visitors else 0
    return MetricSummary(
        store_id=settings.store_id,
        visitors=visitors,
        exits=len({event.track_id for event in exits}),
        active_sessions=active,
        billed_orders=tx.order_count,
        conversion_rate=_rounded(conversion),
        revenue=tx.revenue,
        avg_dwell_minutes=_rounded(sum(dwell_minutes) / len(dwell_minutes)) if dwell_minutes else 0,
        anomalies=len(anomalies),
        generated_from={
            "events": len(events),
            "raw_event_visitors": visitors,
            "checkout_tracks": checkout_count,
            "pos_orders": tx.order_count,
            "transaction_rows_present": tx.order_count > 0,
            "assumption": "Visitors come from CCTV entry tracks and conversion is the detected checkout-to-visitor ratio from seeded store events.",
        },
    )


def compute_funnel(events: list[StoreEvent], tx: TransactionStats) -> dict:
    entry_tracks = {e.track_id for e in events if e.event_type == EventType.ENTRY}
    beauty_tracks = {e.track_id for e in events if e.event_type == EventType.ZONE_ENTER and e.zone_id == "beauty_wall"}
    checkout_tracks = {e.track_id for e in events if e.event_type == EventType.CHECKOUT}
    visitors = len(entry_tracks)
    zone_visits = len(beauty_tracks)
    checkout_visits = min(len(checkout_tracks), zone_visits) if zone_visits else min(len(checkout_tracks), visitors)
    return {
        "stages": [
            {"name": "entered_store", "count": visitors, "rate_from_previous": 1.0 if visitors else 0},
            {
                "name": "visited_beauty_wall",
                "count": zone_visits,
                "rate_from_previous": _rounded(zone_visits / visitors) if visitors else 0,
            },
            {
                "name": "checkout_or_billed",
                "count": checkout_visits,
                "rate_from_previous": _rounded(checkout_visits / zone_visits) if zone_visits else 0,
            },
        ],
        "evidence": {
            "detected_checkout_tracks": len(checkout_tracks),
            "pos_orders": tx.order_count,
            "display_rule": "Funnel display is driven by seeded CCTV checkout tracks; POS orders remain available as revenue evidence.",
        },
    }


def detect_business_anomalies(events: list[StoreEvent], tx: TransactionStats) -> list[dict]:
    anomalies = []
    for event in events:
        if event.event_type == EventType.ANOMALY:
            anomalies.append(
                {
                    "type": event.attributes.get("reason", "event_stream_anomaly"),
                    "severity": "low",
                    "timestamp": event.ts.isoformat(),
                    "message": "An anomaly marker was emitted in the event stream.",
                }
            )
    entry_count = len({e.track_id for e in events if e.event_type == EventType.ENTRY})
    if entry_count and tx.order_count / entry_count > 0.95:
        anomalies.append(
            {
                "type": "conversion_too_high",
                "severity": "medium",
                "message": "POS orders are unusually close to visitor count; check duplicate track merges or staff filtering.",
            }
        )
    if events:
        by_hour = defaultdict(int)
        for event in events:
            if event.event_type == EventType.ENTRY:
                by_hour[event.ts.hour] += 1
        for hour, count in sorted(by_hour.items()):
            order_count = tx.hourly_orders.get(hour, 0)
            if count >= 5 and order_count == 0:
                anomalies.append(
                    {
                        "type": "traffic_without_billing",
                        "severity": "high",
                        "hour": hour,
                        "message": "Entry activity has no matching POS billing in the same hour.",
                    }
                )
    return anomalies
