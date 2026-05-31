# Design

## What I Built

The system is a single FastAPI service that owns ingestion, event storage, analytics APIs, and a small live dashboard. I chose one deployable service because the reviewer flow is time-boxed and the mandatory gate rewards a submission that runs cleanly with `docker compose up`.

The service has four main parts:

- `video_pipeline.py`: scans CCTV clips with a lightweight motion-line counter and emits entry/exit events.
- `event_store.py`: appends structured events to a JSONL log.
- `analytics.py`: converts events and POS rows into metrics, funnel stages, and anomaly flags.
- `dashboard/`: static dashboard that calls the APIs every time the user refreshes.

## Data Flow

```text
CCTV clip or POS seed
        |
        v
Detection / event generation
        |
        v
JSONL event log
        |
        +---- /events
        +---- /metrics
        +---- /funnel
        +---- /anomalies
        |
        v
Dashboard
```

## Event Schema

Each event has:

- `event_id`
- `event_type`
- `ts`
- `store_id`
- `camera_id`
- `track_id`
- `zone_id`
- `confidence`
- `attributes`

This is intentionally event-stream friendly. The JSONL store can be replaced by Kafka or Redpanda without changing the analytics layer much, because the rest of the service reads typed `StoreEvent` objects.

## Detection Pipeline

The video path currently uses OpenCV background subtraction and a configurable virtual gate line. It is not meant to compete with a fine-tuned person detector, but it does perform actual frame scanning and emits events from motion crossing the line. The helper script defaults to bounded processing so a reviewer can process a sample clip quickly instead of waiting for all cameras to finish.

For a production version I would replace the detector with:

- YOLO/RT-DETR person detection
- ByteTrack/DeepSORT tracking
- per-camera homography or calibrated ROIs
- a staff filter using uniform color, long dwell near billing, and known staff schedule

The current implementation keeps the detector simple so the rest of the system can still be reviewed end-to-end.

## Business Logic

Visitor count is based on unique entry tracks. POS order count and revenue come from the transaction CSV. Conversion is:

```text
unique billed orders / unique visitor entries
```

The funnel keeps detected behavior and POS truth together:

- entered store
- visited beauty wall
- checkout or billed

This makes the metric explainable even when camera coverage is imperfect.

## Production Notes

The project includes:

- Docker Compose startup
- health endpoint
- deterministic seed generation
- bounded CCTV clip processing through `scripts/process_cctv.py`
- tests for analytics and API shape
- JSONL event persistence
- dashboard backed by live endpoints

The current observability is basic but useful: API responses include counts and source notes, and events are inspectable directly through `/events`.
