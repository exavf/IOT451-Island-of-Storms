from pathlib import Path

PROJECT_ROOT = next(
    p for p in Path(__file__).resolve().parents
    if p.name == "IOT451U-25-A2-ec25735"
)

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw" / "era5"

json_files = list(RAW_DATA_DIR.glob("*.json"))
print("Found JSON files:", [p.name for p in json_files])

if not json_files:
    raise FileNotFoundError(f"No .json files found in {RAW_DATA_DIR}")
