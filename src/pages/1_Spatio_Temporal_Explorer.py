import streamlit as st
import pandas as pd
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DATA = REPO_ROOT / "data"

from src.visualisations.spatio_temporal_explorer import render_spatio_temporal_explorer



st.set_page_config(
    page_title="Spatio-Temporal Explorer",
    layout="wide"
)

STORMS_V4 = DATA / "processed/IBTrACS/v4_landfall/ibtracs_ph_landfall_1950_2023_storms.csv"
TRACKS_V4 = DATA / "processed/IBTrACS/v4_landfall/ibtracs_ph_landfall_1950_2023_tracks.csv"

PH_GEOJSON = DATA / "assets/geo/philippines.geojson"


@st.cache_data(show_spinner=False)
def load_storms() -> pd.DataFrame:
    df = pd.read_csv(STORMS_V4)
    df["start_year"] = df["start_year"].astype(int)
    df["peak_intensity"] = df["peak_intensity"].fillna("UNK")
    return df

@st.cache_data(show_spinner=False)
def load_tracks() -> pd.DataFrame:
    df = pd.read_csv(TRACKS_V4)

    df["ISO_TIME"] = pd.to_datetime(df["ISO_TIME"], errors="coerce", utc=True)
    df["year"] = df["year"].astype(int)

    # on_ph_land exists in v4
    if "on_ph_land" in df.columns:
        df["on_ph_land"] = df["on_ph_land"].astype(bool)
    else:
        df["on_ph_land"] = False

    # use LON_180 if present (cleaner map continuity)
    if "LON_180" in df.columns:
        df["LON_PLOT"] = df["LON_180"]
    else:
        df["LON_PLOT"] = df["LON"]

    df = df.dropna(subset=["LAT", "LON_PLOT"])
    return df


storms_df = load_storms()
tracks_df = load_tracks()

render_spatio_temporal_explorer(
    storms_df=storms_df,
    tracks_df=tracks_df,
    ph_geojson=PH_GEOJSON,
)