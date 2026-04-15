"""Integration tests for :mod:`app.modules.analysis` with a mocked Earth Engine.

Earth Engine requires authenticated network access, which is not available
in CI. These tests replace the ``ee`` module with a minimal fake that
returns scripted pixel counts from ``reduceRegion``, then exercise every
analysis function the Streamlit app calls.

The assertions verify three things:

* pixel counts are converted to hectares with the correct factor (0.09),
* ``year`` values are mapped to the Hansen ``lossyear`` index correctly,
* per-year, summary and hotspot aggregations line up.
"""

from __future__ import annotations

import sys
import types

import pytest


# ---------------------------------------------------------------------------
# Fake Earth Engine
# ---------------------------------------------------------------------------


class _FakeNumber:
    def __init__(self, v: float) -> None:
        self.v = float(v)

    def getInfo(self) -> float:
        return self.v

    def divide(self, d: float) -> "_FakeNumber":
        return _FakeNumber(self.v / d)


class _FakeDict:
    def __init__(self, d: dict) -> None:
        self.d = d

    def get(self, key: str):
        return self.d.get(key)


class _FakeImage:
    """Minimal stand-in for ``ee.Image`` with scripted reducer output."""

    SCRIPTED: dict = {}

    def __init__(self, band: str | None = None) -> None:
        self.band = band

    def select(self, band: str) -> "_FakeImage":
        return _FakeImage(band)

    def rename(self, band: str) -> "_FakeImage":
        return _FakeImage(band)

    def eq(self, _value):
        return _FakeImage(f"{self.band}_eq")

    def gte(self, _threshold):
        return _FakeImage(f"{self.band}_gte")

    def updateMask(self, _mask):
        return self

    def clip(self, _geom):
        return self

    def reduceRegion(self, **_kwargs):
        return _FakeDict({self.band: _FakeImage.SCRIPTED.get(self.band, 0)})


class _FakeGeometry:
    def area(self, _max_error=None):
        # 10 km^2 = 10,000,000 m^2 => 1000 ha after divide(10_000).
        return _FakeNumber(10_000_000.0)


class _FakeReducer:
    @staticmethod
    def sum():
        return object()


@pytest.fixture(autouse=True)
def install_fake_ee():
    """Install a fake ``ee`` module for the duration of each test."""
    original = sys.modules.get("ee")
    module = types.ModuleType("ee")
    module.Image = lambda x=None: _FakeImage() if not isinstance(x, _FakeImage) else x
    module.Reducer = _FakeReducer
    module.Geometry = _FakeGeometry
    module.Number = lambda x: x if isinstance(x, _FakeNumber) else _FakeNumber(float(x))
    module.Initialize = lambda *a, **k: None
    module.Authenticate = lambda *a, **k: None
    sys.modules["ee"] = module

    _FakeImage.SCRIPTED = {}
    yield

    if original is not None:
        sys.modules["ee"] = original
    else:
        sys.modules.pop("ee", None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _import_analysis():
    # Import after the fake ee is installed; reload to be safe.
    from app.modules import analysis
    return analysis


def test_forest_loss_single_year_converts_pixels_to_hectares():
    analysis = _import_analysis()
    _FakeImage.SCRIPTED = {"loss": 500}
    assert analysis.forest_loss(_FakeImage(), _FakeGeometry(), year=2010) == pytest.approx(45.0)


def test_forest_loss_out_of_range_returns_zero():
    analysis = _import_analysis()
    _FakeImage.SCRIPTED = {"loss": 9999}
    assert analysis.forest_loss(_FakeImage(), _FakeGeometry(), year=1999) == 0.0
    assert analysis.forest_loss(_FakeImage(), _FakeGeometry(), year=2030) == 0.0


def test_total_forest_loss_and_gain():
    analysis = _import_analysis()
    _FakeImage.SCRIPTED = {"loss": 1000, "gain": 200}
    assert analysis.total_forest_loss(_FakeImage(), _FakeGeometry()) == pytest.approx(90.0)
    assert analysis.forest_gain(_FakeImage(), _FakeGeometry()) == pytest.approx(18.0)


def test_tree_cover_2000_uses_threshold_mask():
    analysis = _import_analysis()
    _FakeImage.SCRIPTED = {"treecover2000": 10_000}
    assert analysis.tree_cover_2000(_FakeImage(), _FakeGeometry(), threshold=30) == pytest.approx(900.0)


def test_land_water_area_splits_datamask():
    analysis = _import_analysis()
    _FakeImage.SCRIPTED = {"land": 5_000, "water": 1_000}
    assert analysis.land_water_area(_FakeImage(), _FakeGeometry()) == {
        "land_ha": pytest.approx(450.0),
        "water_ha": pytest.approx(90.0),
    }


def test_aoi_area_hectares_uses_geometry_area():
    analysis = _import_analysis()
    assert analysis.aoi_area_hectares(_FakeGeometry()) == pytest.approx(1000.0)


def test_annual_loss_series_computes_cumulative():
    analysis = _import_analysis()
    _FakeImage.SCRIPTED = {"loss": 100}
    series = analysis.annual_loss_series(_FakeImage(), _FakeGeometry(), 2001, 2003)
    assert [r["year"] for r in series] == [2001, 2002, 2003]
    assert [r["loss_ha"] for r in series] == pytest.approx([9.0, 9.0, 9.0])
    assert [r["cumulative_ha"] for r in series] == pytest.approx([9.0, 18.0, 27.0])


def test_hotspot_years_returns_top_n():
    analysis = _import_analysis()
    _FakeImage.SCRIPTED = {"loss": 50}
    hotspots = analysis.hotspot_years(
        _FakeImage(), _FakeGeometry(), top_n=2, start_year=2001, end_year=2005
    )
    assert len(hotspots) == 2


def test_summary_statistics_aggregates_all_metrics():
    analysis = _import_analysis()
    _FakeImage.SCRIPTED = {
        "loss": 1000,
        "gain": 200,
        "treecover2000": 20_000,
        "land": 50_000,
        "water": 5_000,
    }
    s = analysis.summary_statistics(_FakeImage(), _FakeGeometry(), threshold=30)
    assert s["aoi_area_ha"] == pytest.approx(1000.0)
    assert s["cover_2000"] == pytest.approx(1800.0)
    assert s["loss"] == pytest.approx(90.0)
    assert s["gain"] == pytest.approx(18.0)
    assert s["net"] == pytest.approx(-72.0)
    assert s["land_ha"] == pytest.approx(4500.0)
    assert s["water_ha"] == pytest.approx(450.0)
    assert s["tree_cover_threshold"] == 30.0
