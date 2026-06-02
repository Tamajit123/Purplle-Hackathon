import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.settings import get_settings
from app.services.event_store import EventStore
from app.services.seeding import generate_seed_events


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--if-empty", action="store_true", help="Do not append when events already exist")
    parser.add_argument("--max-orders", type=int, default=999999)
    args = parser.parse_args()

    settings = get_settings()
    store = EventStore(settings.event_log_path)
    if args.if_empty and store.count() > 0:
        print(f"event log already has {store.count()} events")
        return
    written = store.append_many(generate_seed_events(settings, max_orders=args.max_orders))
    print(f"wrote {written} events to {settings.event_log_path}")


if __name__ == "__main__":
    main()
