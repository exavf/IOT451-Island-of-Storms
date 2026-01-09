import json
import pandas as pd
from pathlib import Path

# Initial Configuration

RAW_DATA_DIR = Path("data/raw/era5")
OUTPUT_CSV_PATH = Path("data/processed/ERA5/merged_era5_data.csv")

JSON_FILES = [
    "era5_phl_annual_1950_2023_cdd_r50mm_r95ptot.json",
    "era5_phl_annual_1950_2023_cwd_rx1day_rx5day.json",
    "era5_phl_annual_1950_2023_pr_prpercent_r20mm.json",
]

COLUMN_ORDER = [
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
# Method to load aformentioned JSON files into a single DataFrame

def json_to_dataframe(path: Path, country_code: str = "PHL") -> pd.DataFrame:
    with open(path, "r") as file:
        raw = json.load(file) 

    data = raw["data"] # bc raw is a json object, we can reference key directly as a dict
    parts = []

    for var_name, var_payload in data.items():
        series = pd.Series(var_payload[country_code], name=var_name)
        parts.append(series)

    dataframe = pd.concat(parts, axis=1) # lines things up side-by-side (this way <-->)
    dataframe.index = pd.to_datetime(dataframe.index).year # converts "YYYY-07" to just year (as int)
    dataframe.index.name = "year" # names index for clarity, was using key-value pairs before
    dataframe = dataframe.reset_index() # makes year a column instead of index for merging later

    dataframe = dataframe.rename(columns={"prpercnt": "prpercent"}) # personal preference to rename prpercnt to prpercent for less ambiguity later 

    return dataframe

# loops through all json files and populates dataframes list with dataframes created from each file bosh
dataframes = [json_to_dataframe(RAW_DATA_DIR / filename) for filename in JSON_FILES]

# we then merge all 'triple tables' on year as its linking key
merged = dataframes[0]
for dataframe in dataframes [1:]:
    merged = merged.merge(dataframe, on="year", how="inner")

merged = merged.sort_values("year").reset_index(drop=True)

# double check column order is same, or if something is missing after merge
missing = [c for c in COLUMN_ORDER if c not in merged.columns]
if missing:
    raise KeyError(f"Missing columns after merge: {missing}")

merged = merged[COLUMN_ORDER]

# final export + confirmation outputs

OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
merged.to_csv(OUTPUT_CSV_PATH, index=False)

print(f"Saved CSV to {OUTPUT_CSV_PATH}")
print("Columns:", merged.columns.tolist())
print("Rows:", len(merged))