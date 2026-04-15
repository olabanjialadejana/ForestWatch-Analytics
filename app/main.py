"""Streamlit entry point for the ForestWatch-Analytics dashboard.

Run locally with::

    streamlit run app/main.py

The app lets a user upload a GeoJSON area of interest, authenticates with
Google Earth Engine, clips the Hansen Global Forest Change dataset to the
AOI, and renders interactive charts, maps and downloadable reports.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from app.modules.analysis import (
    HANSEN_END_YEAR,
    annual_loss_series,
    hotspot_years,
    summary_statistics,
)
from app.modules.forest_data import authenticate_and_initialize, get_clipped_forest
from app.modules.geojson_upload import compute_area_hectares, handle_geojson_upload
from app.modules.map_interaction import build_map, simple_aoi_map
from app.modules.reporting import (
    build_pdf_report,
    summary_to_csv,
    time_series_to_csv,
)
from app.utils.data_processing import summary_to_dataframe, time_series_to_dataframe
from app.utils.file_validation import validate_upload
from app.utils.visualization import (
    annual_loss_bar_chart,
    cover_change_donut,
    cumulative_loss_line_chart,
)


st.set_page_config(
    page_title="ForestWatch-Analytics",
    page_icon="🌳",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _persist_upload(uploaded_file) -> Path:
    """Write a Streamlit upload to a temp file and return its path."""
    suffix = Path(uploaded_file.name).suffix or ".geojson"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getvalue())
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


def _render_sidebar():
    st.sidebar.title("🌳 ForestWatch-Analytics")
    st.sidebar.markdown(
        "Upload a GeoJSON describing your area of interest (AOI) and "
        "explore forest change derived from the Hansen Global Forest "
        "Change v1.11 dataset (2000\u20132023)."
    )

    st.sidebar.header("1. Upload AOI")
    uploaded = st.sidebar.file_uploader(
        "GeoJSON file",
        type=["geojson", "json"],
        help="Your GeoJSON is expected in WGS84 (EPSG:4326).",
    )

    st.sidebar.header("2. Analysis settings")
    threshold = st.sidebar.slider(
        "Tree cover threshold (%)",
        min_value=0,
        max_value=100,
        value=30,
        step=5,
        help="Minimum canopy cover to count a pixel as forest in the year 2000.",
    )
    start_year, end_year = st.sidebar.slider(
        "Year range",
        min_value=2001,
        max_value=HANSEN_END_YEAR,
        value=(2001, HANSEN_END_YEAR),
    )

    st.sidebar.header("3. Earth Engine")
    gee_project = st.sidebar.text_input(
        "Cloud project (optional)",
        help="Required on recent EE accounts. Leave blank to use the default.",
    )
    run = st.sidebar.button("Run analysis", type="primary", use_container_width=True)

    return {
        "uploaded": uploaded,
        "threshold": threshold,
        "start_year": start_year,
        "end_year": end_year,
        "project": gee_project.strip() or None,
        "run": run,
    }


def _render_header():
    st.title("ForestWatch-Analytics")
    st.caption(
        "Monitor forest cover change on any area of interest using the "
        "Hansen Global Forest Change dataset."
    )


def _render_aoi_preview(gdf):
    area_ha = compute_area_hectares(gdf)
    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("AOI area", f"{area_ha:,.1f} ha")
        st.metric("Features", f"{len(gdf):,}")
    with col2:
        from streamlit_folium import st_folium

        preview = simple_aoi_map(gdf)
        st_folium(preview, height=320, width=None, returned_objects=[])


def _render_results(
    summary,
    series,
    hotspots,
    gdf,
    forest_image,
    aoi_name: str,
):
    from streamlit_folium import st_folium

    st.subheader("Key metrics")
    cols = st.columns(4)
    cols[0].metric("AOI area", f"{summary['aoi_area_ha']:,.1f} ha")
    cols[1].metric(
        f"Tree cover 2000 (\u2265{int(summary['tree_cover_threshold'])}%)",
        f"{summary['cover_2000']:,.1f} ha",
    )
    cols[2].metric("Total loss 2001\u20132023", f"{summary['loss']:,.1f} ha")
    cols[3].metric("Total gain 2000\u20132012", f"{summary['gain']:,.1f} ha")

    st.subheader("Interactive map")
    fmap = build_map(
        gdf,
        forest_image=forest_image,
        show_tree_cover=True,
        show_loss=True,
        show_loss_year=True,
        show_gain=True,
    )
    st_folium(fmap, height=500, width=None, returned_objects=[])

    st.subheader("Annual forest loss")
    chart_col, donut_col = st.columns([2, 1])
    with chart_col:
        st.plotly_chart(annual_loss_bar_chart(series), use_container_width=True)
    with donut_col:
        st.plotly_chart(cover_change_donut(summary), use_container_width=True)

    st.plotly_chart(cumulative_loss_line_chart(series), use_container_width=True)

    st.subheader("Top loss years")
    if hotspots:
        st.table(
            [
                {"Year": row["year"], "Loss (ha)": f"{row['loss_ha']:,.1f}"}
                for row in hotspots
            ]
        )
    else:
        st.info("No loss recorded in the selected year range.")

    st.subheader("Raw tables")
    tab_series, tab_summary = st.tabs(["Annual series", "Summary"])
    with tab_series:
        st.dataframe(time_series_to_dataframe(series), use_container_width=True)
    with tab_summary:
        st.dataframe(summary_to_dataframe(summary), use_container_width=True)

    st.subheader("Export")
    d1, d2, d3 = st.columns(3)
    d1.download_button(
        "Download time series (CSV)",
        data=time_series_to_csv(series),
        file_name="forestwatch_time_series.csv",
        mime="text/csv",
    )
    d2.download_button(
        "Download summary (CSV)",
        data=summary_to_csv(summary),
        file_name="forestwatch_summary.csv",
        mime="text/csv",
    )
    try:
        pdf_bytes = build_pdf_report(summary, series, aoi_name=aoi_name)
        d3.download_button(
            "Download PDF report",
            data=pdf_bytes,
            file_name="forestwatch_report.pdf",
            mime="application/pdf",
        )
    except RuntimeError as exc:
        d3.info(str(exc))


def main() -> None:
    _render_header()
    controls = _render_sidebar()

    uploaded = controls["uploaded"]
    if uploaded is None:
        st.info(
            "\ud83d\udc48 Upload a GeoJSON file in the sidebar to get started. "
            "The dashboard will validate your AOI and preview it on a map."
        )
        return

    ok, message = validate_upload(uploaded)
    if not ok:
        st.error(message)
        return

    path = _persist_upload(uploaded)
    gdf = handle_geojson_upload(str(path))
    if gdf is None:
        st.error(
            "The uploaded file could not be read as valid GeoJSON. Please "
            "check the geometry and try again."
        )
        return

    st.success(f"Loaded AOI with {len(gdf)} feature(s).")
    _render_aoi_preview(gdf)

    if not controls["run"]:
        st.caption(
            "Click **Run analysis** in the sidebar to query Google Earth "
            "Engine and generate the full report."
        )
        return

    with st.spinner("Authenticating with Google Earth Engine\u2026"):
        if not authenticate_and_initialize(project=controls["project"]):
            st.error(
                "Could not initialise Earth Engine. Make sure you have run "
                "`earthengine authenticate` and (if required) provided a "
                "Cloud project ID in the sidebar."
            )
            return

    with st.spinner("Clipping Hansen dataset to AOI\u2026"):
        forest_image, geometry = get_clipped_forest(
            str(path), project=controls["project"]
        )

    if forest_image is None or geometry is None:
        st.error("Failed to prepare Earth Engine imagery for this AOI.")
        return

    with st.spinner("Computing summary statistics\u2026"):
        summary = summary_statistics(
            forest_image, geometry, threshold=controls["threshold"]
        )

    with st.spinner("Building annual time series\u2026"):
        series = annual_loss_series(
            forest_image,
            geometry,
            start_year=controls["start_year"],
            end_year=controls["end_year"],
        )
        hotspots = hotspot_years(
            forest_image,
            geometry,
            top_n=3,
            start_year=controls["start_year"],
            end_year=controls["end_year"],
        )

    _render_results(
        summary=summary,
        series=series,
        hotspots=hotspots,
        gdf=gdf,
        forest_image=forest_image,
        aoi_name=uploaded.name,
    )


if __name__ == "__main__":
    main()
