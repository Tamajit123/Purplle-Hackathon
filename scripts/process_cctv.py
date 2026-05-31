import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.settings import get_settings
from app.services.event_store import EventStore
from app.services.video_pipeline import MotionLineCounter


def main() -> None:
    parser = argparse.ArgumentParser(description="Process one extracted CCTV clip into the JSONL event stream.")
    parser.add_argument("--video", default="data/cctv/CCTV Footage/CAM 4.mp4")
    parser.add_argument("--camera-id", default="CAM_4")
    parser.add_argument("--max-frames", type=int, default=5000)
    parser.add_argument("--sample-every", type=int, default=8)
    args = parser.parse_args()

    settings = get_settings()
    video = Path(args.video)
    result = MotionLineCounter(settings).process(
        video,
        camera_id=args.camera_id,
        max_frames=args.max_frames,
        sample_every=args.sample_every,
    )
    written = EventStore(settings.event_log_path).append_many(result.events)
    print(
        {
            "video": str(video),
            "camera_id": result.camera_id,
            "frames_scanned": result.frames_scanned,
            "events_written": written,
            "warning": result.warning,
        }
    )


if __name__ == "__main__":
    main()
