# Store Intelligence System

This is my hackathon submission for the Brigade Road store intelligence problem.
The project turns store signals into a small set of reviewable APIs:

- visitor entry/exit events
- zone and checkout events
- conversion and dwell metrics
- basic anomaly flags
- a live browser dashboard

I kept the build intentionally compact. The service starts with deterministic events derived from the provided POS CSV and also exposes a real video ingestion path for extracted clips. On this machine the project lives at `D:\purplle hackathon`, and the original CCTV zip is at `E:\CCTV Footage-20260529T160731Z-3-00144614ea.zip`.

## Run

```bash
docker compose up --build
```

Open:

- Dashboard: http://localhost:8000
- Metrics: http://localhost:8000/metrics
- Funnel: http://localhost:8000/funnel
- Events: http://localhost:8000/events

## Optional Video Ingestion

The clips are expected under `data/cctv/CCTV Footage/` after extraction. To process a bounded sample from CAM 4 locally:

```bash
python scripts/process_cctv.py --video "data/cctv/CCTV Footage/CAM 4.mp4" --camera-id CAM_4 --max-frames 5000
```

Or call the running API:

```bash
curl -X POST "http://localhost:8000/ingest/video?path=data/cctv/CCTV%20Footage/CAM%204.mp4&camera_id=CAM_4&max_frames=5000"
```

When running with Docker, use container paths such as `/app/data/cctv/CCTV Footage/CAM 4.mp4`.

## Local Dev

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/seed_events.py --if-empty
uvicorn app.main:app --reload
```

Run tests:

```bash
pytest
```
