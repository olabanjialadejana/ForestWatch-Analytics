"""Tests for :mod:`app.modules.geojson_upload`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("geopandas")

from app.modules.geojson_upload import (  # noqa: E402
    compute_area_hectares,
    estimate_utm_crs,
    handle_geojson_upload,
)


SAMPLE_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "sample"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [10.0, 10.0],
                        [10.1, 10.0],
                        [10.1, 10.1],
                        [10.0, 10.1],
                        [10.0, 10.0],
                    ]
                ],
            },
        }
    ],
}


@pytest.fixture
def geojson_path(tmp_path: Path) -> Path:
    path = tmp_path / "aoi.geojson"
    path.write_text(json.dumps(SAMPLE_GEOJSON))
    return path


def test_handle_geojson_upload_returns_wgs84(geojson_path: Path) -> None:
    gdf = handle_geojson_upload(str(geojson_path))
    assert gdf is not None
    assert gdf.crs is not None
    assert gdf.crs.to_string() == "EPSG:4326"
    assert len(gdf) == 1


def test_handle_geojson_upload_rejects_empty(tmp_path: Path) -> None:
    bad = tmp_path / "empty.geojson"
    bad.write_text(json.dumps({"type": "FeatureCollection", "features": []}))
    assert handle_geojson_upload(str(bad)) is None


def test_estimate_utm_crs_is_epsg_code(geojson_path: Path) -> None:
    gdf = handle_geojson_upload(str(geojson_path))
    utm = estimate_utm_crs(gdf)
    assert utm.startswith("EPSG:")
    # Our sample sits near the equator at longitude 10, zone 32 -> 32632.
    assert utm == "EPSG:32632"


def test_compute_area_hectares_is_positive(geojson_path: Path) -> None:
    gdf = handle_geojson_upload(str(geojson_path))
    area = compute_area_hectares(gdf)
    assert area > 0
    # ~11 km x 11 km ≈ 121 km² ≈ 12_100 ha at the equator.
    assert 10_000 < area < 14_000
