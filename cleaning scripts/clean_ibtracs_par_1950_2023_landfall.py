import json
import pandas as pd
import numpy as np
from pathlib import Path
from matplotlib.path import Path as MplPath

RAW_CSV_PATH = Path("data/raw/IBTrACS/ibtracs_wp_full.csv.gz")
PH_GEOJSON_PATH = Path("data/raw/boundaries/philippines.geojson")

OUT_TRACKS_PATH = Path("data/processed/IBTrACS/v4_landfall/ibtracs_ph_landfall_1950_2023_tracks.csv")
OUT_STORMS_PATH = Path("data/processed/IBTrACS/v4_landfall/ibtracs_ph_landfall_1950_2023_storms.csv")

START_YEAR = 1950
END_YEAR = 2023

WIND_COLUMN = "USA_WIND"
KEEP_NATURE = {"TD", "TS", "TY"}  # optional filter set for later use

USE_COLUMNS = ["SID", "ISO_TIME", "LAT", "LON", "NATURE", WIND_COLUMN]

#load PH GeoJSON -> list[Path]
def _ensure_lon_180(lon: float) -> float:
    """
    IBTrACS sometimes stores lon in 0..360. PH GeoJSON is usually -180..180.
    convert anything > 180 into the -180..180 range.
    """
    if lon > 180:
        return lon - 360
    return lon


def load_geojson_paths(geojson_path: Path) -> list[MplPath]:
    """
    Load a GeoJSON (Polygon or MultiPolygon) and return a list of matplotlib Paths.
    Notes:
    - We only use the EXTERIOR ring for a minimal landfall test.
    - This ignores holes; usually fine for "hit land somewhere in PH" logic.
    """
    if not geojson_path.exists():
        raise FileNotFoundError(f"Could not find PH GeoJSON at: {geojson_path}")

    with geojson_path.open("r", encoding="utf-8") as f:
        gj = json.load(f)

    geom = None
    if gj.get("type") == "FeatureCollection":
        if not gj.get("features"):
            raise ValueError("GeoJSON FeatureCollection has no features.")
        geom = gj["features"][0]["geometry"]
    elif gj.get("type") == "Feature":
        geom = gj["geometry"]
    else:
        geom = gj  # assume geometry

    if not geom or "type" not in geom:
        raise ValueError("Could not parse geometry from GeoJSON.")

    paths: list[MplPath] = []

    gtype = geom["type"]
    coords = geom["coordinates"]

    def add_polygon(poly_coords):
        # poly_coords: [ exterior_ring, hole1, hole2, ... ]
        exterior = poly_coords[0]
        # exterior is list of [lon, lat]
        verts = [(float(x), float(y)) for x, y in exterior]
        paths.append(MplPath(verts))

    if gtype == "Polygon":
        add_polygon(coords)
    elif gtype == "MultiPolygon":
        for poly in coords:
            add_polygon(poly)
    else:
        raise ValueError(f"Unsupported geometry type: {gtype}. Expected Polygon or MultiPolygon.")

    if not paths:
        raise ValueError("No polygons extracted from the PH GeoJSON.")

    return paths


def points_in_any_polygon(lons: np.ndarray, lats: np.ndarray, paths: list[MplPath]) -> np.ndarray:
    """
    vectorised-ish check: a point is on PH land if it falls inside ANY polygon path.
    """
    pts = np.column_stack([lons, lats])
    hit = np.zeros(len(pts), dtype=bool)
    for p in paths:
        # contains_points returns a boolean array per path
        hit |= p.contains_points(pts)
    return hit

# basic checks

if not RAW_CSV_PATH.exists():
    raise FileNotFoundError(f"Could not find input CSV at: {RAW_CSV_PATH}")

header_columns = pd.read_csv(RAW_CSV_PATH, nrows=0).columns.tolist()
missing_columns = [col for col in USE_COLUMNS if col not in header_columns]
if missing_columns:
    raise KeyError(
        f"Missing required columns: {missing_columns}\n"
        f"Available columns include: {header_columns[:30]} ... (total {len(header_columns)})"
    )

# Load PH land polygon paths
ph_paths = load_geojson_paths(PH_GEOJSON_PATH)

# Load + coerce
df = pd.read_csv(RAW_CSV_PATH, usecols=USE_COLUMNS, low_memory=False)

