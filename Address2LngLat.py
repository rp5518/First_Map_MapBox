# %% Address to LngLat using Mapbox Geocoding API
import pandas as pd
import requests
import time

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

# Read Excel
df = pd.read_excel("C:\\Users\\wjg\\Python_Stuff\\Completed_Walk_Lists\\LD12_Hard_REP_EXAMPLE_approx_tsp_1.xlsx")

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
    time.sleep(0.2)  # Respect Mapbox rate limits

# Export to JS array or GeoJSON
import json
with open('markers.json', 'w') as f:
    json.dump(results, f)