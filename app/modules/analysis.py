from app.modules.gee_initialization import authenticate_and_initialize
import ee
import geemap
from app.modules.geojson_upload import handle_geojson_upload
import pandas as pd
from collections import OrderedDict
import matplotlib.pyplot as plt
import seaborn as sns

FOREST_WATCH = "UMD/hansen/global_forest_change_2023_v1_11"

def get_forest_col(geopolygon):

    # Authenticate and initialize GEE
    authenticate_and_initialize()
    # print("Authenticated")

    # Load the Hansen Global Forest Change dataset
    forest_watch = ee.Image(FOREST_WATCH)

    # Handle the GeoJSON upload and validate the AOI
    aoi = handle_geojson_upload(geopolygon)

    # Check if the AOI is valid
    if aoi is None:
        print("Error: Invalid AOI. Cannot proceed.")
        return None

    forest_col = forest_watch.clip(aoi)

    return forest_col

def get_forest_loss(geopolygon):

    aoi = handle_geojson_upload(geopolygon)

    # If the AOI is invalid, return None
    if aoi is None:
        print("Error: Invalid AOI. Cannot proceed.")
        return None, None

    # Extract the UTM CRS from the aoi's projection
    # The AOI is already projected to the appropriate UTM zone by handle_geojson_upload
    utm_crs_info = ee.Projection(aoi.projection()).getInfo()
    utm_crs = utm_crs_info['crs']

    forest_collection = get_forest_col(geopolygon)

    forest_loss = forest_collection.select('lossyear')

    # Reproject the forest loss to the same UTM projection as the AOI
    # This ensures consistent spatial analysis
    forest_loss_reprojected = forest_loss.reproject(crs=utm_crs, scale=30)

    return forest_loss_reprojected

def calculate_total_loss_per_year(forest_loss_reprojected):
    # Get the histogram from GEE
    histogram = forest_loss_reprojected.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        scale=30,
        maxPixels=1e13
    )

    # Get the histogram data
    histogram_data = histogram.getInfo()

    # Extract the lossyear frequency histogram
    loss_year_hist = histogram_data.get('lossyear', {})

    if not loss_year_hist:
        print("No loss year data found in histogram")
        return pd.DataFrame()

    # Create a dictionary for the DataFrame
    data = OrderedDict()

    # Year column
    data['Year'] = []
    # Pixel count column
    data['Pixel_Count'] = []
    # Area in hectares (1 pixel = 30m x 30m = 900 sq m)
    data['Area_Hectares'] = []
    # Area in square kilometers
    data['Area_SqKm'] = []

    # Calculate area for each year
    # Convert histogram keys from strings to integers for proper sorting
    for year_str, count in sorted(loss_year_hist.items(), key=lambda x: int(x[0]) if x[0] != 'null' else -1):
        # Year 0 means no loss, skip it or handle it differently if needed
        if year_str == '0':
            continue

        # Handle 'null' values (could be no data)
        if year_str == 'null':
            year_label = 'No Data'
        else:
            # Convert GEE encoding (year since 2000) to actual year
            year_label = 2000 + int(year_str)

        # Add to data dictionary
        data['Year'].append(year_label)
        data['Pixel_Count'].append(count)

        # Calculate area in hectares (1 pixel = 900 sq m = 0.09 hectares)
        area_hectares = count * 0.09
        data['Area_Hectares'].append(round(area_hectares, 2))

        # Calculate area in square kilometers
        area_sqkm = area_hectares / 100
        data['Area_SqKm'].append(round(area_sqkm, 4))

    # Create DataFrame
    df = pd.DataFrame(data)

    # Calculate totals
    total_pixels = df['Pixel_Count'].sum()
    total_hectares = df['Area_Hectares'].sum()
    total_sqkm = df['Area_SqKm'].sum()

    # Add a total row
    total_row = pd.DataFrame({
        'Year': ['Total'],
        'Pixel_Count': [total_pixels],
        'Area_Hectares': [round(total_hectares, 2)],
        'Area_SqKm': [round(total_sqkm, 4)]
    })

    df = pd.concat([df, total_row], ignore_index=True)

    return df


