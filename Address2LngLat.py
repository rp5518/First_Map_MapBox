# %%
import pandas as pd
import requests
import time
import json
import os

MAPBOX_TOKEN = 'pk.eyJ1Ijoid2pncnA1NTE4IiwiYSI6ImNtZmxxMm01MzA3c3oyaXExMWMxamVqZWoifQ.u2vTBRK2tHKi1HwI2JkhfA';

def geocode_address(address, token):
    # This function takes a street address and a Mapbox API token,
    # and returns the longitude and latitude coordinates for that address using the Mapbox Geocoding API.
    # It builds the API request URL with the address, sends a GET request, and parses the JSON response.
    # If the response contains at least one feature (i.e., a geocoding result),
    # it extracts the coordinates ([lng, lat]) from the first feature and returns them.
    # If no features are found, it returns None.
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{address}.json"
    params = {'access_token': token, 'limit': 1}
    response = requests.get(url, params=params)
    data = response.json()
    if data['features']:
        coords = data['features'][0]['geometry']['coordinates']
        return coords  # [lng, lat]
    return None

# Get file path from user
prompt_1 = "Enter the Full Path to an Excel File in the Completed_Walk_Lists Directory: "
prompt_1 += "Copy as Path and Paste Here: "
file_path = input(prompt_1)
file_path = file_path.strip('"')  # remove quotations

# Read Excel file
df = pd.read_excel(file_path)
print(f"Loaded {len(df)} rows from Excel file")

# Geocode and collect results
results = []
for idx, row in df.iterrows():
    coords = geocode_address(row['CompleteAddress'], MAPBOX_TOKEN)
    if coords:
        results.append({
            'first': row['FirstName'],
            'last': row['LastName'],
            'address': row['CompleteAddress'],
            'lng': coords[0],
            'lat': coords[1]
        })
        print(f"Geocoded: {row['FirstName']} {row['LastName']}")
    else:
        print(f"Failed: {row['CompleteAddress']}")
    time.sleep(0.2)  # Respect Mapbox rate limits

# Export to JS array or GeoJSON
import json
import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Create the full path to markers.json in the same directory as this script
output_file = os.path.join(script_dir, 'markers.json')

with open(output_file, 'w') as f:
    json.dump(results, f)

print(f"markers.json created successfully at: {output_file}")