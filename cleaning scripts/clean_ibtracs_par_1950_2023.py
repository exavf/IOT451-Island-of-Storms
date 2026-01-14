import pandas as pd
import numpy as np
from pathlib import Path
from matplotlib.path import Path as MplPath

RAW_CSV_PATH = Path("data/raw/IBTrACS/ibtracs_wp_full.csv.gz")
OUT_TRACKS_PATH = Path("data/processed/IBTrACS/v3/ibtracs_par_1950_2023_tracks_3.csv")
OUT_STORMS_PATH = Path("data/processed/IBTrACS/v3/ibtracs_par_1950_2023_storms_3.csv")

# because our dataset from era5 is also 1950-2023
START_YEAR = 1950
END_YEAR = 2023

WIND_COLUMN = "USA_WIND" # one wind standard for consistency i reckon
KEEP_NATURE = {"TD", "TS", "TY"} # all tropical cyclones (TCs): tropical depressions, storms, typhoons

# minimal for now probably (add more later if needed)
USE_COLUMNS = ["SID", "ISO_TIME", "LAT", "LON", "NATURE", WIND_COLUMN]

# PAGASA PAR polygon (lon, lat) points in order
PAR_POLYGON = [
    (115, 5),
    (115, 15),
    (120, 21),
    (120, 25),
    (135, 25),
    (135, 5),
]

#basic checks (file existence + required columns)
if not RAW_CSV_PATH.exists():
    raise FileNotFoundError(f"Could not find input CSV at: {RAW_CSV_PATH}")

header_columns = pd.read_csv(RAW_CSV_PATH, nrows=0).columns.tolist()
missing_columns = [col for col in USE_COLUMNS if col not in header_columns]
if missing_columns:
    raise KeyError(
        f"Missing required columns: {missing_columns}\n"
        f"Available columns include: {header_columns[:30]} ... (total {len(header_columns)})"
    )

# loading actual data to df 
dataframe = pd.read_csv(RAW_CSV_PATH, usecols=USE_COLUMNS, low_memory=False)

dataframe["ISO_TIME"] = pd.to_datetime(dataframe["ISO_TIME"], errors="coerce")
dataframe["LAT"] = pd.to_numeric(dataframe["LAT"], errors="coerce")
dataframe["LON"] = pd.to_numeric(dataframe["LON"], errors="coerce")
dataframe[WIND_COLUMN] = pd.to_numeric(dataframe[WIND_COLUMN], errors="coerce")

# drop rows we can't interpret safely (i.e. if anything has invalid value in any of these columns we drop the row)
dataframe = dataframe.dropna(subset=["SID", "ISO_TIME", "LAT", "LON", WIND_COLUMN])

# add year column for filtering + aggregation
dataframe["year"] = dataframe["ISO_TIME"].dt.year
dataframe = dataframe[(dataframe["year"] >= START_YEAR) & (dataframe["year"] <= END_YEAR)]

# Restrict to tropical systems (Tropical Cyclones only)
dataframe = dataframe[dataframe["NATURE"].isin(KEEP_NATURE)]

# Checking for PAR more accurately using polygon method instead of square approximation
par_path = MplPath(PAR_POLYGON)  # polygon expects (lon, lat)
points = np.column_stack([dataframe["LON"].to_numpy(), dataframe["LAT"].to_numpy()])
dataframe["in_par"] = par_path.contains_points(points)  # addition as a real column

# storms that entered PAR (using all points)
par_storm_ids = dataframe.loc[dataframe["in_par"], "SID"].unique()

# get unique storm IDs that entered PAR (removes duplicates automatically)
par_storm_ids = dataframe.loc[dataframe["in_par"], "SID"].unique()
if len(par_storm_ids) == 0:
    print("Warning: No storms entered the PAR after filtering. Output files will be empty.")

# we kinda want the full track history for analysis later on
tracks_dataframe = dataframe[dataframe["SID"].isin(par_storm_ids)].copy()

dupes = tracks_dataframe.duplicated(subset=["SID", "ISO_TIME", "LAT", "LON"], keep=False)
d = tracks_dataframe.loc[dupes, ["SID", "ISO_TIME", "LAT", "LON", WIND_COLUMN, "in_par"]].copy()

