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

@st.cache_data
def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)

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

