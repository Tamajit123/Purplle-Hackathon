from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.settings import get_settings
from app.services.analytics import compute_funnel, compute_metrics, detect_business_anomalies
from app.services.event_store import EventStore
from app.services.seeding import generate_seed_events
from app.services.resources import resource_summary
from app.services.transactions import load_transaction_stats
from app.services.video_pipeline import MotionLineCounter

settings = get_settings()
store = EventStore(settings.event_log_path)

app = FastAPI(title="Store Intelligence System", version="0.1.0")
app.mount("/dashboard", StaticFiles(directory="dashboard"), name="dashboard")


@app.on_event("startup")
def ensure_initial_events() -> None:
    if store.count() == 0:
        store.append_many(generate_seed_events(settings))


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse("dashboard/index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "events": store.count(), "store_id": settings.store_id}


@app.get("/metrics")
def metrics() -> dict:
    return compute_metrics(store.all(), load_transaction_stats(settings.transaction_csv_path), settings).model_dump()


@app.get("/funnel")
def funnel() -> dict:
    return compute_funnel(store.all(), load_transaction_stats(settings.transaction_csv_path))


@app.get("/events")
def events(limit: int = Query(100, ge=1, le=1000)) -> dict:
    return {"events": [event.model_dump() for event in store.all(limit=limit)]}


@app.get("/anomalies")
def anomalies() -> dict:
    return {"anomalies": detect_business_anomalies(store.all(), load_transaction_stats(settings.transaction_csv_path))}


@app.get("/insights")
def insights() -> dict:
    return resource_summary(settings)


@app.post("/ingest/seed")
def ingest_seed(max_orders: int = Query(90, ge=1, le=500)) -> dict:
    generated = generate_seed_events(settings, max_orders=max_orders)
    return {"written": store.append_many(generated)}


@app.post("/ingest/video")
def ingest_video(
    path: str,
    camera_id: str = "cam_manual",
    max_frames: int | None = Query(None, ge=100, le=200000),
    sample_every: int = Query(8, ge=1, le=60),
) -> dict:
    result = MotionLineCounter(settings).process(
        Path(path),
        camera_id=camera_id,
        max_frames=max_frames,
        sample_every=sample_every,
    )
    written = store.append_many(result.events)
    return {
        "camera_id": result.camera_id,
        "video_path": result.video_path,
        "frames_scanned": result.frames_scanned,
        "events_written": written,
        "warning": result.warning,
    }
