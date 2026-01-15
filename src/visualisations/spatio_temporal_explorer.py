from __future__ import annotations

from pathlib import Path
import json
import pandas as pd
import streamlit as st
import pydeck as pdk


@st.cache_data(show_spinner=False)
def _load_geojson(p: Path) -> dict:
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data(show_spinner=False)
def _heatmap_points(tracks_df: pd.DataFrame, storms_df: pd.DataFrame, land_only_flag: bool) -> pd.DataFrame:
    sids = set(storms_df["SID"].unique().tolist())
    t = tracks_df[tracks_df["SID"].isin(sids)].copy()

    # optional land-only
    if land_only_flag and "on_ph_land" in t.columns:
        t = t[t["on_ph_land"]]

    if t.empty:
        return pd.DataFrame()

    # lon for plotting
    if "LON_PLOT" not in t.columns:
        if "LON_180" in t.columns:
            t["LON_PLOT"] = t["LON_180"]
        else:
            t["LON_PLOT"] = t["LON"]

    t = t.dropna(subset=["LAT", "LON_PLOT"])

    # keep small, avoid dragging 100k+ rows into the deck
    keep = ["SID", "LAT", "LON_PLOT", "USA_WIND"]
    keep = [c for c in keep if c in t.columns]
    t = t[keep].copy()

    return t

@st.cache_data(show_spinner=False)
def _build_paths(tracks_df: pd.DataFrame, storms_df: pd.DataFrame, land_only_flag: bool) -> pd.DataFrame:
    # SID list from storm filter
    sids = set(storms_df["SID"].unique().tolist())
    t = tracks_df[tracks_df["SID"].isin(sids)].copy()

    # only land points (v4 has on_ph_land)
    if land_only_flag and "on_ph_land" in t.columns:
        t = t[t["on_ph_land"]]

    # plotting lon
    if "LON_PLOT" not in t.columns:
        t["LON_PLOT"] = t["LON"]

    t = t.dropna(subset=["LAT", "LON_PLOT"])
    t = t.sort_values(["SID", "ISO_TIME"])

    # stable path build (no groupby.apply edge cases)
    paths_series = t.groupby("SID")[["LON_PLOT", "LAT"]].apply(lambda g: g.values.tolist())
    paths = paths_series.reset_index().rename(columns={0: "path"})

    # tooltip meta
    keep = ["SID", "start_year", "peak_intensity", "max_wind", "n_track_points", "par_max_wind", "par_peak_intensity"]
    keep = [c for c in keep if c in storms_df.columns]
    paths = paths.merge(storms_df[keep], on="SID", how="left")

    # drop tiny paths
    paths = paths[paths["path"].map(lambda x: isinstance(x, list) and len(x) >= 2)].copy()

    return paths

def _intensity_rgba(label: str) -> list[int]:
    return {
        "TD": [120, 120, 120, 220],
        "TS": [70, 130, 180, 220],
        "TY": [255, 165, 0, 220],
        "STY": [220, 20, 60, 230],
    }.get(label, [100, 100, 100, 200])

def _add_color(df: pd.DataFrame, mode: str) -> pd.DataFrame:
    out = df.copy()

    if mode == "Landfall intensity":
        out["color"] = out["peak_intensity"].map(_intensity_rgba)
        return out

    if mode == "PAR peak intensity":
        if "par_peak_intensity" in out.columns:
            out["color"] = out["par_peak_intensity"].fillna("UNK").map(_intensity_rgba)
        else:
            out["color"] = [[100, 100, 100, 120]] * len(out)
        return out

    # max wind grayscale ramp
    w = pd.to_numeric(out.get("max_wind", 0), errors="coerce").fillna(0.0)
    w_min = float(w.min())
    w_max = float(w.max() if w.max() > w.min() else w.min() + 1.0)

    def wind_rgba(v: float) -> list[int]:
        t = (v - w_min) / (w_max - w_min)
        g = int(60 + 180 * t)
        return [g, g, g, 160]

    out["color"] = w.map(wind_rgba)
    return out


