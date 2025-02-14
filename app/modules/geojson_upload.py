import geopandas as gpd
from shapely.geometry import Polygon
import pyproj
import geemap


def handle_geojson_upload(uploaded_file):
    """
    Loads a GeoJSON file into a GeoDataFrame, validates its geometry, and reprojects it to the specified EPSG code.

    Args:
        uploaded_file: Path to the GeoJSON file or a file-like object.

    Returns:
        geopandas.GeoDataFrame: A GeoDataFrame containing the geometry from the GeoJSON file.
                                Returns None if the file is invalid or contains no bounded geometry.
    """
    try:
        # Load the GeoJSON file into a GeoDataFrame
        gdf = gpd.read_file(uploaded_file)

        # Check if the GeoDataFrame is empty
        if gdf.empty:
            print("Error: The GeoJSON file is empty.")
            return None

        # Check if geometry column exists and is valid
        if 'geometry' not in gdf.columns or gdf.geometry.is_empty.all():
            print("Error: No valid geometries found in the GeoJSON file.")
            return None

        if not all(gdf.geometry.is_valid):
            print("Error: The GeoJSON file contains invalid geometries.")
            return None

        # Reproject to a temporary projected CRS for centroid calculation
        # Use a global projection like World Mercator (EPSG:3395) or a local projection
        temp_crs = "EPSG:3395"  # World Mercator (meters) - suitable for temporary calculations
        gdf_temp = gdf.to_crs(temp_crs)

        # Calculate the centroid in the temporary projected CRS
        centroid_projected = gdf_temp.geometry.centroid.iloc[0]  # Centroid in projected CRS

        # Transform the centroid back to geographic coordinates for UTM zone calculation
        # Use pyproj to transform the centroid from the projected CRS to geographic CRS (EPSG:4326)
        transformer = pyproj.Transformer.from_crs(temp_crs, "EPSG:4326", always_xy=True)
        longitude, latitude = transformer.transform(centroid_projected.x, centroid_projected.y)

        # Automatically determine the UTM zone based on the centroid
        utm_zone = int((longitude + 180) // 6) + 1  # Formula to calculate UTM zone
        utm_crs = f"EPSG:{32600 + utm_zone}" if latitude >= 0 else f"EPSG:{32700 + utm_zone}"
        print(f"Automatically determined UTM CRS: {utm_crs}")

        # Step 7: Reproject the GeoDataFrame to the determined UTM CRS
        gdf_projected = gdf.to_crs(utm_crs)

        return gdf_projected

    except Exception as e:
        print(f"Invalid GeoJSON file: {e}")
        return None


def convert_uploaded_file_to_ee_geometry(uploaded_file):
    gdf = handle_geojson_upload(uploaded_file)
    # convert it to a GEE geometry
    gdf_projected_ee = geemap.gdf_to_ee(gdf).geometry()
    return gdf_projected_ee