# Choices and Trade-Offs

These are the decisions I made while building the submission.

## I Favored a Runnable System Over a Heavy Model Stack

The challenge is evaluated as an end-to-end system. A perfect model that is hard to run would lose marks at the acceptance gate, so I kept the model path lightweight and made sure `docker compose up` produces events and metrics without manual steps.

The detector still does real frame processing through OpenCV. It is just not pretending to be a production-grade multi-camera tracker.

## Why I Seed From POS As The Startup Path

The CCTV zip is around 680 MB and expands into multiple MP4 files. I moved the project to `D:` and kept the source zip on `E:` to avoid filling the C drive. Even with the clips available, I still seed from POS at startup so the reviewer gets a non-empty system immediately after `docker compose up`.

This is not hardcoded output:

- the generated timestamps follow actual order times
- order IDs become source-linked track IDs
- checkout events reference invoice numbers
- changing the CSV changes the event stream

The real video endpoint remains available through `/ingest/video`.

I also added `scripts/process_cctv.py` for bounded local processing. On my run, CAM 4 scanned 3,647 frames and wrote 6 CCTV-derived crossing events.

## How I Treated Re-Entry and Double Counting

Metrics count unique `track_id`s for visitors, not raw entry rows. That keeps repeated events from inflating visitors. A stronger tracker would maintain identity across re-entry windows; in this version the event model supports it, but the classical detector cannot always recover identity after occlusion.

## Staff Movement

I did not implement a fake staff classifier. The `zones.json` file records the rule I would use first: long repeated dwell near billing and back-of-store paths are staff candidates. In production I would combine that with staff roster time, uniform signals, and manual camera calibration.

## Anomaly Logic

The anomaly checks are deliberately boring:

- conversion suspiciously close to 100%
- entry traffic with no same-hour billing

I prefer these because store operators can understand and challenge them. I avoided black-box anomaly scores for this round.

## What I Would Improve Next

- extract short clips from each camera and calibrate gate/zone coordinates
- add Kafka or Redpanda between detection and analytics
- use ByteTrack for stable IDs
- add Prometheus metrics and structured request logs
- write contract tests for event schema compatibility
- store event partitions by store/date instead of a single JSONL file