def render_spatio_temporal_explorer(
    storms_df: pd.DataFrame,
    tracks_df: pd.DataFrame,
    ph_geojson: Path,
    par_geojson: Path | None = None,
) -> None:
    st.title("Spatio-Temporal Explorer")
    st.caption("Landfall tracks over time (v4).")

    if not ph_geojson.exists():
        st.error("Missing philippines.geojson")
        st.stop()

    ph = _load_geojson(ph_geojson)

    par = None
    if par_geojson is not None and par_geojson.exists():
        par = _load_geojson(par_geojson)

    # sidebar
    with st.sidebar:
        st.header("Filters")

        # time + intensity
        y0 = int(storms_df["start_year"].min())
        y1 = int(storms_df["start_year"].max())
        year_min, year_max = st.slider(
            "Year range",
            y0, y1, (y0, y1), 1
        )

        base = ["TD", "TS", "TY", "STY"]
        present = set(storms_df["peak_intensity"].dropna().unique())
        intensity_opts = [x for x in base if x in present] or sorted(present)

        intensities = st.multiselect(
            "Landfall intensity",
            intensity_opts,
            default=intensity_opts,
        )

        st.markdown("---")

        # map behaviour
        map_mode = st.selectbox(
            "Map mode",
            ["Landfall points", "Heatmap", "Tracks (selected only)"],
            index=1,
        )

        # track colouring (only matters for tracks)
        if map_mode == "Tracks (selected only)":
            color_mode = st.selectbox(
                "Track colour",
                ["Landfall intensity", "Max wind (kt)", "PAR peak intensity"],
                index=0,
            )
        else:
            color_mode = "Landfall intensity"

        # heatmap tuning
        if map_mode == "Heatmap":
            heat_weight = st.selectbox(
                "Heat weight",
                ["Density", "Wind-weighted"],
                index=0,
            )

            max_points = st.slider(
                "Max points",
                5_000, 120_000, 40_000, 5_000
            )
        else:
            heat_weight = "Density"
            max_points = 40_000

        # spatial mask
        land_only = st.toggle(
            "Only show points on PH land",
            value=False,
        )

    # storm filter
    storms_f = storms_df[
        storms_df["start_year"].between(year_min, year_max)
        & storms_df["peak_intensity"].isin(intensities)
    ].copy()

    if storms_f.empty:
        st.warning("No storms match the selected filters.")
        st.stop()

    # choose what to render
    if map_mode == "Heatmap":
        pts = _heatmap_points(tracks_df, storms_f, land_only)

        if pts.empty:
            st.warning("No points available for heatmap.")
            st.stop()

        if heat_weight == "Wind-weighted" and "USA_WIND" in pts.columns:
            pts["weight"] = pd.to_numeric(pts["USA_WIND"], errors="coerce").fillna(0.0)
        else:
            pts["weight"] = 1.0

        if len(pts) > max_points:
            pts = pts.sample(n=max_points, random_state=42)

    elif map_mode == "Tracks (selected only)":
        paths = _build_paths(tracks_df, storms_f, land_only)

        if paths.empty:
            st.warning("No tracks to render for this selection.")
            st.stop()

        paths = _add_color(paths, color_mode)

        a, b = st.columns(2)
        with a:
            st.metric("Storms", f"{storms_f['SID'].nunique():,}")
        with b:
            st.metric("Rendered tracks", f"{len(paths):,}")

    else:
        st.info("Landfall points mode not wired yet. Switch to Heatmap or Tracks for now.")
        st.stop()



    # build paths (always)
    paths = _build_paths(tracks_df, storms_f, land_only)

    paths = _add_color(paths, color_mode)

    a, b = st.columns(2)

    if map_mode == "Heatmap":
        with a:
            st.metric("Storms", f"{storms_f['SID'].nunique():,}")
        with b:
            st.metric("Heatmap points", f"{len(pts):,}")

    elif map_mode == "Tracks (selected only)":
        with a:
            st.metric("Storms", f"{storms_f['SID'].nunique():,}")
        with b:
            st.metric("Rendered tracks", f"{len(paths):,}")

    # layers (PH first)
    layers: list[pdk.Layer] = []

    if map_mode == "Heatmap":
        layers.append(
            pdk.Layer(
                "HeatmapLayer",
                data=pts,
                get_position=["LON_PLOT", "LAT"],
                get_weight="weight",
                radius_pixels=35,
                intensity=1.2,
                threshold=0.05,
                pickable=False,
            )
        )

    elif map_mode == "Tracks (selected only)":
        layers.append(
            pdk.Layer(
                "PathLayer",
                data=paths,
                get_path="path",
                get_color="color",
                get_width=3,
                width_scale=1,
                width_min_pixels=2,
                pickable=True,
                auto_highlight=True,
            )
        )


    if par is not None:
        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                data=par,
                stroked=True,
                filled=False,
                get_line_color=[30, 30, 30, 130],
                line_width_min_pixels=1,
                pickable=False,
            )
        )

    layers.append(
        pdk.Layer(
            "PathLayer",
            data=paths,
            get_path="path",
            get_color="color",
            get_width=3,
            width_scale=1,
            width_min_pixels=2,
            pickable=True,
            auto_highlight=True,
        )
    )

    view = pdk.ViewState(latitude=12.5, longitude=122.5, zoom=4.5, pitch=0)

    tooltip = {
        "html": (
            "<b>SID:</b> {SID}<br/>"
            "<b>Year:</b> {start_year}<br/>"
            "<b>Intensity:</b> {peak_intensity}<br/>"
            "<b>Max wind:</b> {max_wind} kt<br/>"
            "<b>Track pts:</b> {n_track_points}"
        )
    }

    left, right = st.columns([2.6, 1.4])

    with left:
        st.subheader("Philippines + Tracks")
        st.pydeck_chart(
            pdk.Deck(layers=layers, initial_view_state=view, tooltip=tooltip, map_style=None),
            use_container_width=True,
        )
        st.caption("Colour: TD (grey), TS (blue), TY (orange), STY (red).")


    with right:
        st.subheader("Storms (filtered)")
        cols = [c for c in ["SID", "start_year", "peak_intensity", "max_wind", "n_track_points"] if c in storms_f.columns]
        st.dataframe(
            storms_f.sort_values(["start_year", "max_wind"], ascending=[True, False])[cols].head(300),
            height=650,
            use_container_width=True,
        )
