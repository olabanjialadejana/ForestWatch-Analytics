"""Earth Engine data access for the Hansen Global Forest Change dataset."""

from __future__ import annotations

from typing import Optional

from app.modules.geojson_upload import (
    convert_uploaded_file_to_ee_geometry,
    handle_geojson_upload,
)

FOREST_WATCH = "UMD/hansen/global_forest_change_2023_v1_11"

# Band names for the Hansen dataset.
TREE_COVER_2000 = "treecover2000"
LOSS = "loss"
LOSS_YEAR = "lossyear"
GAIN = "gain"
DATAMASK = "datamask"
FIRST = "first"
LAST = "last"


_EE_INITIALIZED = False


def authenticate_and_initialize(project: Optional[str] = None) -> bool:
    """Initialise the Earth Engine Python client.

    Tries, in order:

    1. A previously-initialised session (no-op).
    2. ``ee.Initialize()`` using an existing token.
    3. Refreshing default Google credentials.
    4. Triggering ``ee.Authenticate()`` for interactive login.

    Args:
        project: Optional Google Cloud project ID to bind the session to.

    Returns:
        ``True`` if Earth Engine is ready to use, otherwise ``False``.
    """
    global _EE_INITIALIZED
    if _EE_INITIALIZED:
        return True

    try:
        import ee
    except ImportError as exc:
        print(f"earthengine-api not installed: {exc}")
        return False

    init_kwargs = {"project": project} if project else {}

    try:
        ee.Initialize(**init_kwargs)
        _EE_INITIALIZED = True
        print("GEE initialized (existing token).")
        return True
    except Exception:
        pass

    try:
        import google.auth
        import google.auth.transport.requests

        creds, _ = google.auth.default()
        creds.refresh(google.auth.transport.requests.Request())
        ee.Initialize(creds, **init_kwargs)
        _EE_INITIALIZED = True
        print("GEE initialized (refreshed token).")
        return True
    except Exception:
        pass

    try:
        ee.Authenticate()
        ee.Initialize(**init_kwargs)
        _EE_INITIALIZED = True
        print("GEE initialized (manual authentication).")
        return True
    except Exception as exc:
        print(f"Failed to initialize Earth Engine: {exc}")
        return False


def load_forest_image():
    """Return the full Hansen Global Forest Change image."""
    import ee

    return ee.Image(FOREST_WATCH)


def get_clipped_forest(uploaded_file, project: Optional[str] = None):
    """Return the Hansen image clipped to an uploaded AOI.

    Args:
        uploaded_file: Path or file-like object of the user's GeoJSON.
        project: Optional Google Cloud project ID for Earth Engine.

    Returns:
        A tuple ``(image, geometry)`` where ``image`` is the clipped
        ``ee.Image`` and ``geometry`` is the ``ee.Geometry`` of the AOI.
        Returns ``(None, None)`` on failure.
    """
    if not authenticate_and_initialize(project=project):
        return None, None

    gdf = handle_geojson_upload(uploaded_file)
    if gdf is None:
        return None, None

    geometry = convert_uploaded_file_to_ee_geometry(uploaded_file)
    if geometry is None:
        return None, None

    try:
        image = load_forest_image().clip(geometry)
    except Exception as exc:
        print(f"Error clipping forest data to AOI: {exc}")
        return None, None

    return image, geometry
