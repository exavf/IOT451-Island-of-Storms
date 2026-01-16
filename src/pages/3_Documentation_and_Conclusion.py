import streamlit as st

st.title("Documentation and Conclusions")
st.header("Overview Page – Documentation")

st.markdown("""
### Purpose
The Overview page introduces the dashboard and provides the context needed to interpret all subsequent analyses.
It defines the datasets used, key geographic concepts, and how storm intensity and counts should be understood.
""")

st.markdown("""
### Data Sources
- **IBTrACS (1950–2023):** Historical tropical cyclone tracks and storm summaries, including wind-based intensity.
- **ERA5 climate indices (annual):** Accessed via the **World Bank Group Climate Change Knowledge Portal** and merged into a single Philippines-wide dataset.
- **Geospatial boundaries:**
  - A **Philippine Area of Responsibility (PAR) polygon** used to identify storms entering the wider regional risk zone.
  - A **Philippines GeoJSON boundary** used to detect storms that make landfall.
""")

st.markdown("""
### Key Concepts
- **PAR entry** represents *exposure*: storms that pass through the wider regional area of responsibility.
- **Landfall** represents *impact*: storms that directly intersect the Philippine landmass.
- **Storm intensity** is measured using maximum sustained wind speed, providing a consistent metric across the historical record.
""")

st.markdown("### Metrics and Definitions")

st.latex(
r"""
\text{Severity shift}
=
(\text{TY} + \text{STY})_{\text{landfall}}
-
(\text{TY} + \text{STY})_{\text{PAR}},
\quad
"""
)
st.caption("Severity shift: difference in proportion of high-intensity storms (Typhoon + Super Typhoon) between landfalling storms and all PAR storms")

st.latex(r"""
R_y = \frac{N^{LF}_y}{N^{PAR}_y}
""")
st.caption("Landfall rate: proportion of PAR storms that make landfall")

st.latex(r"""
I_{\max}(s) = \max_{t \in s}(W_t)
""")
st.caption("Peak storm intensity, where W_t is maximum sustained wind speed")

st.latex(r"""
\text{Class}(s)=
\begin{cases}
TD & \text{if } I_{\max} < 34 \\
TS & \text{if } 34 \le I_{\max} < 64 \\
TY & \text{if } 64 \le I_{\max} < 130 \\
STY & \text{if } I_{\max} \ge 130
\end{cases}
""")
st.caption((
    "Wind-based storm intensity classification (knots): "
    "Tropical Depression (TD), Tropical Storm (TS), Typhoon (TY), Super Typhoon (STY)"
))

st.header("Visual Design")

with st.expander("Why these visuals were chosen"):

    st.subheader("Severity Shift (TY + STY Share)")
    st.markdown("""
    Severity shift condenses changes in storm intensity structure into a single interpretable metric.
    It complements the intensity distributions by quantifying differences that may be visually subtle
    but analytically meaningful.
    """)

    st.subheader("Intensity Distributions (PAR vs Landfall)")
    st.markdown("""
    Side-by-side intensity breakdowns enable direct comparison between exposure and impact subsets.
    Proportional charts are effective here because the number of categories is small and fixed.
    """)

    st.subheader("Time-Series by Intensity Class")
    st.markdown("""
    Time-series plots reveal long-term variability and clustering that summary statistics cannot capture.
    Separating lines by intensity class allows changes in storm composition to be observed over time.
    """)

    st.subheader("Interactive Controls")
    st.markdown("""
    Filters and toggles allow users to explore the data without duplicating static visuals.
    This supports both quick inspection and focused analysis while keeping the interface uncluttered.
    """)

st.divider() #### spatio temporal explorer

st.header("Spatio-Temporal Explorer – Documentation")

st.markdown("""
### Purpose
This page visualises how tropical cyclones move through space and time within the Philippine Area of Responsibility (PAR).
Instead of reducing storms to a single point, it preserves full trajectories to show approach paths, crossings, and exit routes.
""")

st.markdown("""
### Inputs
- **IBTrACS track points (1950–2023)** filtered to points inside the PAR polygon.
- **Philippines boundary GeoJSON** is used elsewhere for landfall classification, but this page focuses on PAR exposure.
- Each track point includes: storm ID (SID), timestamp, latitude, longitude, and wind-based intensity class.
""")

with st.expander("Why these visuals were chosen"):
    st.subheader("KPI Tiles (Storms, Heatmap Points)")
    st.markdown("""
    KPI tiles confirm what the user is actually looking at after filters are applied.
    They also act as a quick data-quality check (e.g., unexpectedly small counts usually means filters are too strict).
    """)

    st.subheader("Interactive Track Map")
    st.markdown("""
    Tracks preserve the storm lifecycle and show directional behaviour that yearly counts cannot capture.
    Colour-coding by intensity makes changes in severity visible along the path, not just at peak.
    """)

    st.subheader("Heatmap Overlay")
    st.markdown("""
    A heatmap reveals persistent corridors of exposure that are hard to see when many tracks overlap.
    It provides a spatial “where risk accumulates” view rather than a storm-by-storm narrative.
    """)

    st.subheader("Filtered Storm Table")
    st.markdown("""
    The table makes the map auditable: users can see exactly which storms are driving the visible patterns.
    It also supports reproducibility by exposing storm IDs and years for manual verification.
    """)

st.subheader("Heatmap Method (Conceptual)")

st.markdown("""
The heatmap shows where cyclone track points occur most frequently within the Philippine Area of Responsibility.
Each storm contributes multiple points along its path, so areas with more overlapping points appear hotter.
""")

