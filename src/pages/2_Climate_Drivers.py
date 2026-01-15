from __future__ import annotations

from pathlib import Path
import streamlit as st
import numpy as np
import pandas as pd

from visualisations.climate_drivers import render_visual_1_baselines, render_visual_2A_correlation_heatmap

PAR_V3 = Path("data/processed/IBTrACS/v3_within_par/ibtracs_par_1950_2023_storms_3.csv")
LANDFALL_V4 = Path("data/processed/IBTrACS/v4_landfall/ibtracs_ph_landfall_1950_2023_storms.csv")
ERA5_MERGED_CSV_PATH = Path("data/processed/era5/merged_era5_data.csv")
# redundant from overview, ok for standalone page
@st.cache_data
def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)

@st.cache_data(show_spinner=False)
def load_era5_merged(csv_path: Path = ERA5_MERGED_CSV_PATH) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"ERA5 merged CSV not found at: {csv_path}")
    df = pd.read_csv(csv_path)
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    return df

def render_page() -> None:
    st.set_page_config(page_title="Climate Drivers", layout="wide")

    st.title("Climate Drivers")
    st.write(
        "We examine long-run rainfall extremes over the Philippines to characterise background climate stress "
        "before relating these signals to typhoon exposure (PAR) and landfall impact."
    )

    # load data (cached)
    try:
        era5_df = load_era5_merged()
        par_df = load_csv(PAR_V3)
        landfall_df = load_csv(LANDFALL_V4)
    except Exception as e:
        st.error(f"Failed to load datasets: {e}")
        st.stop()

    #Visual 1
    render_visual_1_baselines(era5_df)

    with st.expander("Method notes", expanded=False):
        st.markdown(
            """
- Climate indices are analysed at **annual resolution** to match storm-year aggregation.
- The rolling mean overlay is optional and used only to aid interpretation of multi-decadal patterns.
            """.strip()
        )

    st.divider()

    # Visual 2A
    render_visual_2A_correlation_heatmap(era5_df, par_df, landfall_df  )
    with st.expander("What do these climate variables represent?", expanded=False):
        st.caption(
            """
    • **CDD**: length of dry spells (consecutive dry days)  
    • **CWD**: persistence of rainfall (consecutive wet days)  
    • **Rx1day**: single-day rainfall extremes  
    • **Rx5day**: multi-day rainfall accumulation  
    • **R20mm**: frequency of heavy rainfall days (≥ 20 mm)  
    • **R50mm**: frequency of very heavy rainfall days (≥ 50 mm)  
    • **R95pTOT**: share of rainfall from extreme events  
    • **PR**: mean annual precipitation  
    • **PR%**: precipitation anomaly relative to the long-term mean
            """.strip()
        )



if __name__ == "__main__":
    render_page()
