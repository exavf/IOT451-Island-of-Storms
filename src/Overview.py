from __future__ import annotations

from pathlib import Path
import pandas as pd
import streamlit as st
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from visualisations.Overview import (
    render_overview_exposure_vs_impact,
    render_intensity_frequency_timeseries,
)


PAR_V3 = Path("data/processed/IBTrACS/v3_within_par/ibtracs_par_1950_2023_storms_3.csv")
LANDFALL_V4 = Path("data/processed/IBTrACS/v4_landfall/ibtracs_ph_landfall_1950_2023_storms.csv")
ERA5_MERGED_CSV_PATH = Path("data/processed/era5/merged_era5_data.csv")

@st.cache_data
def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)

@st.cache_data(show_spinner=False)
def load_era5_merged(csv_path: Path = ERA5_MERGED_CSV_PATH) -> pd.DataFrame:
    """
    Expected columns include:
    year, cwd, rx1day, rx5day, pr, prpercent, r20mm, r50mm, r95ptot, ...
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"ERA5 merged CSV not found at: {csv_path}")

    df = pd.read_csv(csv_path)

    # make 'year' usable everywhere
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

    return df

st.set_page_config(page_title="Island of Storms — Overview", layout="wide")

st.title("Island of Storms - The Philippines")
st.write("The Philippines, an archipelagic nation of over 7,600 islands, lies within the western North Pacific basin "
"and is consequently one of the most typhoon-exposed countries in the world.")
st.write(
    "This dashboard analyses nine ERA5-derived precipitation and extreme-rainfall indices against IBTrACS "
    "typhoon frequency and wind-based intensity metrics within the **Philippine Area of Responsibility (PAR)**."
)

st.divider()

par_df = load_csv(PAR_V3)
landfall_df = load_csv(LANDFALL_V4)

render_overview_exposure_vs_impact(par_df, landfall_df)
render_intensity_frequency_timeseries(par_df, landfall_df)

