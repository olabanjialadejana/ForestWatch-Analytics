"""Plotly chart builders for the Streamlit dashboard."""

from __future__ import annotations

from typing import Iterable, Mapping

import pandas as pd

from app.utils.data_processing import time_series_to_dataframe


def annual_loss_bar_chart(rows: Iterable[Mapping[str, float]]):
    """Return a Plotly bar chart of annual forest loss in hectares."""
    import plotly.express as px

    df = time_series_to_dataframe(rows)
    fig = px.bar(
        df,
        x="year",
        y="loss_ha",
        title="Annual forest loss",
        labels={"year": "Year", "loss_ha": "Loss (ha)"},
        color_discrete_sequence=["#d62728"],
    )
    fig.update_layout(bargap=0.15, height=420)
    return fig


def cumulative_loss_line_chart(rows: Iterable[Mapping[str, float]]):
    """Return a Plotly line chart of cumulative forest loss in hectares."""
    import plotly.express as px

    df = time_series_to_dataframe(rows)
    fig = px.line(
        df,
        x="year",
        y="cumulative_ha",
        title="Cumulative forest loss",
        labels={"year": "Year", "cumulative_ha": "Cumulative loss (ha)"},
        markers=True,
        color_discrete_sequence=["#2ca02c"],
    )
    fig.update_layout(height=420)
    return fig


def cover_change_donut(summary: Mapping[str, float]):
    """Return a donut chart comparing 2000 cover vs. loss and gain."""
    import plotly.graph_objects as go

    labels = ["Remaining cover", "Loss", "Gain"]
    cover_2000 = float(summary.get("cover_2000", 0.0))
    loss = float(summary.get("loss", 0.0))
    gain = float(summary.get("gain", 0.0))
    remaining = max(cover_2000 - loss, 0.0)

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=[remaining, loss, gain],
                hole=0.55,
                marker=dict(colors=["#2ca02c", "#d62728", "#1f77b4"]),
            )
        ]
    )
    fig.update_layout(title="Tree cover composition (hectares)", height=420)
    return fig
