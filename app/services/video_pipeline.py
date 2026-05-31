from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from app.core.models import EventType, StoreEvent
from app.core.settings import Settings


@dataclass
class VideoRunResult:
    camera_id: str
    frames_scanned: int
    events: list[StoreEvent]
    video_path: str | None = None
    warning: str | None = None


class MotionLineCounter:
    def __init__(self, settings: Settings):
        self.settings = settings

    def process(
        self,
        video_path: Path,
        camera_id: str = "cam",
        max_frames: int | None = None,
        sample_every: int = 8,
    ) -> VideoRunResult:
        try:
            import cv2
        except Exception as exc:  # pragma: no cover - only used when cv2 missing
            return VideoRunResult(camera_id, 0, [], str(video_path), f"opencv unavailable: {exc}")

        if not video_path.exists():
            return VideoRunResult(camera_id, 0, [], str(video_path), f"video not found: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return VideoRunResult(camera_id, 0, [], str(video_path), f"could not open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        bg = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=48, detectShadows=True)
        frame_no = 0
        last_side: str | None = None
        last_emit_frame = -9999
        events: list[StoreEvent] = []
        base_ts = datetime.now().replace(microsecond=0)

        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame_no += 1
            if max_frames and frame_no > max_frames:
                break
            if frame_no % sample_every != 0:
                continue
            height, width = frame.shape[:2]
            gate_x = int(width * 0.48)
            fg = bg.apply(frame)
            fg = cv2.medianBlur(fg, 5)
            contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            candidates = [cv2.boundingRect(c) for c in contours if cv2.contourArea(c) > 900]
            if not candidates:
                continue
            x, y, w, h = max(candidates, key=lambda r: r[2] * r[3])
            cx = x + w // 2
            side = "left" if cx < gate_x else "right"
            if last_side and side != last_side and frame_no - last_emit_frame > fps * 2:
                direction = EventType.ENTRY if last_side == "left" and side == "right" else EventType.EXIT
                track_id = f"{camera_id}_{frame_no}"
                events.append(
                    StoreEvent(
                        event_type=direction,
                        ts=base_ts + timedelta(seconds=frame_no / fps),
                        store_id=self.settings.store_id,
                        camera_id=camera_id,
                        track_id=track_id,
                        confidence=0.62,
                        attributes={"gate_x": gate_x, "centroid_x": cx, "frame": frame_no},
                    )
                )
                last_emit_frame = frame_no
            last_side = side

        cap.release()
        return VideoRunResult(camera_id=camera_id, frames_scanned=frame_no, events=events, video_path=str(video_path))
