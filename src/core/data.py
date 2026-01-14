
## loaders to load v3 v4 csvs

# src/core/data.py
from pathlib import Path

import pandas as pd
import streamlit as st

PAR_V3_STORMS = Path("data/processed/IBTrACS/v3_within_par/ibtracs_par_1950_2023_storms_3.csv")
LANDFALL_V4_STORMS = Path("data/processed/IBTrACS/v4_landfall/ibtracs_ph_landfall_1950_2023_storms.csv")


@st.cache_data
def load_ibtracs_par_v3(path: Path = PAR_V3_STORMS) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["par_peak_intensity"] = df["par_peak_intensity"].astype(str).str.upper().str.strip()
    df["start_year"] = pd.to_numeric(df["start_year"], errors="coerce")
    return df


@st.cache_data
def load_ibtracs_landfall_v4(path: Path = LANDFALL_V4_STORMS) -> pd.DataFrame:
    df = pd.read_csv(path)

    # These normalisations won’t break if some cols are missing
    if "landfall_intensity" in df.columns:
        df["landfall_intensity"] = df["landfall_intensity"].astype(str).str.upper().str.strip()
    if "peak_intensity" in df.columns:
        df["peak_intensity"] = df["peak_intensity"].astype(str).str.upper().str.strip()

    if "start_year" in df.columns:
        df["start_year"] = pd.to_numeric(df["start_year"], errors="coerce")

    return df
