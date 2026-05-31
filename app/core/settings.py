from functools import lru_cache
from pathlib import Path
import os


class Settings:
    store_id: str = os.getenv("STORE_ID", "ST1008")
    store_name: str = os.getenv("STORE_NAME", "Brigade_Bangalore")
    event_log_path: Path = Path(os.getenv("EVENT_LOG_PATH", "data/events/events.jsonl"))
    transaction_csv_path: Path = Path(os.getenv("TRANSACTION_CSV_PATH", "data/transactions.csv"))
    cctv_zip_path: Path = Path(
        os.getenv(
            "CCTV_ZIP_PATH",
            r"E:\CCTV Footage-20260529T160731Z-3-00144614ea.zip",
        )
    )
    timezone: str = os.getenv("STORE_TIMEZONE", "Asia/Kolkata")


@lru_cache
def get_settings() -> Settings:
    return Settings()
