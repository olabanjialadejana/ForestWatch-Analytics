import ee
import geemap
from app.modules.geojson_upload import convert_uploaded_file_to_ee_geometry


# Functions to be built

# # Constants
# TREE_COVER2000 = 'treecover2000' # Percentage of tree cover in the year 2000 (0–100).
# LOSS = 'loss' # Binary mask (1 = forest loss, 0 = no loss).
# LOSS_YEAR = 'lossyear' # Year of forest loss (1–23, corresponding to 2001–2023).
# GAIN = 'gain' # Binary mask for forest gain from 2000–2023.
# DATAMASK = 'datamask' # Values: 0 (no data), 1 (land), 2 (water).
# FIRST = 'first' # Year of the first loss event.
# LAST ='last' # Year of the last loss event.
# TREE_COVER_GAIN = 'treecover_gain' # Tree cover increase from 2000 to 2023.
# BIOMASS = 'biomass' # Aboveground biomass density in Mg/ha.
# DENSITY = 'density' # Canopy density for pixels with >50% cover.

def forest_loss(forest_col, year, uploaded_file):
    """
    Calculates the total forest loss for a specified year within the area of interest (AOI)
    defined by the geometry of the clipped forest loss image.

    Args:
        forest_col (ee.Image): A clipped forest loss image (e.g., from Hansen dataset).
        year (int): The year for which to calculate forest loss.

    Returns:
        float: The total number of pixels with forest loss for the specified year.

    """
    # Extract the loss year band
    loss_year_band = forest_col.select('lossyear')

    # Create mask for the specified year (e.g., 2001 corresponds to 1)
    specified_year_mask = loss_year_band.eq(year)

    # Get the geometry of the AOI from the clipped image (An EE geometry)

    aoi_geometry = convert_uploaded_file_to_ee_geometry(uploaded_file)


    # Reduce the mask to count the number of pixels with forest loss
    loss_stats = specified_year_mask.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi_geometry,  # Use the clipped image's geometry
        scale=30,  # Adjust scale based on your dataset resolution
        maxPixels=1e13
    )

    # Get the total number of pixels with forest loss
    total_loss = loss_stats.getNumber('lossyear').getInfo()

    # Convert loss in pixels to hectares (pixel area is 30m x 30m)
    total_loss_hectares = (900 * total_loss)/100000

    return total_loss_hectares


def forest_gain():
    pass

def tree_cover_change():
    pass


def biomass_and_carbon_stock_estimates():
    pass


def canopy_density():
    pass


def temporal_loss_event():
    pass


def land_water_masking():
    pass


def hotspot_identification():
    pass

def forest_fragmentation():
    pass

def time_series():
    pass

def impact_forest_loss_biomass():
    pass

def data_qlt_cov_ass():
    pass