st.latex(r"""
H(x, y) = \sum_{i=1}^{n} \mathbf{1}\big((x_i, y_i) \approx (x, y)\big)
""")

st.markdown("""
Here, \((x_i, y_i)\) are individual storm track points.
The heat value at a location increases as more track points fall nearby.

In practice, the heatmap applies smoothing so nearby points blend together visually.
Higher intensity therefore indicates regions that storms pass through more often under the selected filters.
""")

st.subheader("What to Interpret")

st.markdown("""
- **Tracks** show *how* storms move through PAR (routes, curvature, entry/exit behaviour).
- **Heat intensity** shows *where exposure accumulates* across many storms.
- Differences across year ranges can indicate shifts in storm corridors, not just changes in storm counts.
""")

st.divider() ### climate drivers

import streamlit as st

st.header("Climate Drivers – Documentation")

st.markdown("""
### Purpose
This page examines long-run rainfall variability and extremes over the Philippines using ERA5 data.
These background climate signals are then related to typhoon exposure (PAR) and landfall impact at annual scale.
""")

st.markdown("""
### Data
- **ERA5 annual climate indices** accessed via the **World Bank Group Climate Change Knowledge Portal**.
- Nine rainfall-related variables describing totals, extremes, persistence, and intensity.
- Data are aggregated at national (Philippines-wide) and annual resolution (1950–2023).
""")

with st.expander("Why these visuals were chosen"):
    st.subheader("Baseline Time-Series Plots")
    st.markdown("""
    Time-series plots reveal long-term variability, trends, and extremes in rainfall metrics.
    Overlaying a rolling mean highlights low-frequency behaviour without removing year-to-year variability.
    """)

    st.subheader("Rolling Mean Overlay")
    st.markdown("""
    A rolling mean reduces short-term noise while preserving multi-decadal structure.
    This helps distinguish persistent climate shifts from interannual variability.
    """)

    st.subheader("Correlation Heatmap")
    st.markdown("""
    The correlation heatmap provides a compact comparison across multiple climate drivers.
    It is used for exploratory screening of co-variation rather than causal inference.
    """)

    st.subheader("Dataset Toggle (PAR vs Landfall)")
    st.markdown("""
    Allowing users to switch between exposure and impact subsets tests whether climate relationships
    differ when focusing only on storms that directly affect the Philippines.
    """)

st.subheader("Climate Indices (Definitions)")

st.subheader("Rolling Mean")

st.latex(r"""
\overline{x}_t = \frac{1}{w} \sum_{i=t-w+1}^{t} x_i
""")

st.markdown("""
Where \(w\) is the rolling window length.
This smooths short-term variability to highlight longer-term behaviour.
""")

st.subheader("Correlation Method")

st.latex(r"""
r = \frac{\sum (x_i - \bar{x})(y_i - \bar{y})}
{\sqrt{\sum (x_i - \bar{x})^2 \sum (y_i - \bar{y})^2}}
""")

st.markdown("""
Pearson correlation coefficients quantify linear association between climate variables and
annual storm metrics. Values range from −1 (strong negative) to +1 (strong positive).

These correlations are exploratory and indicate co-variation, not causation.
""")

st.subheader("Interpretation Notes")

st.markdown("""
- Stronger correlations with extreme rainfall metrics (e.g. R50mm, Rx5day) suggest years with
  more storms also tend to experience more intense rainfall extremes.
- Weaker correlations with persistence metrics (e.g. CWD, CDD) indicate less direct linkage.
- Annual aggregation limits causal inference but supports robust long-term comparison.
""")

st.divider()

import streamlit as st

st.header("Conclusions and Reflection")

st.subheader("Conclusions")
st.markdown("""
This dashboard examined long-term typhoon exposure and rainfall extremes in the Philippines by separating storms that enter the Philippine Area of Responsibility from those that make landfall. This distinction matters. Many storms pass through the region, but only a subset translate into direct national impact, and that subset shows a different intensity profile.

Spatio-temporal analysis reveals persistent storm corridors rather than uniform risk, while climate driver analysis suggests that years with more storms tend to coincide with stronger rainfall extremes. These relationships are exploratory, not causal, but they provide important context for understanding how typhoon activity and rainfall extremes vary together over time.
""")

st.subheader("Reflection")
st.markdown("""
Having survived Super Typhoon Haiyan in 2013, this project holds personal meaning. As a child, typhoons felt sudden and isolated. Working with decades of data reframed that experience, placing individual events within longer patterns of exposure, recurrence, and variability.

The project also highlighted that effective time and scope management is an area of ongoing development. Forecasting models were initially planned but were removed due to limited time available for proper implementation and validation. This resulted in a narrower scope and a focus on descriptive analysis, reinforcing the importance of realistic planning and prioritisation in future work.
""")

st.markdown("""
With the project, I acquired hands-on experience with large typhoon and climate datasets. I was able to learn about the process of preparing and merging IBTrACS cyclone datasets, applying polygon filters, and incorporating ERA5 climate datasets from the World Bank Group Climate Change Knowledge Portal. I was also able to work with GeoJSON datasets, create data workflows, and visualize complex datasets.

These skills provide a good foundation for me to develop from. In the future, my aim is to enhance the dashboard with more accurate time data and sophisticated analysis, beginning with the current typhoon and climate data streams. This project helped to further develop my passion for data analysis and geospatial applications in real-world climate risk and disaster responses.
""")
