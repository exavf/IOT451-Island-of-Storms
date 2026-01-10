import pandas as pd
from pathlib import Path

RAW_CSV_PATH = Path("data/raw/IBTrACS/ibtracs.WP.list.v04r01.csv")
OUT_TRACKS_PATH = Path("data/processed/IBTrACS/ibtracs_par_1950_2023_tracks.csv")
OUT_STORMS_PATH = Path("data/processed/IBTrACS/ibtracs_par_1950_2023_storms.csv")

# because our dataset from era5 is also 1950-2023
START_YEAR = 1950
END_YEAR = 2023

# Rough Philippine Area of Responsibility (PAR) using simple box approximation
PAR_LAT_MIN, PAR_LAT_MAX = 5, 25
PAR_LON_MIN, PAR_LON_MAX = 115, 135

WIND_COLUMN = "USA_WIND" # one wind standard for consistency i reckon
KEEP_NATURE = {"TD", "TS", "TY"} # all tropical cyclones (TCs): tropical depressions, storms, typhoons

# minimal for now probably (add more later if needed)
USE_COLUMNS = ["SID", "ISO_TIME", "LAT", "LON", "NATURE", WIND_COLUMN]

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


# Philippine Area of Responsibility (PAR) filtering (box approximation as mentioned above)
inside_par = (
    (dataframe["LAT"] >= PAR_LAT_MIN) & (dataframe["LAT"] <= PAR_LAT_MAX) &
    (dataframe["LON"] >= PAR_LON_MIN) & (dataframe["LON"] <= PAR_LON_MAX)
)

# get unique storm IDs that entered PAR (removes duplicates automatically)
par_storm_ids = dataframe.loc[inside_par, "SID"].unique()
if len(par_storm_ids) == 0:
    print("Warning: No storms entered the PAR after filtering. Output files will be empty.")

# we kinda want the full track history for analysis later on
tracks_dataframe = dataframe[dataframe["SID"].isin(par_storm_ids)].copy()


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

# Intensity label based on Joint Typhoon Warning Center (JTWC) standards
storms_dataframe["peak_intensity"] = "TD" # default to tropical depression
storms_dataframe.loc[storms_dataframe["max_wind"] >= 34, "peak_intensity"] = "TS" # tropical storm
storms_dataframe.loc[storms_dataframe["max_wind"] >= 64, "peak_intensity"] = "TY" # typhoon
storms_dataframe.loc[storms_dataframe["max_wind"] >= 130, "peak_intensity"] = "STY" # super typhoon


# actual exports
OUT_TRACKS_PATH.parent.mkdir(parents=True, exist_ok=True)
tracks_dataframe.to_csv(OUT_TRACKS_PATH, index=False)
storms_dataframe.to_csv(OUT_STORMS_PATH, index=False)

print(f"Saved tracks CSV to: {OUT_TRACKS_PATH}")
print(f"Saved storms CSV to: {OUT_STORMS_PATH}")
print("Tracks rows:", len(tracks_dataframe), "| Storms:", len(storms_dataframe))
print("Storm intensity counts:", storms_dataframe["peak_intensity"].value_counts().to_dict())
