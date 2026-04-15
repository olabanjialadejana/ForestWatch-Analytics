"""Tests for reporting exports and chart builders."""

from __future__ import annotations

import csv
import io

import pytest

from app.modules.reporting import summary_to_csv, time_series_to_csv


SERIES = [
    {"year": 2001, "loss_ha": 1.0, "cumulative_ha": 1.0},
    {"year": 2002, "loss_ha": 2.5, "cumulative_ha": 3.5},
]

SUMMARY = {
    "aoi_area_ha": 123.456,
    "cover_2000": 80.0,
    "loss": 12.0,
    "gain": 3.0,
}


def test_time_series_to_csv_round_trip():
    data = time_series_to_csv(SERIES)
    assert isinstance(data, bytes)
    reader = csv.reader(io.StringIO(data.decode("utf-8")))
    rows = list(reader)
    assert rows[0] == ["year", "loss_ha", "cumulative_ha"]
    assert rows[1][0] == "2001"
    assert float(rows[2][2]) == pytest.approx(3.5)


def test_summary_to_csv_has_all_metrics():
    data = summary_to_csv(SUMMARY)
    decoded = data.decode("utf-8")
    for key in SUMMARY:
        assert key in decoded


def test_annual_loss_bar_chart_builds_figure():
    plotly = pytest.importorskip("plotly")
    from app.utils.visualization import annual_loss_bar_chart

    fig = annual_loss_bar_chart(SERIES)
    assert fig is not None
    assert len(fig.data) == 1
    assert list(fig.data[0].x) == [2001, 2002]


def test_cover_change_donut_builds_figure():
    plotly = pytest.importorskip("plotly")
    from app.utils.visualization import cover_change_donut

    fig = cover_change_donut(SUMMARY)
    assert fig is not None
    assert fig.data[0].values[1] == pytest.approx(SUMMARY["loss"])


def test_pdf_report_generates_bytes():
    pytest.importorskip("reportlab")
    from app.modules.reporting import build_pdf_report

    pdf = build_pdf_report(SUMMARY, SERIES, aoi_name="Sample")
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF")
