# %%
import json
import os
import sys
import time

import pandas as pd
import requests

# Add parent directory to Python path to find my_functions_file
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from my_functions_file import get_address_requests, get_distance, reset_address_requests

"""
CANVASERS DRIVING DISTANCE ASSIGNMENT SCRIPT - Ran Interactively in Jupyter Notebook "Run Below"

This script processes a voter/address input file and a canvasser file, then assigns
each remaining source row to the nearest canvasser in the order provided.

1. INPUTS:
    - Source Excel file using the same input schema as Driving_Distance_Sort.py
    - Canvasers Excel file with: LastName, FirstName, FullStreetAddress, Zip
      or street component columns that can be combined into FullStreetAddress

2. GEOCODING:
    - Resolves each source address to longitude/latitude using a local cache first
      (`Lng_Lat_Hash.json`) and Mapbox Geocoding API only on cache misses

3. DISTANCE ASSIGNMENT:
    - For each canvasser row, calculates driving distance from that canvasser address
      to every remaining source address using get_distance(...)
    - Sorts the remaining rows by distance
        - Assigns an evenly sized share of the closest rows to that canvasser
    - Removes assigned rows before processing the next canvasser

4. OUTPUT:
        - Creates one Excel file in a format similar to Driving_Distance_Sort.py
        - Adds `Zone` column where value is the canvasser FirstName used for that assignment
    - Icon numbering follows driving distance from the address in `Canvasers.xlsx`
      for that canvasser row
    - The sequential icon numbering does NOT represent the shortest round trip path

5. REQUEST REPORTING:
    - Prints `address_requests_final` as the number of new driving-distance lookups
    - Prints `mapbox_address_requests_final` as the number of Mapbox geocoding calls made
    - Prints `lng_lat_hash_path` so the geocode cache location is visible
"""


MAPBOX_TOKEN = os.environ.get('MAPBOX_TOKEN')

if not MAPBOX_TOKEN:
    print("Mapbox token not found in environment variables.")
    print("Please set MAPBOX_TOKEN environment variable or enter it below:")
    MAPBOX_TOKEN = input("Enter your Mapbox API token: ").strip()

mapbox_address_requests = 0

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
        return coords
    return None


def ensure_full_street_address(df):
    if 'FullStreetAddress' in df.columns:
        return df['FullStreetAddress'].fillna('').astype(str).str.strip()

    address_parts = ['PrimaryHouseNumber', 'PrimaryStreetPre', 'PrimaryStreetName', 'PrimaryStreetType']
    missing_parts = [col for col in address_parts if col not in df.columns]
    if missing_parts:
        raise ValueError(
            "Excel file must include either 'FullStreetAddress' or all of "
            f"{address_parts}. Missing: {missing_parts}"
        )

    return (
        df['PrimaryHouseNumber'].fillna('').astype(str).str.strip() + ' ' +
        df['PrimaryStreetPre'].fillna('').astype(str).str.strip() + ' ' +
        df['PrimaryStreetName'].fillna('').astype(str).str.strip() + ' ' +
        df['PrimaryStreetType'].fillna('').astype(str).str.strip()
    ).str.replace(r'\s+', ' ', regex=True).str.strip()


def normalize_source_dataframe(df):
    df = df.copy()
    df['FullStreetAddress'] = ensure_full_street_address(df)

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
    else:
        df['Age'] = ''

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
    else:
        party_raw = pd.Series([''] * len(df), index=df.index)

    df['Party'] = 'Ind'
    df.loc[party_raw.str.contains('republican', regex=False), 'Party'] = 'Rep'
    df.loc[party_raw.str.contains('democrat', regex=False), 'Party'] = 'Dem'
    df.loc[party_raw.str.contains('swing', regex=False), 'Party'] = 'Ind'

    zip_series = df['Zip'].fillna('').astype(str).str.strip()
    df['CompleteAddress'] = df['FullStreetAddress'].where(
        zip_series == '',
        df['FullStreetAddress'] + ', ' + zip_series
    )
    return df


