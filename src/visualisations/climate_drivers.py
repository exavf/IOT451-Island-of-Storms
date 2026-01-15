from __future__ import annotations

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Canonical climate drivers (locked)
CLIMATE_VARS_9 = [
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

VAR_LABELS = {
    "cdd": "CDD (Consecutive Dry Days)",
    "cwd": "CWD (Consecutive Wet Days)",
    "rx1day": "Rx1day (Max 1-day precip)",
    "rx5day": "Rx5day (Max 5-day precip)",
    "pr": "PR (Mean precip)",
    "prpercent": "PR% (Precip anomaly %)",
    "r20mm": "R20mm (Days ≥ 20mm)",
    "r50mm": "R50mm (Days ≥ 50mm)",
    "r95ptot": "R95pTOT (% precip from very wet days)",
}


DEFAULT_VARS_VIS1 = ["rx1day", "rx5day", "cwd", "r50mm"]


def validate_era5_df(era5_df: pd.DataFrame, required_vars: list[str] | None = None) -> None:
    # casual but thorough checks
    if era5_df is None or era5_df.empty:
        st.error("ERA5 dataset is empty or not loaded.")
        st.stop()

    if "year" not in era5_df.columns:
        st.error("ERA5 dataset is missing the required 'year' column.")
        st.stop()

    # make sure year is usable
    try:
        era5_df["year"] = pd.to_numeric(era5_df["year"], errors="raise").astype(int)
    except Exception:
        st.error("ERA5 'year' column must be numeric (or convertible to int).")
        st.stop()

    if required_vars:
        missing = [v for v in required_vars if v not in era5_df.columns]
        if missing:
            st.warning(f"Some requested ERA5 variables are missing and will be ignored: {missing}")


@st.cache_data(show_spinner=False)
def prepare_era5_timeseries(era5_df: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    df = era5_df.copy()
    keep = ["year"] + variables
    df = df[keep]

    for v in variables:
        df[v] = pd.to_numeric(df[v], errors="coerce")

    df = df.dropna(subset=["year"]).sort_values("year")
    return df


def make_timeseries_fig(df: pd.DataFrame, var: str, rolling_window: int | None) -> plt.Figure:
    fig, ax = plt.subplots()
    ax.plot(df["year"], df[var], marker="o", linewidth=1)

    if rolling_window and rolling_window >= 2:
        rolled = df[var].rolling(window=rolling_window, min_periods=1).mean()
        ax.plot(df["year"], rolled, linewidth=2)

    label = VAR_LABELS.get(var, var)
    ax.set_title(f"{label} over time")
    ax.set_ylabel(label)
    ax.grid(True, alpha=0.3)
    return fig


def render_visual_1_baselines(era5_df: pd.DataFrame) -> None:
    st.subheader("Climate baseline trends (ERA5)")

    validate_era5_df(era5_df)

    # only allow plotting of the canonical 9 variables that exist in the dataframe
    available_vars = [v for v in CLIMATE_VARS_9 if v in era5_df.columns]

    missing_canon = [v for v in CLIMATE_VARS_9 if v not in era5_df.columns]
    if missing_canon:
        st.warning(f"ERA5 is missing some expected climate variables: {missing_canon}")

    default = [v for v in DEFAULT_VARS_VIS1 if v in available_vars]


    variables = st.multiselect(
        "Select climate variables",
        options=sorted(available_vars),
        default=default,
        help="Small multiples: one chart per variable.",
        key="vis1_climate_vars",  
    )

    if not variables:
        st.info("Pick at least one variable to display.")
        return
    
    df = prepare_era5_timeseries(era5_df, variables)

    use_rolling = st.toggle(
        "Overlay rolling mean",
        value=True,
        key="vis1_rolling_toggle",
    )
    rolling_window = 5 if use_rolling else None

    charts_per_row = st.slider(
        "Charts per row",
        2, 4, 2,
        key="vis1_charts_per_row",
    )

    # year range selector
    min_year = int(df["year"].min())
    max_year = int(df["year"].max())

    year_range = st.slider(
        "Select year range",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
        key="vis1_year_range",
    )

    df = df[(df["year"] >= year_range[0]) & (df["year"] <= year_range[1])]

    # render small multiples
    for i in range(0, len(variables), charts_per_row):
        row_vars = variables[i : i + charts_per_row]
        cols = st.columns(len(row_vars))
        for col, var in zip(cols, row_vars):
            with col:
                fig = make_timeseries_fig(df, var, rolling_window)
                st.pyplot(fig, clear_figure=True)

    st.caption(
        "Rolling mean is shown only to improve readability of long-run patterns; "
        "analysis focuses on multi-decadal behaviour."
    )

def build_storm_year_metrics(storms_df: pd.DataFrame, mode: str) -> pd.DataFrame:
    """
    Annual storm metrics from storms-level tables.

    mode:
      - "v3_par": uses par_peak_intensity
      - "v4_landfall": filters any_landfall if present and uses landfall_intensity (fallback peak_intensity)
    """
    if storms_df is None or storms_df.empty:
        st.error("Storms dataset is empty or not loaded.")
        st.stop()

    if "start_year" not in storms_df.columns:
        st.error("Storms dataset missing required column: 'start_year'.")
        st.stop()

    df = storms_df.copy()
    df = df.dropna(subset=["start_year"])
    df["start_year"] = pd.to_numeric(df["start_year"], errors="coerce").astype(int)

    if mode == "v3_par":
        intensity_col = "par_peak_intensity"
        if intensity_col not in df.columns:
            st.error("v3 storms missing required column: 'par_peak_intensity'.")
            st.stop()

    elif mode == "v4_landfall":
        if "any_landfall" in df.columns:
            # handle bool, 0/1, strings
            df["any_landfall"] = df["any_landfall"].astype(str).str.lower().isin(["true", "1", "yes"])
            df = df[df["any_landfall"] == True]

        intensity_col = "landfall_intensity"
        if intensity_col not in df.columns:
            if "peak_intensity" in df.columns:
                intensity_col = "peak_intensity"
            else:
                st.error("v4 storms missing 'landfall_intensity' and 'peak_intensity'.")
                st.stop()
    else:
        st.error(f"Unknown mode: {mode}")
        st.stop()

    # Base metrics
    out = (
        df.groupby("start_year")
        .agg(
            storm_count=("SID", "nunique"),
            mean_max_wind=("max_wind", "mean"),
        )
        .reset_index()
        .rename(columns={"start_year": "year"})
    )

    # Counts by class (TD/TS/TY/STY)
    class_counts = (
        df.groupby(["start_year", intensity_col])["SID"]
        .nunique()
        .unstack(fill_value=0)
        .reset_index()
        .rename(columns={"start_year": "year"})
    )

    for c in ["TD", "TS", "TY", "STY"]:
        if c not in class_counts.columns:
            class_counts[c] = 0

    class_counts = class_counts.rename(
        columns={"TD": "td_count", "TS": "ts_count", "TY": "ty_count", "STY": "sty_count"}
    )
    class_counts["ty_sty_count"] = class_counts["ty_count"] + class_counts["sty_count"]

    out = out.merge(
        class_counts[["year", "td_count", "ts_count", "ty_count", "sty_count", "ty_sty_count"]],
        on="year",
        how="left",
    )

    for c in ["storm_count", "td_count", "ts_count", "ty_count", "sty_count", "ty_sty_count"]:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype(int)

    return out


def merge_climate_and_storm_metrics(
    era5_df: pd.DataFrame, year_metrics_df: pd.DataFrame, climate_vars: list[str]
) -> pd.DataFrame:
    """Inner-join climate and annual storm metrics by year."""
    c = era5_df.copy()
    c["year"] = pd.to_numeric(c["year"], errors="coerce").astype(int)

    keep = ["year"] + climate_vars
    c = c[keep]

    for v in climate_vars:
        c[v] = pd.to_numeric(c[v], errors="coerce")

    merged = c.merge(year_metrics_df, on="year", how="inner")
    return merged


def render_visual_2A_correlation_heatmap(
    era5_df: pd.DataFrame, storms_v3_df: pd.DataFrame, storms_v4_df: pd.DataFrame
) -> None:
    st.subheader("Visual 2 — Climate drivers vs typhoon frequency (correlation heatmap)")

    dataset_mode = st.radio(
        "Storm dataset",
        options=["v3 (PAR exposure)", "v4 (landfall impact)"],
        horizontal=True,
        key="vis2_dataset_mode",
    )
    mode = "v3_par" if dataset_mode.startswith("v3") else "v4_landfall"
    storms_df = storms_v3_df if mode == "v3_par" else storms_v4_df

    storm_metric = st.selectbox(
        "Storm metric (annual)",
        options=["storm_count", "td_count", "ts_count", "ty_sty_count", "mean_max_wind"],
        help="Counts are annual totals; mean_max_wind is the annual mean of storm max_wind.",
        key="vis2_metric",
    )

    climate_vars = [v for v in CLIMATE_VARS_9 if v in era5_df.columns]
    if not climate_vars:
        st.error("None of the 9 climate variables are present in ERA5 dataframe.")
        st.stop()

    # Build annual metrics + merge
    year_metrics = build_storm_year_metrics(storms_df, mode)
    merged = merge_climate_and_storm_metrics(era5_df, year_metrics, climate_vars)

    if merged.empty:
        st.error("Merged dataset is empty after joining climate + storms by year.")
        st.stop()

    # Shared year slider
    min_year = int(merged["year"].min())
    max_year = int(merged["year"].max())
    year_range = st.slider(
        "Select year range",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
        key=f"vis2_year_range_{mode}",
    )
    merged = merged[(merged["year"] >= year_range[0]) & (merged["year"] <= year_range[1])]

    # Correlations (one row: storm_metric vs all climate vars)
    corrs = []
    for v in climate_vars:
        x = merged[v]
        y = merged[storm_metric]

        if x.notna().sum() < 3 or y.notna().sum() < 3:
            corrs.append(np.nan)
            continue
        if x.nunique(dropna=True) <= 1 or y.nunique(dropna=True) <= 1:
            corrs.append(np.nan)
            continue

        corrs.append(x.corr(y))

    data = np.array([corrs])  # (1, n_vars)

    fig, ax = plt.subplots(figsize=(max(7, len(climate_vars) * 0.9), 2.4))
    im = ax.imshow(data, aspect="auto")

    ax.set_yticks([0])
    ax.set_yticklabels([storm_metric])
    ax.set_xticks(range(len(climate_vars)))
    ax.set_xticklabels(climate_vars, rotation=45, ha="right")

    for j, val in enumerate(corrs):
        ax.text(j, 0, "NA" if np.isnan(val) else f"{val:.2f}", ha="center", va="center")

    ax.set_title(f"Pearson correlation: climate drivers vs {storm_metric} ({dataset_mode})")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    st.pyplot(fig, clear_figure=True)

    st.write(
        "Pearson correlation coefficients quantify the strength and direction of linear association "
        "between two variables, ranging from −1 (strong negative) to +1 (strong positive)."
    )

    st.caption(
        "Exploratory Pearson correlations. Useful for screening relationships, not causal inference."
    )

