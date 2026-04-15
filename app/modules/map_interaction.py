"""Interactive map helpers built on top of folium and geemap."""

from __future__ import annotations

from typing import Optional

import folium

# Visualisation parameters tailored to the Hansen Global Forest Change dataset.
TREE_COVER_VIS = {
    "bands": ["treecover2000"],
    "min": 0,
    "max": 100,
    "palette": ["000000", "00FF00"],
}

LOSS_VIS = {
    "bands": ["loss"],
    "min": 0,
    "max": 1,
    "palette": ["000000", "FF0000"],
}

LOSS_YEAR_VIS = {
    "bands": ["lossyear"],
    "min": 1,
    "max": 23,
    "palette": [
        "fff7ec", "fee8c8", "fdd49e", "fdbb84", "fc8d59",
        "ef6548", "d7301f", "b30000", "7f0000",
    ],
}

GAIN_VIS = {
    "bands": ["gain"],
    "min": 0,
    "max": 1,
    "palette": ["000000", "0000FF"],
}


def _add_ee_layer(folium_map: folium.Map, ee_image, vis_params: dict, name: str) -> None:
    """Attach an Earth Engine tile layer to a folium map."""
    import ee

    map_id = ee.Image(ee_image).getMapId(vis_params)
    folium.raster_layers.TileLayer(
        tiles=map_id["tile_fetcher"].url_format,
        attr="Google Earth Engine",
        name=name,
        overlay=True,
        control=True,
    ).add_to(folium_map)


def _aoi_center(gdf):
    """Return ``(lat, lon)`` for the centroid of a GeoDataFrame."""
    mercator = gdf.to_crs("EPSG:3857")
    centroid = mercator.geometry.union_all().centroid
    import pyproj

    transformer = pyproj.Transformer.from_crs(
        "EPSG:3857", "EPSG:4326", always_xy=True
    )
    lon, lat = transformer.transform(centroid.x, centroid.y)
    return lat, lon


def build_map(
    aoi_gdf,
    forest_image=None,
    *,
    show_tree_cover: bool = True,
    show_loss: bool = True,
    show_loss_year: bool = False,
    show_gain: bool = False,
    zoom_start: int = 8,
) -> folium.Map:
    """Create a folium map centred on the AOI with optional GEE overlays.

    Args:
        aoi_gdf: GeoDataFrame in EPSG:4326 describing the AOI.
        forest_image: Optional clipped ``ee.Image``. When omitted only the
            AOI outline is drawn.
        show_tree_cover: Add the 2000 tree cover layer.
        show_loss: Add the aggregate loss layer.
        show_loss_year: Add the per-year loss layer.
        show_gain: Add the forest gain layer.
    """
    lat, lon = _aoi_center(aoi_gdf)
    fmap = folium.Map(location=[lat, lon], zoom_start=zoom_start, tiles="OpenStreetMap")

    folium.GeoJson(
        aoi_gdf.__geo_interface__,
        name="Area of Interest",
        style_function=lambda _feat: {
            "color": "#1f77b4",
            "weight": 2,
            "fillOpacity": 0.05,
        },
    ).add_to(fmap)

    if forest_image is not None:
        if show_tree_cover:
            _add_ee_layer(fmap, forest_image, TREE_COVER_VIS, "Tree cover 2000")
        if show_loss:
            _add_ee_layer(
                fmap,
                forest_image.updateMask(forest_image.select("loss")),
                LOSS_VIS,
                "Forest loss 2001-2023",
            )
        if show_loss_year:
            _add_ee_layer(
                fmap,
                forest_image.updateMask(forest_image.select("lossyear")),
                LOSS_YEAR_VIS,
                "Loss year",
            )
        if show_gain:
            _add_ee_layer(
                fmap,
                forest_image.updateMask(forest_image.select("gain")),
                GAIN_VIS,
                "Forest gain",
            )

    folium.LayerControl(collapsed=False).add_to(fmap)
    return fmap


def fit_bounds_to_gdf(fmap: folium.Map, gdf) -> folium.Map:
    """Zoom ``fmap`` to the bounding box of ``gdf``."""
    minx, miny, maxx, maxy = gdf.total_bounds
    fmap.fit_bounds([[miny, minx], [maxy, maxx]])
    return fmap


def simple_aoi_map(aoi_gdf, zoom_start: int = 8) -> folium.Map:
    """Return a folium map that only shows the AOI outline.

    Useful when Earth Engine is not available (e.g. for previews before the
    user authenticates).
    """
    return build_map(aoi_gdf, forest_image=None, zoom_start=zoom_start)