def plot_forest_loss_histogram(forest_loss_reprojected):
    loss_per_year_table = calculate_total_loss_per_year(forest_loss_reprojected)

    # Exclude the 'Total' row from the DataFrame for plotting
    df = loss_per_year_table[:-1]

    # Set Seaborn style for better aesthetics
    sns.set(style="whitegrid", palette="muted")

    # Create a bar plot using Seaborn
    plt.figure(figsize=(14, 7))
    ax = sns.barplot(
        x='Year',
        y='Area_SqKm',
        data=df,
        color='lightcoral',  # Soft coral color for bars
        edgecolor='darkred',  # Dark red outline for bars
        linewidth=2,  # Thicker outline
        alpha=0.8  # Slightly transparent bars
    )

    # Add labels and title
    plt.xlabel('Year', fontsize=14, fontweight='bold')
    plt.ylabel('Area Loss (Square Kilometers)', fontsize=14, fontweight='bold')
    plt.title('Forest Loss Over Time', fontsize=18, fontweight='bold', pad=20)

    # Add legend
    plt.legend(['Forest Loss (Area in SqKm)'], loc='upper right', fontsize=12)

    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45, fontsize=12, ha='right')
    plt.yticks(fontsize=12)

    # Add grid for better visualization (Seaborn's whitegrid style already includes this)

    # Add value labels on top of each bar
    for p in ax.patches:
        ax.annotate(
            f'{p.get_height():.2f}',  # Format the value to 2 decimal places
            (p.get_x() + p.get_width() / 2., p.get_height()),  # Position of the label
            ha='center', va='center',  # Center the label
            xytext=(0, 10),  # Offset the label slightly above the bar
            textcoords='offset points',
            fontsize=12,
            color='black'
        )

    # Adjust layout to prevent clipping of labels
    plt.tight_layout()

    # Show the plot
    plt.show()


def plot_forest_loss_map(forest_loss_reprojected, year, aoi):

    year_input = {
        2001: 1,
        2002: 2,
        2003: 3,
        2004: 4,
        2005: 5,
        2006: 6,
        2007: 7,
        2008: 8,
        2009: 9,
        2010: 10,
        2011: 11,
        2012: 12,
        2013: 13,
        2014: 14,
        2015: 15,
        2016: 16,
        2017: 17,
        2018: 18,
        2019: 19,
        2020: 20,
        2021: 21,
        2022: 22,
        2023: 23
    }
    try:
        number = year_input.get(year)
        loss_variable_name = 'loss_' + str(year)
        globals()[loss_variable_name] = forest_loss_reprojected.eq(number)

        loss_polygons = globals()[loss_variable_name].selfMask().reduceToVectors(
            geometryType='polygon',
            reducer=ee.Reducer.countEvery(),
            scale=30,
            maxPixels=1e13
        )

    except ee.ee_exception.EEException as e:
        print(f"Error: {e} - Using grid-based approach to avoid exceeding 5000 elements.")

        grid_size = 0.1
        grid = aoi.coveringGrid('EPSG:32632', grid_size * 10000)

        def process_cell(cell):
            cell_geometry = ee.Feature(cell).geometry()
            cell_loss = globals()[loss_variable_name].selfMask().clip(cell_geometry)

            try:
                cell_polygons = cell_loss.reduceToVectors(
                    geometryType='polygon',
                    reducer=ee.Reducer.countEvery(),
                    scale=30,
                    maxPixels=1e13,
                    geometry=cell_geometry
                )
                return cell_polygons.map(lambda feat: feat.set({
                    'grid_cell_id': ee.Feature(cell).id(),
                    'area_hectares': feat.area().divide(10000)
                }))

            except Exception as e:
                print(f"Grid cell processing error: {e}")
                return ee.FeatureCollection([])

        loss_polygons = ee.FeatureCollection(grid.map(process_cell)).flatten()

    Map = geemap.Map()
    Map.addLayer(loss_polygons, {'color': 'red'}, f"Forest Loss Polygons ({year})")
    Map.to_html()
    return Map






























