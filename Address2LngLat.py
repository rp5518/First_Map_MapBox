"""
This script geocodes voter addresses with the Mapbox Geocoding API.
It prompts for an input Excel file, creates CompleteAddress if needed from
FullStreetAddress and Zip, converts each address to longitude/latitude, and
writes the results to markers.json in First_Map_MapBox.
"""

# %% Address to LngLat using Mapbox Geocoding API
import pandas as pd
import requests
import time
import json
import os
from pathlib import Path

MAPBOX_TOKEN = os.getenv('MAPBOX_TOKEN', '').strip()
if not MAPBOX_TOKEN:
    MAPBOX_TOKEN = input('Enter Mapbox access token: ').strip()
if not MAPBOX_TOKEN:
    raise ValueError('Mapbox access token is required.')

try:
    SCRIPT_DIR = Path(__file__).resolve().parent
except NameError:
    SCRIPT_DIR = Path.cwd()


def prompt_for_input_excel_path():
    prompt = "Enter full path to source Excel file: "
    while True:
        raw = input(prompt).strip().strip('"').strip("'")
        if not raw:
            print('A file path is required.')
            continue

        candidate = Path(raw)
        if not candidate.is_absolute():
            cwd_candidate = (Path.cwd() / candidate).resolve()
            if cwd_candidate.exists():
                candidate = cwd_candidate

        if candidate.exists() and candidate.is_file():
            return candidate

        print(f'File not found: {candidate}')


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
input_excel = prompt_for_input_excel_path()
print(f'Using input file: {input_excel}')
df = pd.read_excel(input_excel)

if 'CompleteAddress' not in df.columns:
    required_cols = {'FullStreetAddress', 'Zip'}
    missing = required_cols.difference(df.columns)
    if missing:
        raise KeyError(f"Missing required columns to create CompleteAddress: {sorted(missing)}")

    full_street = df['FullStreetAddress'].astype(str).str.strip()
    zip_code = df['Zip'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
    df['CompleteAddress'] = full_street + ', ' + zip_code

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
output_json = SCRIPT_DIR / 'markers.json'
with output_json.open('w', encoding='utf-8') as f:
    json.dump(results, f)

print(f'markers.json created at: {output_json}')