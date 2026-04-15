"""Small pandas-based helpers for post-processing analytics output."""

from __future__ import annotations

from typing import Iterable, Mapping

import pandas as pd


def time_series_to_dataframe(rows: Iterable[Mapping[str, float]]) -> pd.DataFrame:
    """Convert an annual-loss series into a tidy DataFrame.

    Returns columns ``year``, ``loss_ha`` and ``cumulative_ha``. An empty
    DataFrame with the expected schema is returned when ``rows`` is empty.
    """
    df = pd.DataFrame(list(rows))
    expected = ["year", "loss_ha", "cumulative_ha"]
    if df.empty:
        return pd.DataFrame(columns=expected)
    for col in expected:
        if col not in df.columns:
            df[col] = 0.0
    df = df[expected].copy()
    df["year"] = df["year"].astype(int)
    df["loss_ha"] = df["loss_ha"].astype(float)
    df["cumulative_ha"] = df["cumulative_ha"].astype(float)
    return df.sort_values("year").reset_index(drop=True)


def summary_to_dataframe(summary: Mapping[str, float]) -> pd.DataFrame:
    """Convert a summary dict into a two-column DataFrame for display."""
    return pd.DataFrame(
        [{"metric": key, "value": value} for key, value in summary.items()]
    )


def percentage_change(before: float, after: float) -> float:
    """Return the percentage change from ``before`` to ``after``.

    Returns ``0.0`` when ``before`` is zero to avoid division errors.
    """
    if before == 0:
        return 0.0
    return (after - before) / before * 100.0
