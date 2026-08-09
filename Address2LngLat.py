"""
This script prepares map marker data from a source Excel file.

What it does:
- Prompts for an input Excel workbook containing voter or household records.
- Builds a CompleteAddress column when one is not already present by combining
    FullStreetAddress and Zip, or reuses an existing CompleteAddress column.
- Groups rows by CompleteAddress so multiple people at the same address are
    written as one map marker entry.
- Reuses existing lng/lat values from the spreadsheet when they are already
    available.
- Reuses coordinate values from Lng_Lat_Hash.json when that cache already has
    a matching address, and otherwise falls back to the Mapbox Geocoding API.
- Preserves first name, last name, optional age, optional party, and optional
    zone values as comma-separated lists so the popup on the map can show
    everyone at the same address.
- Writes the final marker list to markers.json next to this script, including
    party when a Party column exists in the input file.
- Prints a progress update every five seconds and reports how many external
    coordinate lookups were required at the end of the run.

Expected input columns:
- FullStreetAddress and Zip, unless CompleteAddress already exists.
- FirstName and LastName for popup labels.
- Optional Age, Party, lng, and lat columns.
- Optional Zone column (e.g. "Zone #1"). All rows in a group must share
    the same zone value; the first non-blank value in the group is used.

Output:
- markers.json containing one object per unique address with first, last,
    address, lng, lat, and optional age, party, and zone fields.
"""

# %% Address to LngLat using Mapbox Geocoding API
import pandas as pd
import requests
import time
import json
import os
from pathlib import Path

MAPBOX_TOKEN = os.getenv('MAPBOX_TOKEN', '').strip()

try:
    SCRIPT_DIR = Path(__file__).resolve().parent
except NameError:
    SCRIPT_DIR = Path.cwd()


def prompt_for_input_excel_path():
    """Prompt until the user provides an existing Excel file path."""
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
    """Return [lng, lat] for an address using the Mapbox Geocoding API."""
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{address}.json"
    params = {'access_token': token, 'limit': 1}
    response = requests.get(url, params=params)
    data = response.json()
    if data['features']:
        coords = data['features'][0]['geometry']['coordinates']
        return coords  # [lng, lat]
    return None


def get_mapbox_token():
    """Return the Mapbox token, prompting the user if the environment variable is missing."""
    global MAPBOX_TOKEN
    if not MAPBOX_TOKEN:
        MAPBOX_TOKEN = input('Enter Mapbox access token: ').strip()
    if not MAPBOX_TOKEN:
        raise ValueError('Mapbox access token is required for geocoding.')
    return MAPBOX_TOKEN


def normalize_column_name(column_name):
    """Return a simplified column name for tolerant matching."""
    return ''.join(ch.lower() for ch in str(column_name).strip() if ch.isalnum())


def find_column_name(columns, aliases):
    """Return the first source column whose normalized name matches any alias."""
    normalized_aliases = {normalize_column_name(alias) for alias in aliases}
    for column in columns:
        if normalize_column_name(column) in normalized_aliases:
            return column
    return None


def load_existing_hash(hash_path):
    """Load an existing Lng_Lat_Hash.json file if it exists."""
    if not hash_path.exists():
        return {}
    try:
        with hash_path.open('r', encoding='utf-8') as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except Exception as exc:
        print(f'Warning: could not read {hash_path}: {exc}')
    return {}


def save_hash_entry(hash_path, address, coords):
    """Persist a new address-to-coordinates mapping to Lng_Lat_Hash.json."""
    hash_data = load_existing_hash(hash_path)
    hash_data[address] = [coords[0], coords[1]]
    with hash_path.open('w', encoding='utf-8') as handle:
        json.dump(hash_data, handle, indent=2)


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

# Normalise column names for tolerant lookup
lng_column = find_column_name(df.columns, ['lng', 'longitude'])
lat_column = find_column_name(df.columns, ['lat', 'latitude'])
age_column = find_column_name(df.columns, ['age'])
party_column = find_column_name(df.columns, ['party'])
zone_column = find_column_name(df.columns, ['zone', 'zone column', 'zone_number', 'zonenumber'])

