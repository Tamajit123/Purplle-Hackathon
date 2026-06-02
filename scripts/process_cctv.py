import argparse
import zipfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.settings import get_settings
from app.services.event_store import EventStore
from app.services.video_pipeline import MotionLineCounter


def extract_store_archive(archive: Path, output_root: Path) -> tuple[Path, str]:
    output_dir = output_root / archive.stem.replace(" ", "_")
    output_dir.mkdir(parents=True, exist_ok=True)
    if not any(output_dir.rglob("*.mp4")):
        with zipfile.ZipFile(archive) as z:
            z.extractall(output_dir)
    mp4s = sorted(output_dir.rglob("*.mp4"))
    if not mp4s:
        raise RuntimeError(f"No mp4 files found in {archive}")
    return output_dir, str(mp4s[0])


def main() -> None:
    parser = argparse.ArgumentParser(description="Process one CCTV clip from a store archive into the JSONL event stream.")
    parser.add_argument("--store-archive", default="data/Store 1.zip")
    parser.add_argument("--video", default="")
    parser.add_argument("--camera-id", default="CAM_1")
    parser.add_argument("--max-frames", type=int, default=5000)
    parser.add_argument("--sample-every", type=int, default=8)
    args = parser.parse_args()

    settings = get_settings()
    archive = Path(args.store_archive)
    extracted_root, default_video = extract_store_archive(archive, Path("data/stores"))
    video = Path(args.video) if args.video else Path(default_video)
    if not video.is_absolute():
        relative_candidate = extracted_root / video
        if relative_candidate.exists():
            video = relative_candidate
    result = MotionLineCounter(settings).process(
        video,
        camera_id=args.camera_id,
        max_frames=args.max_frames,
        sample_every=args.sample_every,
    )
    written = EventStore(settings.event_log_path).append_many(result.events)
    print(
        {
            "store_archive": str(archive),
            "extracted_root": str(extracted_root),
            "video": str(video),
            "camera_id": result.camera_id,
            "frames_scanned": result.frames_scanned,
            "events_written": written,
            "warning": result.warning,
        }
    )


if __name__ == "__main__":
    main()
