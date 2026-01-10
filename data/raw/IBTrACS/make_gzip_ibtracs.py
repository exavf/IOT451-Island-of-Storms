### NOTE: Had to compress original ibtracs.WP.list.v04r01.csv due to 
### "remote: error: File data/raw/IBTrACS/ibtracs.WP.list.v04r01.csv is 108.19 MB;
### this exceeds GitHub Enterprise's file size limit of 100.00 MB"

import pandas as pd
from pathlib import Path

INPUT_CSV_PATH = Path("data/raw/IBTrACS/ibtracs.WP.list.v04r01.csv")
OUTPUT_GZ_PATH = Path("data/raw/IBTrACS/ibtracs_full.csv.gz")

dataframe = pd.read_csv(
    INPUT_CSV_PATH,
    low_memory=False,
)

OUTPUT_GZ_PATH.parent.mkdir(parents=True, exist_ok=True)

dataframe.to_csv(
    OUTPUT_GZ_PATH,
    index=False,
    compression="gzip",
)

print("Compressed IBTrACS CSV saved to:")
print(OUTPUT_GZ_PATH)
print("File size (bytes):", OUTPUT_GZ_PATH.stat().st_size)
print("Rows:", len(dataframe))
print("Columns:", len(dataframe.columns))
