import pandas as pd
import streamlit as st


def _normalise_intensity(series: pd.Series) -> pd.Series:
    # just making sure labels like "ty " become "TY"
    return series.astype(str).str.upper().str.strip()


def _count_classes(df: pd.DataFrame, intensity_col: str) -> tuple[dict, dict, float]:
    # count how many storms fall into each intensity bucket
    classes = ["TD", "TS", "TY", "STY"]
    counts = {c: int((df[intensity_col] == c).sum()) for c in classes}

    total = int(df.shape[0])
    props = {c: (counts[c] / total * 100.0) if total else 0.0 for c in classes}

    # TY + STY share = “stronger storms”
    high_share = ((counts["TY"] + counts["STY"]) / total * 100.0) if total else 0.0
    return counts, props, high_share


def _class_row(counts: dict, highlight_red: bool = False) -> None:
    # lightweight “kpi tiles” using HTML so Streamlit spacing doesn’t look weird
    cols = st.columns(4)
    labels = ["TD", "TS", "TY", "STY"]

    for i, lab in enumerate(labels):
        with cols[i]:
            colour = "#ff4d4f" if highlight_red and lab == "STY" else "black"

            st.markdown(
                f"""
                <div style="line-height:1.0; margin-top:0.25rem;">
                  <div style="font-weight:300; font-size:1.1rem; margin-bottom:0.2rem;">{lab}</div>
                  <div style="font-weight:300; font-size:3.0rem; color:{colour}; margin:0;">{counts[lab]:,}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _intensity_pie(counts: dict) -> None:
    # pie chart for the composition (helps show “mix” not just totals)
    import matplotlib.pyplot as plt

    labels = ["TD", "TS", "TY", "STY"]
    values = [counts[l] for l in labels]

    # simple intensity gradient colours (cool -> hot)
    colours = ["#4C78A8", "#59A14F", "#F28E2B", "#E15759"]

    fig, ax = plt.subplots()
    ax.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        colors=colours,
    )
    ax.axis("equal")
    st.pyplot(fig)

def render_intensity_frequency_timeseries(par_df: pd.DataFrame, landfall_df: pd.DataFrame) -> None:
    """
    Interactive line chart: annual frequency by intensity class.
    - User can switch between PAR (exposure) and Landfall (impact)
    - User can select year range
    - Lines are coloured by intensity class (Altair default palette)
    """
    import altair as alt  # lazy import so pages stay light

    st.subheader("Annual frequency by intensity class")

    # Choose dataset (exposure vs impact)
    mode = st.radio(
        "View:",
        ["PAR entries (exposure)", "Philippine landfall (impact)"],
        horizontal=True,
    )

    if mode == "PAR entries (exposure)":
        df = par_df.copy()
        year_col = "start_year"
        intensity_col = "par_peak_intensity"
    else:
        df = landfall_df.copy()

        # landfall intensity preferred; fallback to peak intensity if needed
        intensity_col = "landfall_intensity" if "landfall_intensity" in df.columns else "peak_intensity"

        # if your v4 has any_landfall, filter to True
        if "any_landfall" in df.columns:
            df = df[df["any_landfall"] == True].copy()

        # v4 should ideally have start_year; if not, derive from first_landfall_time
        if "start_year" in df.columns:
            year_col = "start_year"
        elif "first_landfall_time" in df.columns:
            df["first_landfall_time"] = pd.to_datetime(df["first_landfall_time"], errors="coerce")
            df["start_year"] = df["first_landfall_time"].dt.year
            year_col = "start_year"
        else:
            st.error("Landfall dataset needs 'start_year' or 'first_landfall_time' to plot a yearly time series.")
            return

    # Clean columns
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
    df = df.dropna(subset=[year_col])
    df[year_col] = df[year_col].astype(int)

    df[intensity_col] = df[intensity_col].astype(str).str.upper().str.strip()
    df = df[df[intensity_col].isin(["TD", "TS", "TY", "STY"])]

    if df.empty:
        st.warning("No rows available after filtering. Check intensity labels and year column.")
        return

    # Year range selector
    min_year, max_year = int(df[year_col].min()), int(df[year_col].max())
    year_range = st.slider("Year range", min_year, max_year, (min_year, max_year), step=1)

    df = df[(df[year_col] >= year_range[0]) & (df[year_col] <= year_range[1])]

    # Aggregate annual counts by class
    ts = (
        df.groupby([year_col, intensity_col])
        .size()
        .reset_index(name="storm_count")
        .rename(columns={year_col: "year", intensity_col: "intensity"})
        .sort_values("year")
    )

    # Optional: let user choose which lines to show
    selected = st.multiselect(
        "Intensity classes",
        ["TD", "TS", "TY", "STY"],
        default=["TD", "TS", "TY", "STY"],
    )
    ts = ts[ts["intensity"].isin(selected)]

    if ts.empty:
        st.warning("No data for the selected classes/year range.")
        return

    chart = (
        alt.Chart(ts)
        .mark_line(point=False)
        .encode(
            x=alt.X("year:Q", title="Year"),
            y=alt.Y("storm_count:Q", title="Storm count"),
            color=alt.Color("intensity:N", title="Intensity class"),  # different colours automatically
            tooltip=["year:Q", "intensity:N", "storm_count:Q"],
        )
        .properties(height=320)
        .interactive()
    )

    st.altair_chart(chart, use_container_width=True)

    st.caption(
        "Counts are based on one row per storm in the selected dataset. "
        "PAR uses intensity reached within PAR; landfall uses intensity at first Philippine landfall."
    )

    st.markdown("#### How to interpret this section")
    st.write(
        "- **Conversion rate**: fraction of PAR-entering storms that made Philippine landfall.\n"
        "- **Severity shift**: how the TY+STY share changes when restricting to landfall storms.\n"
        "- Differences are expected because landfall is a smaller subset shaped by track + intensity evolution."
    )

    st.markdown("#### Why this matters")
    st.write(
        "Separating **exposure** (storms that enter PAR) from **impact** (storms that make landfall) helps avoid misleading conclusions. "
        "For example, storm counts within PAR can change without the same change being felt on the ground in the Philippines. "
        "This dashboard treats landfall as the subset that is most relevant for real-world disruption, while PAR captures the broader risk environment."
    )

    st.divider()

    st.subheader("Evidence from literature")
    st.markdown(
        """
        Recent research shows that tropical cyclone impacts in the Philippines can intensify even when storm counts
        within PAR decline, highlighting the need to distinguish between **exposure** and **impact**.

        **Reference:**  
        Basconcillo, J. and Bangquiao, N. (2025), Recent increase in the number of Super Typhoons in the Philippines
        https://www.sciencedirect.com/science/article/pii/S2225603225000402
        """
    )
    with st.expander("Data provenance notes"):
        st.write(
            "- **IBTrACS v3 (within PAR):** Storm-level summaries for all tropical cyclones entering PAR, "
            "including `par_peak_intensity`, used to characterise regional exposure.\n"
            "- **IBTrACS v4 (landfall):** Subset of storms that made Philippine landfall, "
            "including `landfall_intensity`, used to capture realised national impact.\n"
            "- **ERA5 climate indices:** Nine precipitation and extreme-rainfall variables used later in the "
            "dashboard to explore links between storm behaviour and hydro-climatic extremes."
        )


def render_overview_exposure_vs_impact(par_df: pd.DataFrame, landfall_df: pd.DataFrame) -> None:
    # sanity checks so we don’t render nonsense if files change
    required_par = {"SID", "start_year", "par_peak_intensity"}
    if not required_par.issubset(par_df.columns):
        st.error(f"PAR (v3) missing: {sorted(required_par - set(par_df.columns))}")
        st.write("PAR columns:", list(par_df.columns))
        st.stop()

    if "landfall_intensity" not in landfall_df.columns and "peak_intensity" not in landfall_df.columns:
        st.error("Landfall (v4) needs landfall_intensity or peak_intensity.")
        st.write("Landfall columns:", list(landfall_df.columns))
        st.stop()

    # prefer landfall intensity if present, otherwise fallback
    land_intensity_col = "landfall_intensity" if "landfall_intensity" in landfall_df.columns else "peak_intensity"

    par = par_df.copy()
    land = landfall_df.copy()

    par["par_peak_intensity"] = _normalise_intensity(par["par_peak_intensity"])
    par["start_year"] = pd.to_numeric(par["start_year"], errors="coerce")
    land[land_intensity_col] = _normalise_intensity(land[land_intensity_col])

    # defensive filter (some versions might keep non-landfall rows)
    if "any_landfall" in land.columns:
        land = land[land["any_landfall"] == True].copy()

    # if SID is missing, we assume one row per storm (not ideal but ok)
    land_has_sid = "SID" in land.columns
    if not land_has_sid:
        st.warning("Landfall file has no SID column; assuming one row = one storm.")
        land = land.reset_index().rename(columns={"index": "ROW_ID"})

    par_total = int(par["SID"].nunique())
    land_total = int(land["SID"].nunique()) if land_has_sid else int(land.shape[0])
    conversion_rate = (land_total / par_total * 100.0) if par_total else 0.0

    # PAR defines the coverage window
    years = par["start_year"].dropna()
    start_year = int(years.min()) if not years.empty else None
    end_year = int(years.max()) if not years.empty else None

    # intensity composition for both subsets
    par_counts, par_props, par_high_share = _count_classes(par, "par_peak_intensity")
    land_counts, land_props, land_high_share = _count_classes(land, land_intensity_col)

    # difference in strong-storm share, in percentage points
    severity_shift_pp = land_high_share - par_high_share

    st.subheader("Exposure vs Impact")
    st.write(
        "PAR storms represent **exposure** (systems that entered the Philippine Area of Responsibility). "
        "Landfall storms represent **direct impact** (systems that crossed the Philippine coastline). "
        "Because storms can recurve or weaken before land, the landfall subset is smaller and can show a different severity profile."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Storms entering PAR (v3)", f"{par_total:,}")
    c2.metric("Storms making PH landfall (v4)", f"{land_total:,}")
    c3.metric("Landfall conversion rate", f"{conversion_rate:.1f}%")
    c4.metric("Severity shift (TY+STY share)", f"{severity_shift_pp:+.1f} pp")

    st.caption(
        "A negative severity shift value means fewer high-intensity storms in the landfall subset."
    )

    if start_year is not None and end_year is not None:
        st.caption(f"Coverage shown here: {start_year}–{end_year} (PAR dataset defines the study window).")

    st.divider()

    left, right = st.columns(2)

    with left:
        st.markdown("### Intensity within PAR")
        st.caption("par_peak_intensity (maximum intensity while inside PAR)")
        st.write(
            "Each storm is counted once and classified by its **strongest intensity while inside PAR**. "
            "This captures storms that posed a threat to the Philippines, even if they did not make landfall."
        )
        _class_row(par_counts)

    with right:
        st.markdown("### Intensity at landfall")
        st.caption(f"{land_intensity_col} (intensity at first Philippine landfall)")
        st.write(
            "This is a **subset** of PAR storms: only storms that crossed the coastline. "
            "Intensity at landfall can differ because storms often **weaken near land** or change track before landfall."
        )
        _class_row(land_counts, highlight_red=True)

    # composition comparison (mix of TD/TS/TY/STY)
    p1, p2 = st.columns(2)
    with p1:
        _intensity_pie(par_counts)
    with p2:
        _intensity_pie(land_counts)

    st.caption(
        "Storms are grouped by wind-based intensity (in knots):\n"
        "- **TD (Tropical Depression):** < 34 kt\n"
        "- **TS (Tropical Storm):** 34–63 kt\n"
        "- **TY (Typhoon):** 64–129 kt\n"
        "- **STY (Super Typhoon):** ≥ 130 kt\n\n"
        "In this dashboard, the PAR panel uses the strongest intensity reached **while inside PAR**, "
        "and the landfall panel uses intensity **at first Philippine landfall**."
    )

