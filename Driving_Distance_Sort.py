# %%
import pandas as pd
import requests
import time
import json
import os
import math
import sys

# Add parent directory to Python path to find my_functions_file
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from my_functions_file import get_distance, get_address_requests, reset_address_requests

"""
DRIVING DISTANCE SORT SCRIPT - Ran Interactively in Jupyter Notebook "Run Below"

This script processes an Excel file containing contact information with addresses and performs the following operations:

1. INPUTS: Prompts user for an Excel file path containing columns:
    - FirstName, LastName, FullStreetAddress, Zip
    - Optional: Age or Age/Party
    - Optional party source columns: Party, CalculatedParty, or OfficialParty

2. GEOCODING: Resolves each address (FullStreetAddress + Zip) to longitude/latitude
    using a local cache first (`Lng_Lat_Hash.json`) and Mapbox Geocoding API only on cache misses

3. DISTANCE CALCULATION: Calculates the driving distance in feet from the first address 
   in the list to all other addresses using Google Maps API with smart fallbacks:
   - Primary: Driving distance via Google Maps
   - Fallback 1: Walking distance if driving < 1200 feet
   - Fallback 2: Straight-line distance if walking < 400 feet

4. SORTING: Sorts all addresses by their distance from the first address (closest to farthest)

5. OUTPUT: Creates a new Excel file "Driving_Distance.xlsx" with columns:
    - FirstName, LastName, FullStreetAddress, Zip, Age, Party, lng, lat, distance_in_feet
   - Auto-sized columns for optimal viewing
   - Sorted by distance from the first address

6. REQUEST REPORTING:
    - Prints `mapbox_address_requests_final` as the total number of Mapbox API geocoding calls made
    - Prints `lng_lat_hash_path` so the cache file location is visible

7. PARTY NORMALIZATION:
    - Source priority: Party -> CalculatedParty -> OfficialParty -> Age/Party
    - Any value containing "republican" maps to "Rep"
    - Any value containing "democrat" maps to "Dem"
    - Any value containing "swing" maps to "Ind"
    - All other values default to "Ind"

Use case: Organizing contact lists by actual travel distance for canvassing, delivery routes, or territorial planning.
"""

# Get Mapbox token from environment variable or config file
import os
MAPBOX_TOKEN = os.environ.get('MAPBOX_TOKEN')

if not MAPBOX_TOKEN:
    # If environment variable not set, prompt user for token
    print("Mapbox token not found in environment variables.")
    print("Please set MAPBOX_TOKEN environment variable or enter it below:")
    MAPBOX_TOKEN = input("Enter your Mapbox API token: ").strip()

# Track total MapBox geocoding requests made during this script run.
mapbox_address_requests = 0

# Persist MapBox geocoding results so reruns can reuse lng/lat values.
script_dir = os.path.dirname(os.path.abspath(__file__))
lng_lat_hash_path = os.path.join(script_dir, 'Lng_Lat_Hash.json')
if os.path.exists(lng_lat_hash_path):
    try:
        with open(lng_lat_hash_path, 'r', encoding='utf-8') as lng_lat_file:
            lng_lat_hash = json.load(lng_lat_file)
    except json.JSONDecodeError:
        lng_lat_hash = {}
else:
    lng_lat_hash = {}

def geocode_address(address, token):
    # Return [lng, lat] for an address.
    # Uses Lng_Lat_Hash.json cache first, then calls Mapbox only when missing.
    # Successful Mapbox responses are written back to the cache.
    # Returns None when Mapbox has no matching feature.
    cached_coords = lng_lat_hash.get(address)
    if cached_coords is not None:
        return cached_coords

    global mapbox_address_requests
    mapbox_address_requests += 1
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{address}.json"
    params = {'access_token': token, 'limit': 1}
    response = requests.get(url, params=params)
    data = response.json()
    if data['features']:
        coords = data['features'][0]['geometry']['coordinates']
        lng_lat_hash[address] = coords
        with open(lng_lat_hash_path, 'w', encoding='utf-8') as lng_lat_file:
            json.dump(lng_lat_hash, lng_lat_file, indent=2)
        return coords  # [lng, lat]
    return None

# Note: Distance calculation is now handled by the get_distance function from my_functions_file
# which uses Google Maps API for driving distances with smart fallbacks

# Get file path from user
prompt_1 = "Enter the Full Path to an Excel File in the Completed_Walk_Lists Directory: "
prompt_1 += "Copy as Path and Paste Here: "
file_path = input(prompt_1)
file_path = file_path.strip('"')  # remove quotations

# Read Excel file
df = pd.read_excel(file_path)
print(f"Loaded {len(df)} rows from Excel file")
print("Column names in your Excel file:")
print(df.columns.tolist())