# analyze duplicates
print("Duplicate-like rows:", len(d))
print("Unique duplicate groups:", d.groupby(["SID", "ISO_TIME", "LAT", "LON"]).ngroups)

wind_spread = d.groupby(["SID", "ISO_TIME", "LAT", "LON"])[WIND_COLUMN].nunique()
print("Groups with >1 distinct wind:", (wind_spread > 1).sum())

# Specifically inside PAR
d_inpar = d[d["in_par"]]
wind_spread_inpar = d_inpar.groupby(["SID", "ISO_TIME", "LAT", "LON"])[WIND_COLUMN].nunique()
print("In-PAR groups with >1 distinct wind:", (wind_spread_inpar > 1).sum())

# more light cleaning
tracks_dataframe = tracks_dataframe.drop_duplicates(subset=["SID", "ISO_TIME", "LAT", "LON"]) # removes rows that has all same vals in subset
tracks_dataframe = tracks_dataframe.sort_values(["SID", "ISO_TIME"]).reset_index(drop=True) # we now order rows by time, just to double check standard + indexes redone

#storm-level summary (1 row per storm)
storms_dataframe = (
    tracks_dataframe
    .groupby("SID", as_index=False)
    .agg(
        start_time=("ISO_TIME", "min"),
        end_time=("ISO_TIME", "max"),
        start_year=("year", "min"),
        max_wind=(WIND_COLUMN, "max"),
        n_track_points=("ISO_TIME", "count"),
        mean_lat=("LAT", "mean"),
        mean_lon=("LON", "mean"),
    )
    .sort_values(["start_year", "SID"])
    .reset_index(drop=True)
)

# --- PAR-ONLY peak wind per storm ---
par_max = (
    tracks_dataframe[tracks_dataframe["in_par"]]
    .groupby("SID", as_index=False)
    .agg(par_max_wind=(WIND_COLUMN, "max"))
)

storms_dataframe = storms_dataframe.merge(par_max, on="SID", how="left") 

# if a storm is in par_storm_ids, it *should* have at least one in_par point;
# in case of edge cases / geometry boundary quirks
missing = storms_dataframe["par_max_wind"].isna().sum()
if missing:
    print(f"WARNING: {missing} storms have no par_max_wind after filtering; investigate.")

# Intensity label based on Joint Typhoon Warning Center (JTWC) standards
storms_dataframe["peak_intensity"] = "TD" # default to tropical depression
storms_dataframe.loc[storms_dataframe["max_wind"] >= 34, "peak_intensity"] = "TS" # tropical storm
storms_dataframe.loc[storms_dataframe["max_wind"] >= 64, "peak_intensity"] = "TY" # typhoon
storms_dataframe.loc[storms_dataframe["max_wind"] >= 130, "peak_intensity"] = "STY" # super typhoon

# PAR-only label (interpreted as “peaked in PAR”) - what we want to analyse primarily
storms_dataframe["par_peak_intensity"] = "TD"
storms_dataframe.loc[storms_dataframe["par_max_wind"] >= 34, "par_peak_intensity"] = "TS"
storms_dataframe.loc[storms_dataframe["par_max_wind"] >= 64, "par_peak_intensity"] = "TY"
storms_dataframe.loc[storms_dataframe["par_max_wind"] >= 130, "par_peak_intensity"] = "STY"


# actual exports
OUT_TRACKS_PATH.parent.mkdir(parents=True, exist_ok=True)
tracks_dataframe.to_csv(OUT_TRACKS_PATH, index=False)
storms_dataframe.to_csv(OUT_STORMS_PATH, index=False)

print(f"Saved tracks CSV to: {OUT_TRACKS_PATH}")
print(f"Saved storms CSV to: {OUT_STORMS_PATH}")
print("Tracks rows:", len(tracks_dataframe), "| Storms:", len(storms_dataframe))

print("\nStorms that entered PAR:", storms_dataframe["SID"].nunique())

print("\nLifetime intensity counts (storms that entered PAR at any point):")
print(storms_dataframe["peak_intensity"].value_counts().to_dict())

print("\nPAR-only intensity counts (max wind while inside PAR):")
print(storms_dataframe["par_peak_intensity"].value_counts().to_dict())
