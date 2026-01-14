from pathlib import Path

import pandas as pd
import streamlit as st

STORMS_CSV = Path("data/processed/IBTrACS/v2/ibtracs_par_1950_2023_storms_2.csv")


@st.cache_data
def load_storms(path: Path) -> pd.DataFrame:
    """Load storm-level IBTrACS dataset (already PAR-filtered and classified)."""
    df = pd.read_csv(path)

    # Minimal cleaning: normalise intensity labels
    df["peak_intensity"] = df["peak_intensity"].astype(str).str.upper().str.strip()

    # Ensure year is numeric for coverage + later time-series work
    df["start_year"] = pd.to_numeric(df["start_year"], errors="coerce")

    return df


def compute_headline_kpis(storms: pd.DataFrame) -> dict:
    """Compute headline KPIs from storm-level rows."""
    df = storms.copy()

    # Total unique storms
    total = df["SID"].nunique()

    # Study period
    year_ok = df["start_year"].dropna()
    start_year = int(year_ok.min()) if not year_ok.empty else None
    end_year = int(year_ok.max()) if not year_ok.empty else None

    # Composition
    classes = ["TD", "TS", "TY", "STY"]
    counts = {c: int((df["peak_intensity"] == c).sum()) for c in classes}
    props = {c: (counts[c] / total * 100.0) if total else 0.0 for c in classes}

    high_intensity_share = ((counts["TY"] + counts["STY"]) / total * 100.0) if total else 0.0

    return {
        "total_storms": total,
        "start_year": start_year,
        "end_year": end_year,
        "counts": counts,
        "props": props,
        "high_intensity_share": high_intensity_share,
    }


# -------------------------
# Page UI
# -------------------------
st.set_page_config(page_title="Overview & Provenance", layout="wide")

st.title("Island of Storms: A Typhoon-Centric Dashboard of the Philippines")
st.write(
    "The dashboard analyses nine ERA5-derived precipitation and extreme-rainfall indices against IBTrACS "
    "typhoon frequency and wind-based intensity metrics within the Philippine Area of Responsibility."
)

try:
    storms_df = load_storms(STORMS_CSV)
except Exception as e:
    st.error(f"Failed to load storms CSV: {STORMS_CSV}")
    st.exception(e)
    st.stop()

kpis = compute_headline_kpis(storms_df)

# Headline KPI row
c1, c2, c3, c4 = st.columns(4)

c1.metric("Total storms affecting PAR", f"{kpis['total_storms']:,}")

if kpis["start_year"] is not None and kpis["end_year"] is not None:
    n_years = (kpis["end_year"] - kpis["start_year"]) + 1
    c2.metric("Study period", f"{kpis['start_year']}–{kpis['end_year']}", f"{n_years} years")
else:
    c2.metric("Study period", "Unknown")

c3.metric("High-intensity share (TY + STY)", f"{kpis['high_intensity_share']:.1f}%")
c4.metric("Super Typhoons (STY)", f"{kpis['counts']['STY']:,}", f"{kpis['props']['STY']:.1f}%")

st.divider()

st.subheader("Intensity composition (peak intensity per storm, within PAR)")
b1, b2, b3, b4 = st.columns(4)
b1.metric("TD", f"{kpis['counts']['TD']:,}", f"{kpis['props']['TD']:.1f}%")
b2.metric("TS", f"{kpis['counts']['TS']:,}", f"{kpis['props']['TS']:.1f}%")
b3.metric("TY", f"{kpis['counts']['TY']:,}", f"{kpis['props']['TY']:.1f}%")
b4.metric("STY", f"{kpis['counts']['STY']:,}", f"{kpis['props']['STY']:.1f}%")

with st.expander("Debug: show sample storms rows"):
    st.write("Columns:", list(storms_df.columns))
    st.dataframe(storms_df.head(10))