# Support two input schemas for street address.
# If FullStreetAddress is missing, construct it from primary street components.
if 'FullStreetAddress' not in df.columns:
    address_parts = ['PrimaryHouseNumber', 'PrimaryStreetPre', 'PrimaryStreetName', 'PrimaryStreetType']
    missing_parts = [col for col in address_parts if col not in df.columns]
    if missing_parts:
        raise ValueError(
            "Excel file must include either 'FullStreetAddress' or all of "
            f"{address_parts}. Missing: {missing_parts}"
        )

    df['FullStreetAddress'] = (
        df['PrimaryHouseNumber'].fillna('').astype(str).str.strip() + ' ' +
        df['PrimaryStreetPre'].fillna('').astype(str).str.strip() + ' ' +
        df['PrimaryStreetName'].fillna('').astype(str).str.strip() + ' ' +
        df['PrimaryStreetType'].fillna('').astype(str).str.strip()
    ).str.replace(r'\s+', ' ', regex=True).str.strip()

    print("Constructed 'FullStreetAddress' from primary street component columns.")

# Normalize Age for output. Prefer Age; if missing, try to parse leading number from Age/Party.
if 'Age' in df.columns:
    df['Age'] = df['Age'].fillna('').astype(str).str.strip()
elif 'Age/Party' in df.columns:
    df['Age'] = (
        df['Age/Party']
        .fillna('')
        .astype(str)
        .str.extract(r'^(\d+)')[0]
        .fillna('')
        .str.strip()
    )
    print("Constructed 'Age' from 'Age/Party'.")
else:
    df['Age'] = ''

# Build normalized Party with source priority:
# Party -> CalculatedParty -> OfficialParty -> Age/Party
# Keyword mapping: republican => Rep, democrat => Dem, swing => Ind, else Ind.
party_source_col = None
if 'Party' in df.columns:
    party_source_col = 'Party'
elif 'CalculatedParty' in df.columns:
    party_source_col = 'CalculatedParty'
elif 'OfficialParty' in df.columns:
    party_source_col = 'OfficialParty'

if party_source_col is not None:
    party_raw = df[party_source_col].fillna('').astype(str).str.strip().str.lower()
elif 'Age/Party' in df.columns:
    party_raw = df['Age/Party'].fillna('').astype(str).str.strip().str.lower()
    party_source_col = 'Age/Party'
else:
    party_raw = pd.Series([''] * len(df), index=df.index)

df['Party'] = 'Ind'
df.loc[party_raw.str.contains('republican', regex=False), 'Party'] = 'Rep'
df.loc[party_raw.str.contains('democrat', regex=False), 'Party'] = 'Dem'
df.loc[party_raw.str.contains('swing', regex=False), 'Party'] = 'Ind'

if party_source_col is not None:
    print(f"Constructed normalized 'Party' from '{party_source_col}'.")

# Geocode and collect results
results = []
first_complete_address = None  # Store the first address string for distance calculations

for idx, row in df.iterrows():
    # Combine FullStreetAddress and Zip to create complete address for geocoding
    complete_address = f"{row['FullStreetAddress']}, {row['Zip']}"
    
    coords = geocode_address(complete_address, MAPBOX_TOKEN)
    if coords:
        # Store the first address string for distance calculations
        if first_complete_address is None:
            first_complete_address = complete_address
            distance_feet = 0  # First address has 0 distance from itself
        else:
            # Calculate driving distance from first address using get_distance function
            distance_feet = get_distance(first_complete_address, complete_address)
        
        result_row = {
            'FirstName': row['FirstName'],
            'LastName': row['LastName'],
            'FullStreetAddress': row['FullStreetAddress'],
        }
        # Insert PrimaryUnitNumber after FullStreetAddress if it exists
        if 'PrimaryUnitNumber' in df.columns:
            result_row['PrimaryUnitNumber'] = row['PrimaryUnitNumber'] if pd.notna(row['PrimaryUnitNumber']) else ''
        
        result_row.update({
            'Zip': row['Zip'],
            'Age': row['Age'],
            'Party': row['Party'],
        })

        result_row.update({
            'lng': coords[0],
            'lat': coords[1],
            'distance_in_feet': distance_feet
        })
        results.append(result_row)
        print(f"Geocoded: {row['FirstName']} {row['LastName']} - Distance: {distance_feet} ft")
    else:
        print(f"Failed: {complete_address}")
    time.sleep(0.2)  # Respect Mapbox rate limits

# Export to Excel file
# Create the full path to Driving_Distance.xlsx in the same directory as this script
output_file = os.path.join(script_dir, 'Driving_Distance.xlsx')

# Convert results to DataFrame, sort by distance, and save as Excel
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('distance_in_feet', ascending=True)

# Create Excel file with auto-sized columns
with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    results_df.to_excel(writer, sheet_name='Sheet1', index=False)
    
    # Get the xlsxwriter workbook and worksheet objects
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']
    
    # Auto-adjust column widths based on content
    for i, col in enumerate(results_df.columns):
        # Calculate the maximum width needed for each column
        max_len = max(
            results_df[col].astype(str).map(len).max(),  # max length of column data
            len(str(col))  # length of column name
        )
        # Add some padding and set the column width
        worksheet.set_column(i, i, max_len + 2)

print(f"Driving_Distance.xlsx created successfully at: {output_file}")
mapbox_address_requests_final = mapbox_address_requests
print(f"mapbox_address_requests_final = {mapbox_address_requests_final}")
print(f"lng_lat_hash_path = {lng_lat_hash_path}")
# %%
