import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "store_layout.xlsx"
TARGET = ROOT / "dashboard" / "assets" / "store_layout.png"


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE) as z:
        media = [name for name in z.namelist() if name.startswith("xl/media/")]
        if not media:
            raise RuntimeError("No embedded layout media found in store_layout.xlsx")
        TARGET.write_bytes(z.read(media[0]))
        print(TARGET)


if __name__ == "__main__":
    main()
