"""Export helpers for ForestWatch-Analytics.

The reporting layer turns the dictionaries produced by
:mod:`app.modules.analysis` into user-facing artefacts:

* CSV downloads (per-year time series, summary statistics).
* PDF summary reports rendered with ReportLab.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Dict, Iterable, List, Mapping


def time_series_to_csv(rows: Iterable[Mapping[str, float]]) -> bytes:
    """Serialise an annual-loss series as CSV bytes.

    Args:
        rows: Iterable of dicts with ``year``, ``loss_ha`` and
            ``cumulative_ha`` keys (the output of
            :func:`app.modules.analysis.annual_loss_series`).
    """
    rows = list(rows)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["year", "loss_ha", "cumulative_ha"])
    for row in rows:
        writer.writerow(
            [
                row.get("year"),
                f"{float(row.get('loss_ha', 0.0)):.4f}",
                f"{float(row.get('cumulative_ha', 0.0)):.4f}",
            ]
        )
    return buffer.getvalue().encode("utf-8")


def summary_to_csv(summary: Mapping[str, float]) -> bytes:
    """Serialise a summary stats dict as two-column CSV bytes."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["metric", "value"])
    for key, value in summary.items():
        if isinstance(value, float):
            writer.writerow([key, f"{value:.4f}"])
        else:
            writer.writerow([key, value])
    return buffer.getvalue().encode("utf-8")


def build_pdf_report(
    summary: Mapping[str, float],
    time_series: Iterable[Mapping[str, float]],
    *,
    aoi_name: str = "Area of Interest",
) -> bytes:
    """Render a short PDF summary report.

    ReportLab is imported lazily so unit tests that do not require PDFs can
    run without the dependency installed.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "reportlab is required to generate PDF reports"
        ) from exc

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="ForestWatch Report")
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("ForestWatch-Analytics Report", styles["Title"]))
    story.append(
        Paragraph(
            f"Area of interest: <b>{aoi_name}</b>", styles["Normal"]
        )
    )
    story.append(
        Paragraph(
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 18))

    story.append(Paragraph("Summary statistics", styles["Heading2"]))
    summary_rows: List[List[str]] = [["Metric", "Value"]]
    for key, value in summary.items():
        if isinstance(value, float):
            summary_rows.append([key, f"{value:,.2f}"])
        else:
            summary_rows.append([key, str(value)])
    summary_table = Table(summary_rows, hAlign="LEFT")
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f77b4")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 18))

    ts_rows: List[List[str]] = [["Year", "Loss (ha)", "Cumulative (ha)"]]
    for row in time_series:
        ts_rows.append(
            [
                str(row.get("year", "")),
                f"{float(row.get('loss_ha', 0.0)):,.2f}",
                f"{float(row.get('cumulative_ha', 0.0)):,.2f}",
            ]
        )
    if len(ts_rows) > 1:
        story.append(Paragraph("Annual forest loss", styles["Heading2"]))
        ts_table = Table(ts_rows, hAlign="LEFT")
        ts_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2ca02c")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ]
            )
        )
        story.append(ts_table)

    doc.build(story)
    return buffer.getvalue()
