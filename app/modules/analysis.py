"""Forest-change analytics on top of the Hansen dataset.

Each function in this module assumes the caller has already initialised
Earth Engine (see :mod:`app.modules.forest_data`) and provides a clipped
image together with the ``ee.Geometry`` that defines the AOI.

The Hansen dataset is published at roughly 30 m resolution, so one pixel
covers 900 m\u00b2 (0.09 ha). Pixel counts are therefore multiplied by
0.09 to obtain hectares.
"""

from __future__ import annotations

from typing import Dict, List, Optional

PIXEL_AREA_HA = 0.09  # 30 m x 30 m pixels = 900 m^2 = 0.09 ha
HANSEN_START_YEAR = 2000
HANSEN_END_YEAR = 2023


def _reduce_sum(mask, geometry, band: str, scale: int = 30) -> float:
    """Return the sum of a binary mask over ``geometry`` (as a Python float)."""
    import ee

    stats = mask.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=scale,
        maxPixels=int(1e13),
        bestEffort=True,
    )
    value = stats.get(band)
    if value is None:
        return 0.0
    # ee.Number handles None gracefully via .getInfo()
    try:
        return float(ee.Number(value).getInfo() or 0.0)
    except Exception:
        return 0.0


def forest_loss(forest_image, geometry, year: int) -> float:
    """Total forest loss for a single year, in hectares.

    Args:
        forest_image: A clipped ``ee.Image`` of the Hansen dataset.
        geometry: The AOI as an ``ee.Geometry``.
        year: Calendar year between 2001 and ``HANSEN_END_YEAR``.

    Returns:
        Forest loss area (ha). Returns ``0.0`` if the year is out of range.
    """
    if year < HANSEN_START_YEAR + 1 or year > HANSEN_END_YEAR:
        return 0.0

    loss_year_band = forest_image.select("lossyear")
    mask = loss_year_band.eq(year - HANSEN_START_YEAR)
    # Rename the band so the reducer output key is predictable.
    mask = mask.rename("loss")
    pixels = _reduce_sum(mask, geometry, band="loss")
    return pixels * PIXEL_AREA_HA


def forest_loss_by_year(
    forest_image, geometry, start_year: int = 2001, end_year: int = HANSEN_END_YEAR
) -> Dict[int, float]:
    """Compute per-year forest loss (ha) between two years (inclusive)."""
    start_year = max(start_year, HANSEN_START_YEAR + 1)
    end_year = min(end_year, HANSEN_END_YEAR)
    return {
        year: forest_loss(forest_image, geometry, year)
        for year in range(start_year, end_year + 1)
    }


def total_forest_loss(forest_image, geometry) -> float:
    """Total forest loss in hectares across the full Hansen record."""
    loss_band = forest_image.select("loss").rename("loss")
    pixels = _reduce_sum(loss_band, geometry, band="loss")
    return pixels * PIXEL_AREA_HA


def forest_gain(forest_image, geometry) -> float:
    """Total forest gain in hectares (2000\u20132012 as published by Hansen)."""
    gain_band = forest_image.select("gain").rename("gain")
    pixels = _reduce_sum(gain_band, geometry, band="gain")
    return pixels * PIXEL_AREA_HA


def tree_cover_2000(forest_image, geometry, threshold: int = 30) -> float:
    """Area (ha) with tree cover \u2265 ``threshold`` percent in 2000.

    Args:
        threshold: Minimum canopy cover percentage to count as "forest".
    """
    band = forest_image.select("treecover2000")
    mask = band.gte(threshold).rename("treecover2000")
    pixels = _reduce_sum(mask, geometry, band="treecover2000")
    return pixels * PIXEL_AREA_HA


def tree_cover_change(
    forest_image, geometry, threshold: int = 30
) -> Dict[str, float]:
    """Summarise tree cover change within the AOI.

    Returns:
        A dict with keys ``cover_2000``, ``loss``, ``gain`` and ``net``
        (all in hectares).
    """
    cover_2000 = tree_cover_2000(forest_image, geometry, threshold=threshold)
    loss = total_forest_loss(forest_image, geometry)
    gain = forest_gain(forest_image, geometry)
    return {
        "cover_2000": cover_2000,
        "loss": loss,
        "gain": gain,
        "net": gain - loss,
    }


def land_water_area(forest_image, geometry) -> Dict[str, float]:
    """Return land and water area (ha) from the ``datamask`` band."""
    datamask = forest_image.select("datamask")
    land_mask = datamask.eq(1).rename("land")
    water_mask = datamask.eq(2).rename("water")
    land_ha = _reduce_sum(land_mask, geometry, band="land") * PIXEL_AREA_HA
    water_ha = _reduce_sum(water_mask, geometry, band="water") * PIXEL_AREA_HA
    return {"land_ha": land_ha, "water_ha": water_ha}


def aoi_area_hectares(geometry) -> float:
    """Return the area of the AOI in hectares using Earth Engine."""
    import ee

    try:
        return float(ee.Number(geometry.area(1)).divide(10_000).getInfo())
    except Exception:
        return 0.0


def annual_loss_series(
    forest_image,
    geometry,
    start_year: int = 2001,
    end_year: int = HANSEN_END_YEAR,
) -> List[Dict[str, float]]:
    """Build a tabular time series of forest loss.

    Returns:
        A list of ``{"year": int, "loss_ha": float, "cumulative_ha": float}``
        dicts, ordered by year ascending.
    """
    per_year = forest_loss_by_year(
        forest_image, geometry, start_year=start_year, end_year=end_year
    )
    out: List[Dict[str, float]] = []
    running = 0.0
    for year in sorted(per_year):
        loss_ha = per_year[year]
        running += loss_ha
        out.append(
            {"year": year, "loss_ha": loss_ha, "cumulative_ha": running}
        )
    return out


def hotspot_years(
    forest_image,
    geometry,
    top_n: int = 3,
    start_year: int = 2001,
    end_year: int = HANSEN_END_YEAR,
) -> List[Dict[str, float]]:
    """Return the ``top_n`` years with the highest forest loss."""
    series = annual_loss_series(forest_image, geometry, start_year, end_year)
    ranked = sorted(series, key=lambda row: row["loss_ha"], reverse=True)
    return ranked[:top_n]


def summary_statistics(
    forest_image,
    geometry,
    threshold: int = 30,
) -> Dict[str, float]:
    """Generate a single summary dict for reports and dashboards."""
    change = tree_cover_change(forest_image, geometry, threshold=threshold)
    land_water = land_water_area(forest_image, geometry)
    return {
        "aoi_area_ha": aoi_area_hectares(geometry),
        "tree_cover_threshold": float(threshold),
        **change,
        **land_water,
    }
