from datetime import datetime, timedelta

from app.core.models import EventType, StoreEvent
from app.core.settings import Settings
from app.services.analytics import compute_funnel, compute_metrics
from app.services.seeding import load_sample_events
from app.services.transactions import TransactionStats


def event(kind, track, minutes=0, zone=None):
    return StoreEvent(
        event_type=kind,
        ts=datetime(2026, 4, 10, 10, 0, 0) + timedelta(minutes=minutes),
        store_id="ST1008",
        track_id=track,
        zone_id=zone,
    )


def test_metrics_are_session_based():
    events = [
        event(EventType.ENTRY, "a"),
        event(EventType.ZONE_ENTER, "a", 2, "beauty_wall"),
        event(EventType.EXIT, "a", 12),
        event(EventType.ENTRY, "b", 1),
    ]
    tx = TransactionStats(row_count=1, order_count=1, revenue=250.0, hourly_orders={10: 1}, brand_mix={}, store_mix={})
    metrics = compute_metrics(events, tx, Settings())
    assert metrics.visitors == 2
    assert metrics.exits == 1
    assert metrics.active_sessions == 1
    assert metrics.conversion_rate == 0.5
    assert metrics.avg_dwell_minutes == 12


def test_funnel_uses_detected_zone_and_pos_orders():
    events = [
        event(EventType.ENTRY, "a"),
        event(EventType.ZONE_ENTER, "a", 2, "beauty_wall"),
        event(EventType.CHECKOUT, "a", 8, "billing_counter"),
        event(EventType.ENTRY, "b", 1),
    ]
    tx = TransactionStats(row_count=3, order_count=3, revenue=1000.0, hourly_orders={}, brand_mix={}, store_mix={})
    funnel = compute_funnel(events, tx)
    assert funnel["stages"][0]["count"] == 2
    assert funnel["stages"][1]["count"] == 1
    assert funnel["stages"][2]["count"] == 1
    assert funnel["evidence"]["pos_orders"] == 3


def test_sample_events_file_normalizes_to_store_events():
    events = load_sample_events(Settings(), limit=5)
    assert len(events) == 5
    assert events[0].event_type == EventType.ENTRY
    assert events[0].track_id == "ID_60001"
    assert events[4].event_type == EventType.ZONE_ENTER
    assert events[4].zone_id == "beauty_wall"