# Geocode and collect results
results = []
has_existing_coordinates = bool(lng_column and lat_column)
has_age_column = bool(age_column)
has_party_column = bool(party_column)
has_zone_column = bool(zone_column)

if has_existing_coordinates:
    df.rename(columns={lng_column: 'lng', lat_column: 'lat'}, inplace=True)
if has_age_column:
    df.rename(columns={age_column: 'Age'}, inplace=True)
if has_party_column:
    df.rename(columns={party_column: 'Party'}, inplace=True)
if has_zone_column:
    df.rename(columns={zone_column: 'Zone'}, inplace=True)

print(
    'Columns detected  ->  '
    f'age: {has_age_column} ({age_column}), '
    f'party: {has_party_column} ({party_column}), '
    f'zone: {has_zone_column} ({zone_column}), '
    f'existing coords: {has_existing_coordinates} ({lng_column}, {lat_column})'
)

address_groups = list(df.groupby('CompleteAddress', sort=False))
total_addresses = len(address_groups)
last_progress_time = time.time()
external_lookup_count = 0
hash_path = SCRIPT_DIR / 'Lng_Lat_Hash.json'
existing_hash = load_existing_hash(hash_path)

for index, (complete_address, address_group) in enumerate(address_groups, start=1):
    current_time = time.time()
    if current_time - last_progress_time >= 5:
        print(
            f'Progress: {index}/{total_addresses} addresses processed '
            f'({index / total_addresses * 100:.1f}%)'
        )
        last_progress_time = current_time
    # Keep row-level ordering so first/last/age entries stay aligned in popup rendering.
    first_values = [value.strip() for value in address_group['FirstName'].fillna('').astype(str).tolist()]
    last_values = [value.strip() for value in address_group['LastName'].fillna('').astype(str).tolist()]
    age_values = []
    if has_age_column:
        for value in address_group['Age'].tolist():
            if pd.isna(value):
                age_values.append('')
            else:
                normalized = value.item() if hasattr(value, 'item') else value
                age_values.append(str(normalized).strip())

    party_values = []
    if has_party_column:
        for value in address_group['Party'].tolist():
            if pd.isna(value):
                party_values.append('')
            else:
                normalized = value.item() if hasattr(value, 'item') else value
                party_values.append(str(normalized).strip())

    zone_value = ''
    if has_zone_column:
        non_blank = address_group['Zone'].dropna().astype(str).str.strip()
        non_blank = non_blank[non_blank != '']
        if not non_blank.empty:
            zone_value = non_blank.iloc[0]

    coords = None
    if has_existing_coordinates:
        coords_rows = address_group[address_group['lng'].notna() & address_group['lat'].notna()]
        if not coords_rows.empty:
            first_coords = coords_rows.iloc[0]
            coords = [first_coords['lng'], first_coords['lat']]

    if not coords:
        cached_coords = existing_hash.get(complete_address)
        if cached_coords:
            coords = [cached_coords[0], cached_coords[1]]
        else:
            token = get_mapbox_token()
            coords = geocode_address(complete_address, token)
            if coords:
                external_lookup_count += 1
                save_hash_entry(hash_path, complete_address, coords)
            time.sleep(0.2)  # Respect Mapbox rate limits only for API calls

    if coords:
        marker_row = {
            'first': ', '.join(first_values),
            'last': ', '.join(last_values),
            'address': complete_address,
            'lng': coords[0],
            'lat': coords[1]
        }
        if has_age_column:
            marker_row['age'] = ', '.join(age_values)
        if has_party_column:
            marker_row['party'] = ', '.join(party_values)
        if has_zone_column and zone_value:
            marker_row['zone'] = zone_value

        results.append(marker_row)


# Export to JS array or GeoJSON
output_json = SCRIPT_DIR / 'markers.json'
with output_json.open('w', encoding='utf-8') as f:
    json.dump(results, f)

print(f'markers.json created at: {output_json}')
print(f'External coordinate lookups performed: {external_lookup_count}')