"""
Project-wide constants (single source of truth).

Location: src/core/constants.py
Import pattern (from any file under src/): from core.constants import ...
"""

from __future__ import annotations

from pathlib import Path

# ERA5 paths + merge config
RAW_ERA5_DIR: Path = Path("data/raw/era5")
PROCESSED_ERA5_DIR: Path = Path("data/processed/ERA5")

ERA5_JSON_FILES: list[str] = [
    "era5_phl_annual_1950_2023_cdd_r50mm_r95ptot.json",
    "era5_phl_so will core nnual_1950_2023_cwd_rx1day_rx5day.json",
    "era5_phl_annual_1950_2023_pr_prpercent_r20mm.json",
]

ERA5_OUTPUT_CSV_PATH: Path = PROCESSED_ERA5_DIR / "merged_era5_data.csv"

ERA5_COLUMN_ORDER: list[str] = [
    "year",
    "cdd",
    "r50mm",
    "r95ptot",
    "cwd",
    "rx1day",
    "rx5day",
    "pr",
    "prpercent",
    "r20mm",
]


# IBTrACS paths + outputs
RAW_IBTRACS_DIR: Path = Path("data/raw/IBTrACS")
PROCESSED_IBTRACS_V2_DIR: Path = Path("data/processed/IBTrACS/v2")

IBTRACS_RAW_CSV_GZ_PATH: Path = RAW_IBTRACS_DIR / "ibtracs_wp_full.csv.gz"
IBTRACS_OUT_TRACKS_PATH: Path = PROCESSED_IBTRACS_V2_DIR / "ibtracs_par_1950_2023_tracks_2.csv"
IBTRACS_OUT_STORMS_PATH: Path = PROCESSED_IBTRACS_V2_DIR / "ibtracs_par_1950_2023_storms_2.csv"

# Shared analysis scope
START_YEAR: int = 1950
END_YEAR: int = 2023


# IBTrACS cleaning choices
WIND_COLUMN: str = "USA_WIND"
KEEP_NATURE: set[str] = {"TD", "TS", "TY"}


# common IBTrACS columns likely referenced
COL_SEASON: str = "SEASON"
COL_NATURE: str = "NATURE"
COL_LAT: str = "LAT"
COL_LON: str = "LON"
COL_STORM_ID: str = "SID"
COL_TIME: str = "ISO_TIME"