def normalize_canvasser_dataframe(df):
    df = df.copy()
    required_columns = ['LastName', 'FirstName', 'Zip']
    missing_required = [col for col in required_columns if col not in df.columns]
    if missing_required:
        raise ValueError(f"Canvasers.xlsx is missing required columns: {missing_required}")

    df['FullStreetAddress'] = ensure_full_street_address(df)
    zip_series = df['Zip'].fillna('').astype(str).str.strip()
    df['CompleteAddress'] = df['FullStreetAddress'].where(
        zip_series == '',
        df['FullStreetAddress'] + ', ' + zip_series
    )
    df['FirstName'] = df['FirstName'].fillna('').astype(str).str.strip()
    df['LastName'] = df['LastName'].fillna('').astype(str).str.strip()
    return df


def load_input_dataframe(file_path):
    suffix = os.path.splitext(file_path)[1].lower()

    if os.path.basename(file_path).startswith('~$'):
        raise ValueError(
            f"'{file_path}' looks like an Excel temporary lock file. "
            "Close the workbook in Excel and select the real .xlsx file instead."
        )

    if suffix in ['.xlsx', '.xlsm']:
        return pd.read_excel(file_path, engine='openpyxl')
    if suffix == '.csv':
        return pd.read_csv(file_path)

    raise ValueError(
        f"Unsupported input file type: '{suffix}'. Expected .xlsx, .xlsm, or .csv."
    )


def resolve_input_path(user_input, default_path=None, label='input file'):
    resolved_path = user_input.strip().strip('"')
    if not resolved_path:
        if default_path is None:
            raise ValueError(f"No {label} path was provided.")
        resolved_path = default_path

    if resolved_path.lower().endswith('.py') and default_path and os.path.exists(default_path):
        print(
            f"Resolved {label} path ended with .py; using default workbook instead: {default_path}"
        )
        resolved_path = default_path

    if not os.path.exists(resolved_path):
        raise FileNotFoundError(f"Could not find {label}: {resolved_path}")

    print(f"Using {label}: {resolved_path}")
    return resolved_path


def build_output_columns(df):
    columns = ['FirstName', 'LastName', 'FullStreetAddress']
    if 'PrimaryUnitNumber' in df.columns:
        columns.append('PrimaryUnitNumber')
    columns.extend(['Zip', 'Age', 'Party', 'Zone', 'lng', 'lat', 'distance_in_feet'])
    return columns


def autosize_worksheet(worksheet, result_df):
    for i, col in enumerate(result_df.columns):
        if result_df.empty:
            data_max_len = 0
        else:
            # Use positional indexing to avoid issues with duplicate column names.
            col_values = result_df.iloc[:, i]
            data_max_len = col_values.map(lambda val: len(str(val)) if pd.notna(val) else 0).max()
        max_len = max(data_max_len, len(str(col)))
        worksheet.set_column(i, i, max_len + 2)


def geocode_source_rows(source_df):
    prepared_rows = []
    failed_count = 0

    for _, row in source_df.iterrows():
        complete_address = row['CompleteAddress']
        coords = geocode_address(complete_address, MAPBOX_TOKEN)
        if coords:
            row_dict = row.to_dict()
            row_dict['lng'] = coords[0]
            row_dict['lat'] = coords[1]
            prepared_rows.append(row_dict)
            print(f"Geocoded source address: {row['FirstName']} {row['LastName']}")
        else:
            failed_count += 1
            print(f"Failed to geocode source address: {complete_address}")
        time.sleep(0.2)

    return pd.DataFrame(prepared_rows), failed_count


