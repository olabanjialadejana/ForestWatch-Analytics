import ee
import geemap
import geopandas as gpd
from IPython.display import display

FOREST_WATCH = "UMD/hansen/global_forest_change_2023_v1_11"

TREE_COVER2000 = 'treecover2000' # Percentage of tree cover in the year 2000 (0–100).
LOSS = 'loss' # Binary mask (1 = forest loss, 0 = no loss).
LOSS_YEAR = 'lossyear' # Year of forest loss (1–23, corresponding to 2001–2023).
GAIN = 'gain' # Binary mask for forest gain from 2000–2023.
DATAMASK = 'datamask' # Values: 0 (no data), 1 (land), 2 (water).
FIRST = 'first' # Year of the first loss event.
LAST ='last' # Year of the last loss event.
TREE_COVER_GAIN = 'treecover_gain' # Tree cover increase from 2000 to 2023.
BIOMASS = 'biomass' # Aboveground biomass density in Mg/ha.
DENSITY = 'density' # Canopy density for pixels with >50% cover.

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



def get_variable(forest_variable, geopolygon):
    authenticate_and_initialize()
    forest_watch = ee.Image("UMD/hansen/global_forest_change_2023_v1_11")
    aoi = gpd.read_file(geopolygon)
    # Simplify the geopolygon to reduce the number of edges (tolerance controls detail),
    # Else, gee will reject it
    aoi["geometry"] = aoi["geometry"].simplify(tolerance=0.001, preserve_topology=True)
    aoi_gee = geemap.gdf_to_ee(aoi)
    clipped_forest_variable = forest_variable.clip(aoi_gee)
    return clipped_forest_variable


def visualization_parameters():
    pass



