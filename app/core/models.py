from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    ENTRY = "entry"
    EXIT = "exit"
    ZONE_ENTER = "zone_enter"
    ZONE_EXIT = "zone_exit"
    CHECKOUT = "checkout"
    ANOMALY = "anomaly"


class StoreEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    ts: datetime
    store_id: str
    camera_id: str = "derived"
    track_id: str
    zone_id: str | None = None
    confidence: float = Field(ge=0, le=1, default=0.75)
    attributes: dict[str, Any] = Field(default_factory=dict)


class MetricSummary(BaseModel):
    store_id: str
    visitors: int
    exits: int
    active_sessions: int
    billed_orders: int
    conversion_rate: float
    revenue: float
    avg_dwell_minutes: float
    anomalies: int
    generated_from: dict[str, Any]
