import ee
import geemap
from app.modules.geojson_upload import handle_geojson_upload

FOREST_WATCH = "UMD/hansen/global_forest_change_2023_v1_11"



def authenticate_and_initialize():
    try:
        ee.Initialize()
        print('GEE initialized (existing token).')
    except:
        # if token is expired, try to refresh it
        # based on https://stackoverflow.com/questions/53472429/how-to-get-a-gcp-bearer-token-programmatically-with-python
        try:
            import google.auth
            import google.auth.transport.requests
            creds, project = google.auth.default()
            # creds.valid is False, and creds.token is None
            # refresh credentials to populate those
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            # initialise GEE session with refreshed credentials
            ee.Initialize(creds)
            print('GEE initialized (refreshed token).')
        except:
            # get the user to authenticate manually and initialize the session
            ee.Authenticate()
            ee.Initialize()
            print('GEE initialized (manual authentication).')


def get_variable(geopolygon):
    """
    Retrieves forest cover data from the Forest Watch dataset for a specified geographical polygon.

    This function initializes authentication for Google Earth Engine (GEE), processes the input
    geographical polygon (GeoJSON format), simplifies it to reduce complexity, and extracts
    relevant forest cover data from the FOREST_WATCH dataset.

    Args:
        File path to a geopolygon (dict or geopandas.GeoDataFrame): File path to a GeoJSON-like dictionary or a
            GeoDataFrame representing the area of interest (AOI).

    Returns:
        ee.Image: A Google Earth Engine (GEE) image representing forest cover data for the
        specified AOI.

    """
    # Authenticate and initialize GEE
    authenticate_and_initialize()
    print("Authenticated")

    # Load the Hansen Global Forest Change dataset
    forest_watch = ee.Image(FOREST_WATCH)

    # Handle the GeoJSON upload and validate the AOI
    aoi = handle_geojson_upload(geopolygon)

    # Check if the AOI is valid
    if aoi is None:
        print("Error: Invalid AOI. Cannot proceed.")
        return None

    # Simplify the geometry to reduce complexity
    aoi["geometry"] = aoi["geometry"].simplify(tolerance=0.001, preserve_topology=True)

    # Convert the GeoDataFrame to an ee.Geometry object
    try:
        aoi_gee = geemap.gdf_to_ee(aoi)

    except Exception as e:
        print(f"Error converting GeoDataFrame to ee.Geometry: {e}")
        return None


    # Clip the forest data to the AOI
    try:
        forest_col = forest_watch.clip(aoi_gee)

    except Exception as e:
        print(f"Error clipping forest data to AOI: {e}")
        return None


    return forest_col