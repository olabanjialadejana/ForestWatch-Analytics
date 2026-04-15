"""GeoJSON upload and validation utilities.

The Hansen Global Forest Change dataset on Google Earth Engine expects
geometries in geographic coordinates (EPSG:4326). This module loads a
user-supplied GeoJSON file, validates it, and returns a GeoDataFrame in
WGS84 that can be passed to GEE.
"""

from __future__ import annotations

from typing import Optional, Union

import geopandas as gpd
import pyproj
from shapely.geometry import shape
from shapely.validation import make_valid

WGS84 = "EPSG:4326"


def handle_geojson_upload(uploaded_file) -> Optional[gpd.GeoDataFrame]:
    """Load a GeoJSON file into a validated WGS84 GeoDataFrame.

    Args:
        uploaded_file: Path to a GeoJSON file or a file-like object (e.g.
            a Streamlit ``UploadedFile``).

    Returns:
        A GeoDataFrame in EPSG:4326 containing valid geometries, or ``None``
        if the file is empty or invalid.
    """
    try:
        gdf = gpd.read_file(uploaded_file)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Invalid GeoJSON file: {exc}")
        return None

    if gdf.empty:
        print("Error: The GeoJSON file is empty.")
        return None

    if "geometry" not in gdf.columns or gdf.geometry.is_empty.all():
        print("Error: No valid geometries found in the GeoJSON file.")
        return None

    # Attempt to repair any invalid geometries rather than rejecting outright.
    invalid_mask = ~gdf.geometry.is_valid
    if invalid_mask.any():
        gdf.loc[invalid_mask, "geometry"] = gdf.loc[invalid_mask, "geometry"].apply(
            make_valid
        )

    # Ensure a CRS is set; default to WGS84 when absent (common for raw GeoJSON).
    if gdf.crs is None:
        gdf = gdf.set_crs(WGS84)

    # Earth Engine expects geographic coordinates.
    if gdf.crs.to_string() != WGS84:
        gdf = gdf.to_crs(WGS84)

    return gdf


def estimate_utm_crs(gdf: gpd.GeoDataFrame) -> str:
    """Pick an appropriate UTM CRS for area calculations.

    Args:
        gdf: A GeoDataFrame (any CRS).

    Returns:
        An EPSG code string such as ``"EPSG:32633"``.
    """
    if gdf.crs is None:
        gdf = gdf.set_crs(WGS84)

    # Compute a geographic centroid without triggering the "centroid in
    # geographic CRS" warning by projecting first.
    mercator = gdf.to_crs("EPSG:3857")
    centroid = mercator.geometry.union_all().centroid
    transformer = pyproj.Transformer.from_crs("EPSG:3857", WGS84, always_xy=True)
    lon, lat = transformer.transform(centroid.x, centroid.y)

    zone = int((lon + 180) // 6) + 1
    epsg = 32600 + zone if lat >= 0 else 32700 + zone
    return f"EPSG:{epsg}"


def compute_area_hectares(gdf: gpd.GeoDataFrame) -> float:
    """Return the total area of the GeoDataFrame in hectares (UTM-based)."""
    utm = estimate_utm_crs(gdf)
    projected = gdf.to_crs(utm)
    return float(projected.geometry.area.sum() / 10_000.0)


def convert_uploaded_file_to_ee_geometry(
    uploaded_file, simplify_tolerance: float = 0.001
):
    """Convert an uploaded GeoJSON file into an Earth Engine geometry.

    Args:
        uploaded_file: Path or file-like object for the user's GeoJSON.
        simplify_tolerance: Douglas-Peucker tolerance in degrees used to
            reduce vertex count before sending to Earth Engine.

    Returns:
        An ``ee.Geometry`` object, or ``None`` if conversion fails.
    """
    gdf = handle_geojson_upload(uploaded_file)
    if gdf is None:
        return None

    gdf = gdf.copy()
    gdf["geometry"] = gdf["geometry"].simplify(
        tolerance=simplify_tolerance, preserve_topology=True
    )

    try:
        import geemap  # imported lazily so tests can run without GEE installed
    except ImportError as exc:  # pragma: no cover
        print(f"geemap is required for EE conversion: {exc}")
        return None

    try:
        return geemap.gdf_to_ee(gdf).geometry()
    except Exception as exc:  # pragma: no cover - depends on GEE auth
        print(f"Error converting GeoDataFrame to ee.Geometry: {exc}")
        return None