df["ISO_TIME"] = pd.to_datetime(df["ISO_TIME"], errors="coerce")
df["LAT"] = pd.to_numeric(df["LAT"], errors="coerce")
df["LON"] = pd.to_numeric(df["LON"], errors="coerce")
df[WIND_COLUMN] = pd.to_numeric(df[WIND_COLUMN], errors="coerce")

df = df.dropna(subset=["SID", "ISO_TIME", "LAT", "LON", WIND_COLUMN])

df["year"] = df["ISO_TIME"].dt.year
df = df[(df["year"] >= START_YEAR) & (df["year"] <= END_YEAR)].copy()

# Make lon consistent with PH GeoJSON
df["LON_180"] = df["LON"].map(_ensure_lon_180)

# Landfall detection: point-in-PH-land polygons
df["on_ph_land"] = points_in_any_polygon(
    df["LON_180"].to_numpy(),
    df["LAT"].to_numpy(),
    ph_paths
)

# Storms that made PH landfall (at least one point on land)
landfall_storm_ids = df.loc[df["on_ph_land"], "SID"].unique()
if len(landfall_storm_ids) == 0:
    print("Warning: No storms intersect PH land after filtering. Output files will be empty.")

# Keep full track history for landfall storms
tracks_df = df[df["SID"].isin(landfall_storm_ids)].copy()

# Light dedupe + sort
tracks_df = tracks_df.drop_duplicates(subset=["SID", "ISO_TIME", "LAT", "LON_180"])
tracks_df = tracks_df.sort_values(["SID", "ISO_TIME"]).reset_index(drop=True)

# First landfall moment per storm
lf_first = (
    tracks_df[tracks_df["on_ph_land"]]
    .sort_values(["SID", "ISO_TIME"])
    .groupby("SID", as_index=False)
    .first()[["SID", "ISO_TIME", "LAT", "LON_180", WIND_COLUMN, "NATURE"]]
    .rename(columns={
        "ISO_TIME": "first_landfall_time",
        "LAT": "first_landfall_lat",
        "LON_180": "first_landfall_lon",
        WIND_COLUMN: "first_landfall_wind",
        "NATURE": "first_landfall_nature",
    })
)

# Storm-level summary
storms_df = (
    tracks_df
    .groupby("SID", as_index=False)
    .agg(
        start_time=("ISO_TIME", "min"),
        end_time=("ISO_TIME", "max"),
        start_year=("year", "min"),
        max_wind=(WIND_COLUMN, "max"),         # lifetime max (for storms that landfell)
        n_track_points=("ISO_TIME", "count"),
        mean_lat=("LAT", "mean"),
        mean_lon=("LON_180", "mean"),
        any_landfall=("on_ph_land", "max"),    # should be True for all kept storms
    )
    .merge(lf_first, on="SID", how="left")
    .sort_values(["start_year", "SID"])
    .reset_index(drop=True)
)

# Intensity label (JTWC-style thresholds in knots)
storms_df["peak_intensity"] = "TD"
storms_df.loc[storms_df["max_wind"] >= 34, "peak_intensity"] = "TS"
storms_df.loc[storms_df["max_wind"] >= 64, "peak_intensity"] = "TY"
storms_df.loc[storms_df["max_wind"] >= 130, "peak_intensity"] = "STY"

# landfall intensity label, based on wind at first landfall point
storms_df["landfall_intensity"] = np.nan
storms_df["landfall_intensity"] = "TD"
storms_df.loc[storms_df["first_landfall_wind"] >= 34, "landfall_intensity"] = "TS"
storms_df.loc[storms_df["first_landfall_wind"] >= 64, "landfall_intensity"] = "TY"
storms_df.loc[storms_df["first_landfall_wind"] >= 130, "landfall_intensity"] = "STY"

# exports
OUT_TRACKS_PATH.parent.mkdir(parents=True, exist_ok=True)
tracks_df.to_csv(OUT_TRACKS_PATH, index=False)
storms_df.to_csv(OUT_STORMS_PATH, index=False)

print(f"Saved tracks CSV to: {OUT_TRACKS_PATH}")
print(f"Saved storms CSV to: {OUT_STORMS_PATH}")
print("Tracks rows:", len(tracks_df), "| Storms:", storms_df["SID"].nunique())
print("\nLandfall intensity counts (first landfall point):")
print(storms_df["landfall_intensity"].value_counts(dropna=False).to_dict())
