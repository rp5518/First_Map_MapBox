# First Map MapBox - Mapping and Distance Analysis Tools

## Overview

This repository contains tools for processing voter/contact lists and creating maps with distance analysis.

## Scripts

### 1. Walk List Generation (Prerequisites)
The first thing you must do is create your "Completed_Walk_Lists" which are stored in the directory "C:\Users\wjg\Python_Stuff\Completed_Walk_Lists"
The "Completed_Walk_Lists" are generated from the Python File: "C:\Users\wjg\Python_Stuff\make_walk_lists.py"
Example Excel files for the input of make_walk_lists.py are: "C:\Users\wjg\Python_Stuff\Excel_Files\LD12_Hard_REP_EXAMPLE.xlsx" "C:\Users\wjg\Python_Stuff\Excel_Files\Thunderhill_Rep_VS_2024_EXAMPLE.csv"

### 2. Address2LngLat.py (Map Markers)
You must populate the "C:\Users\wjg\Python_Stuff\First_Map_MapBox\markers.json" by running the Python file: "C:\Users\wjg\Python_Stuff\First_Map_MapBox\Address2LngLat.py"
  
The Address2LngLat.py will request a Completed_Walk_List as input. The Completed_Walk_Lists are located at:
"C:\Users\wjg\Python_Stuff\Completed_Walk_Lists"
Once the markers.json is updated you can run the index.html file to generate a new map. "C:\Users\wjg\Python_Stuff\First_Map_MapBox\index.html"

### 3. **NEW: Radial_Distance_Sort.py** (Distance Analysis)
This script processes Excel files containing contact information and sorts them by distance from the first address using the Mapbox Geocoding API.

#### Setup Required Packages
```bash
pip install pandas requests xlsxwriter
```

#### Mapbox API Token Setup

**Option A: Environment Variable (Recommended)**
```bash
# Windows Command Prompt
set MAPBOX_TOKEN=your_mapbox_token_here

# Windows PowerShell
$env:MAPBOX_TOKEN="your_mapbox_token_here"
```

**Option B: Enter Token When Prompted**
The script will prompt you to enter your token if the environment variable is not set.

#### Get Your Mapbox Token
1. Sign up at [Mapbox.com](https://www.mapbox.com)
2. Go to your [Account page](https://account.mapbox.com/)
3. Copy your Default Public Token or create a new token

#### Usage
1. Run the script: `python Radial_Distance_Sort.py`
2. Enter the path to your Excel file when prompted
3. The script will create `Radial_Distance.xlsx` with results sorted by distance

#### Input File Format
Your Excel file should contain these columns:
- `FirstName`, `LastName`, `FullStreetAddress`, `Zip`, `Age/Party`

#### Output
Creates `Radial_Distance.xlsx` with all input columns plus:
- `lng` - Longitude coordinate
- `lat` - Latitude coordinate  
- `distance_in_feet` - Distance from first address

Results are sorted by distance (closest first).

The latest versions of "C:\Users\wjg\Python_Stuff\First_Map_MapBox\Address2LngLat.py" and "C:\Users\wjg\Python_Stuff\First_Map_MapBox\markers.json" are stored in GitHub at: https://github.com/rp5518/First_Map_MapBox
The marker’s data is stored at: https://console.firebase.google.com
The final map can be accessed at: https://map2canvass.com
My map2canvass name domain is saved in Cloudflare. I do not have a password. I just login with Google.

## Understanding Domain Name Assignments
    CNAME Type (Cononical Name) = www
    "A" Name Type (address Name) = map2canvass.com
    www.map2canvass.com maps to: rp5518.github.io
    map2canvass.com inside of Github maps to one of four servers: 185.199.108.153 or 185.199.109.153 or 185.199.110.153 or 185.199.111.153
    The apex domain (also called a "root domain" or "naked domain") is your domain name without any subdomain prefix
    apex domain = map2canvass.com

