"""Lightweight validation helpers for user uploads."""

from __future__ import annotations

import json
import os
from typing import Tuple

ALLOWED_EXTENSIONS = {".geojson", ".json"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


def _extension(name: str) -> str:
    return os.path.splitext(name)[1].lower()


def validate_upload(uploaded_file) -> Tuple[bool, str]:
    """Perform cheap sanity checks on a Streamlit upload (or path).

    Args:
        uploaded_file: A Streamlit ``UploadedFile`` or a filesystem path.

    Returns:
        ``(ok, message)``. On success ``message`` is empty.
    """
    if uploaded_file is None:
        return False, "No file provided."

    name = getattr(uploaded_file, "name", None) or str(uploaded_file)
    if _extension(name) not in ALLOWED_EXTENSIONS:
        return False, (
            "Unsupported file type. Please upload a .geojson or .json file."
        )

    size = getattr(uploaded_file, "size", None)
    if size is None and isinstance(uploaded_file, str) and os.path.exists(uploaded_file):
        size = os.path.getsize(uploaded_file)
    if size is not None and size > MAX_UPLOAD_BYTES:
        return False, (
            f"File too large ({size / 1_000_000:.1f} MB). "
            f"Maximum is {MAX_UPLOAD_BYTES // 1_000_000} MB."
        )

    return True, ""


def is_valid_geojson_bytes(data: bytes) -> bool:
    """Return ``True`` when ``data`` decodes as a minimally valid GeoJSON payload."""
    try:
        parsed = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False

    if not isinstance(parsed, dict):
        return False

    obj_type = parsed.get("type")
    if obj_type == "FeatureCollection":
        return isinstance(parsed.get("features"), list)
    if obj_type == "Feature":
        return "geometry" in parsed
    return obj_type in {
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
        "GeometryCollection",
    }
