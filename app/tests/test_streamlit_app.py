"""Smoke test that the Streamlit dashboard script executes without errors."""

from __future__ import annotations

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402


def test_app_renders_landing_state():
    at = AppTest.from_file("app/main.py", default_timeout=30)
    at.run()

    # No uncaught exceptions while rendering.
    assert not list(at.exception), f"App raised: {list(at.exception)}"

    # Core UI pieces are present.
    titles = [t.value for t in at.title]
    assert "ForestWatch-Analytics" in titles

    sidebar_buttons = [b.label for b in at.sidebar.button]
    assert "Run analysis" in sidebar_buttons

    slider_labels = {s.label for s in at.sidebar.slider}
    assert "Tree cover threshold (%)" in slider_labels
    assert "Year range" in slider_labels

    # Landing state shows the upload prompt.
    info_messages = [i.value for i in at.info]
    assert any("Upload a GeoJSON" in msg for msg in info_messages)
