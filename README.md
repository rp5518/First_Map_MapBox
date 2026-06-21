# First Map MapBox - Mapping and Distance Analysis Tools

## Overview

This repository contains four related workflows that start from a GOP Data Center Excel export and turn it into canvasser zones, walk lists, driving-distance lists, radial-distance lists, and map data.

Workflow priority in this repository:
1. Canvasser zone assignment (`Canvasser_Zones_Driving_Distance.xlsx`)
2. Walk list generation (`make_walk_lists.py`)
3. Driving distance sort (`Driving_Distance_Sort.py`)
4. Radial distance sort (`Radial_Distance_Sort.py`)

## Common Input Source

All four workflows start from an original Excel export from the GOP Data Center. The exact column set can vary a little by export, but these scripts are designed around the following common fields:

- `FirstName`
- `LastName`
- `FullStreetAddress` and `Zip`
- or street component columns that can be combined into `FullStreetAddress`
- optional `Age` or `Age/Party`
- optional `Party`, `CalculatedParty`, or `OfficialParty`
- optional `PrimaryUnitNumber`

If `FullStreetAddress` is not present, the scripts can build it from:
- `PrimaryHouseNumber`
- `PrimaryStreetPre`
- `PrimaryStreetName`
- `PrimaryStreetType`

## Workflow 1: Canvasser Zone Assignment (Most Important)

### Script
- [Canvasers_Driving_Distance_Assign.py](Canvasers_Driving_Distance_Assign.py)

### What it does
This workflow creates the most important assignment output in this project:
`C:\Users\wjg\Python_Stuff\First_Map_MapBox\Canvasser_Zones_Driving_Distance.xlsx`.

The script:
- reads the GOP Data Center source file
- reads canvasser addresses from `Canvasers.xlsx`
- computes driving distances from each canvasser to remaining source rows
- assigns rows in sequence to canvasser zones
- writes one combined output file with a `Zone` column using canvasser `FirstName`

### Expected input
- GOP Data Center source Excel file with the common fields listed above
- `C:\Users\wjg\Python_Stuff\First_Map_MapBox\Canvasers.xlsx` with:
	- `LastName`
	- `FirstName`
	- `FullStreetAddress` and `Zip`
	- or street component columns that can build `FullStreetAddress`

### Output location
- `C:\Users\wjg\Python_Stuff\First_Map_MapBox\Canvasser_Zones_Driving_Distance.xlsx`

### Cache files used
- `Lng_Lat_Hash.json` for geocoding cache
- `distance_hash.json` for driving-distance cache

## Workflow 2: Walk List Generation (Second Most Important)

### Script
- [make_walk_lists.py](../make_walk_lists.py)

### What it does
This is the starting workflow. It takes the GOP Data Center export and turns it into optimized walk lists.

The script:
- normalizes address data into `CompleteAddress`
- normalizes party values to `Rep`, `Dem`, or `Ind`
- groups repeated addresses together
- calculates distances from the first address
- builds walk-list batches based on `max_radius` and `max_houses`
- solves route order using both a nearest-neighbor approach and a TSP approximation

### Expected input
The source file can be Excel or CSV and should include the common columns listed above. `FirstName` and `LastName` are required for the final output. `Age`, `Party`, and `Distance` are optional.

### Output location
Walk list outputs are written to:
- `C:\Users\wjg\Python_Stuff\Completed_Walk_Lists`

### Output files
The workflow creates:
- individual walk-list Excel files in `Completed_Walk_Lists`
- `Summary_File.txt` in `Completed_Walk_Lists`

## Workflow 3: Driving Distance Sort (Third Most Important)

### Script
- [Driving_Distance_Sort.py](Driving_Distance_Sort.py)

### What it does
This workflow takes a source Excel file and sorts the rows by driving distance from the first address in the file.

The script:
- geocodes each address with Mapbox
- caches geocoding results in `Lng_Lat_Hash.json`
- calculates driving distance with Google Maps through `get_distance(...)`
- caches distance lookups in `distance_hash.json`
- sorts rows from closest to farthest based on driving distance

### Expected input
Use the original GOP Data Center Excel export or a related source file with the common columns listed above.

### Output location
The output is written in the same folder as the script:
- `C:\Users\wjg\Python_Stuff\First_Map_MapBox\Driving_Distance.xlsx`

### Output columns
The output workbook includes:
- `FirstName`
- `LastName`
- `FullStreetAddress`
- optional `PrimaryUnitNumber`
- `Zip`
- `Age`
- `Party`
- `lng`
- `lat`
- `distance_in_feet`

### Cache files
This workflow writes and reuses:
- `Lng_Lat_Hash.json` for Mapbox geocoding cache
- `distance_hash.json` for driving-distance cache

## Workflow 4: Radial Distance Sort (Least Important)

### Script
- [Radial_Distance_Sort.py](Radial_Distance_Sort.py)

### What it does
This workflow is similar to the driving sort workflow, but it sorts by straight-line distance from the first address instead of driving distance.

The script:
- geocodes each address with Mapbox
- caches geocoding results in `Lng_Lat_Hash.json`
- calculates straight-line distance using the Haversine formula
- sorts rows from closest to farthest based on radial distance

### Expected input
Use the original GOP Data Center Excel export or a related source file with the common columns listed above.

### Output location
The output is written in the same folder as the script:
- `C:\Users\wjg\Python_Stuff\First_Map_MapBox\Radial_Distance.xlsx`

### Output columns
The output workbook includes:
- `FirstName`
- `LastName`
- `FullStreetAddress`
- optional `PrimaryUnitNumber`
- `Zip`
- `Age`
- `Party`
- `lng`
- `lat`
- `distance_in_feet`

### Cache files
This workflow writes and reuses:
- `Lng_Lat_Hash.json` for Mapbox geocoding cache

## Mapbox API Token Setup

**Option A: Environment Variable (Recommended)**
```bash
# Windows Command Prompt
set MAPBOX_TOKEN=your_mapbox_token_here

# Windows PowerShell
$env:MAPBOX_TOKEN="your_mapbox_token_here"
```

**Option B: Enter Token When Prompted**
The scripts prompt for your token if `MAPBOX_TOKEN` is not set.

## Map Markers

### Script
- [Address2LngLat.py](Address2LngLat.py)

This script reads output files from the four workflows and populates `markers.json`.

End-to-end map flow:
1. Run one of the four workflows to produce an output workbook:
	- `Canvasser_Zones_Driving_Distance.xlsx`
	- walk-list output files in `Completed_Walk_Lists`
	- `Driving_Distance.xlsx`
	- `Radial_Distance.xlsx`
2. Provide that workbook to `Address2LngLat.py`.
3. `Address2LngLat.py` writes marker data to `markers.json`.
4. `index.html` reads `markers.json` and renders the map.

Use `Address2LngLat.py` when you want to update marker data for the map.

## Requirements

Install the Python packages used by these scripts:

```bash
pip install pandas requests openpyxl xlsxwriter networkx matplotlib
```

## Notes

- The distance workflows are designed to preserve the original row data while adding distance and geocoding fields.
- `distance_hash.json` and `Lng_Lat_Hash.json` are cache files. They speed up reruns, so you may want to keep them in Git only if you want the cached results versioned.
- The final map can be accessed at `https://map2canvass.com`.

