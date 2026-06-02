import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET_ROOT = ROOT / "dashboard" / "assets" / "stores"


def main() -> None:
    TARGET_ROOT.mkdir(parents=True, exist_ok=True)
    archives = sorted(ROOT.glob("data/Store *.zip"))
    if not archives:
        raise RuntimeError("No store archives found in data/")

    for archive in archives:
        target_dir = TARGET_ROOT / archive.stem.lower().replace(" ", "_")
        target_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as z:
            pngs = [name for name in z.namelist() if name.lower().endswith(".png")]
            if not pngs:
                continue
            target = target_dir / "layout.png"
            target.write_bytes(z.read(pngs[0]))
            print(target)


if __name__ == "__main__":
    main()