def assign_rows_to_canvassers(source_df, canvasser_df):
    output_columns = build_output_columns(source_df)
    remaining_df = source_df.copy()
    assigned_zone_frames = []
    total_rows = len(remaining_df)
    canvasser_count = len(canvasser_df)
    base_rows = total_rows // canvasser_count
    extra_rows = total_rows % canvasser_count

    for canvasser_index, (_, canvasser_row) in enumerate(canvasser_df.iterrows()):
        rows_for_this_canvasser = base_rows + (1 if canvasser_index < extra_rows else 0)
        canvasser_name = f"{canvasser_row['FirstName']} {canvasser_row['LastName']}".strip()
        zone_value = canvasser_row['FirstName']

        if rows_for_this_canvasser > 0 and not remaining_df.empty:
            canvasser_address = canvasser_row['CompleteAddress']
            distance_values = []
            for complete_address in remaining_df['CompleteAddress']:
                if complete_address == canvasser_address:
                    distance_values.append(0)
                else:
                    distance_values.append(get_distance(canvasser_address, complete_address))

            ranked_df = remaining_df.assign(distance_in_feet=distance_values).sort_values(
                'distance_in_feet', ascending=True
            )
            assigned_df = ranked_df.head(rows_for_this_canvasser).copy()
            remaining_df = ranked_df.iloc[rows_for_this_canvasser:].drop(columns=['distance_in_feet']).copy()
        else:
            assigned_df = remaining_df.iloc[0:0].copy()
            assigned_df['distance_in_feet'] = pd.Series(dtype='float64')

        assigned_df['Zone'] = zone_value
        assigned_df = assigned_df.reindex(columns=output_columns)
        assigned_zone_frames.append(assigned_df)

        print(f"Assigned {len(assigned_df)} rows to zone '{zone_value}' for {canvasser_name}")

    if assigned_zone_frames:
        combined_df = pd.concat(assigned_zone_frames, ignore_index=True)
    else:
        combined_df = pd.DataFrame(columns=output_columns)

    return combined_df


reset_address_requests()

source_prompt = "Enter the Full Path to the Source Excel file: "
source_file_path = resolve_input_path(input(source_prompt), label='source file')

default_canvasser_path = os.path.join(script_dir, 'Canvasers.xlsx')
if os.path.exists(default_canvasser_path):
    canvasser_file_path = default_canvasser_path
    print(f"Using canvasser file: {canvasser_file_path}")
else:
    canvasser_prompt = "Enter the Full Path to Canvasers.xlsx: "
    canvasser_file_path = resolve_input_path(
        input(canvasser_prompt),
        label='canvasser file'
    )

source_df = load_input_dataframe(source_file_path)
source_df = normalize_source_dataframe(source_df)

canvasser_df = load_input_dataframe(canvasser_file_path)
canvasser_df = normalize_canvasser_dataframe(canvasser_df)

if canvasser_df.empty:
    raise ValueError('Canvasers.xlsx must contain at least one canvasser row.')

prepared_source_df, failed_geocode_count = geocode_source_rows(source_df)
if prepared_source_df.empty:
    raise ValueError('No source rows could be geocoded, so no output files were created.')

combined_output_df = assign_rows_to_canvassers(prepared_source_df, canvasser_df)

combined_output_path = os.path.join(script_dir, 'Canvasser_Zones_Driving_Distance.xlsx')
with pd.ExcelWriter(combined_output_path, engine='xlsxwriter') as writer:
    combined_output_df.to_excel(writer, sheet_name='Sheet1', index=False)
    worksheet = writer.sheets['Sheet1']
    autosize_worksheet(worksheet, combined_output_df)

print(f"Created combined output file: {combined_output_path}")

print(f"failed_geocode_count = {failed_geocode_count}")
address_requests_final = get_address_requests()
print(f"new_mapbox_distance_requests_final = {address_requests_final}")
mapbox_address_requests_final = mapbox_address_requests
print(f"new_mapbox_lng_lat_request_final = {mapbox_address_requests_final}")
print(f"lng_lat_hash_path = {lng_lat_hash_path}")
# %%