from app.modules.geojson_upload import handle_geojson_upload

file_path = 'C:\Python Training\ForestWatch-Analytics\caroni2.geojson'
aoi = handle_geojson_upload(file_path)
print(aoi)




