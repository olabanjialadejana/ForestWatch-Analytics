"""Tests for :mod:`app.utils.data_processing` and file validation."""

from __future__ import annotations

import json

import pytest

from app.utils.data_processing import (
    percentage_change,
    summary_to_dataframe,
    time_series_to_dataframe,
)
from app.utils.file_validation import is_valid_geojson_bytes, validate_upload


def test_time_series_to_dataframe_empty_input():
    df = time_series_to_dataframe([])
    assert list(df.columns) == ["year", "loss_ha", "cumulative_ha"]
    assert len(df) == 0


def test_time_series_to_dataframe_sorts_and_types():
    rows = [
        {"year": 2003, "loss_ha": 2.5, "cumulative_ha": 6.0},
        {"year": 2001, "loss_ha": 1.0, "cumulative_ha": 1.0},
        {"year": 2002, "loss_ha": 2.5, "cumulative_ha": 3.5},
    ]
    df = time_series_to_dataframe(rows)
    assert list(df["year"]) == [2001, 2002, 2003]
    assert df["loss_ha"].dtype.kind == "f"
    assert df["cumulative_ha"].iloc[-1] == pytest.approx(6.0)


def test_summary_to_dataframe_roundtrip():
    summary = {"aoi_area_ha": 100.0, "loss": 25.0}
    df = summary_to_dataframe(summary)
    assert set(df.columns) == {"metric", "value"}
    assert set(df["metric"]) == {"aoi_area_ha", "loss"}


def test_percentage_change_handles_zero():
    assert percentage_change(0, 10) == 0.0
    assert percentage_change(100, 80) == pytest.approx(-20.0)


def test_validate_upload_rejects_none():
    ok, message = validate_upload(None)
    assert not ok and message


def test_validate_upload_rejects_bad_extension(tmp_path):
    bogus = tmp_path / "not_geojson.txt"
    bogus.write_text("nope")
    ok, message = validate_upload(str(bogus))
    assert not ok and "Unsupported" in message


def test_validate_upload_accepts_geojson(tmp_path):
    good = tmp_path / "aoi.geojson"
    good.write_text('{"type": "FeatureCollection", "features": []}')
    ok, message = validate_upload(str(good))
    assert ok and message == ""


def test_is_valid_geojson_bytes_accepts_feature_collection():
    payload = json.dumps(
        {"type": "FeatureCollection", "features": []}
    ).encode("utf-8")
    assert is_valid_geojson_bytes(payload)


def test_is_valid_geojson_bytes_rejects_garbage():
    assert not is_valid_geojson_bytes(b"not-json")
    assert not is_valid_geojson_bytes(b'{"type": "Unknown"}')
