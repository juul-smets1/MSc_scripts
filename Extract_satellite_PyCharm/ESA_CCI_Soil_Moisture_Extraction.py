import os
import glob
import re
from datetime import datetime
import pandas as pd
import xarray as xr

# Base directory containing the year folders
base_dir = r'D:\WUR\ESA_CCI_Soil_Moisture'

print("Searching for NetCDF files...")
nc_files = glob.glob(os.path.join(base_dir, '**', '*.nc'), recursive=True)
print(f"Found {len(nc_files)} .nc files.\n")

# Define regions
regions = [
    {
        'name': 'Pantanal_Brazil_Bolivia',
        'lon_min': -59.5, 'lon_max': -56.0,
        'lat_min': -18.5, 'lat_max': -16.5
    },
    {
        'name': 'South_Eastern_Central_Africa',
        'lon_min': 17.0, 'lon_max': 28.0,
        'lat_min': -22.5, 'lat_max': -15.5
    },
    {
        'name': 'Bornean_Karst_Jungle_Malaysia',
        'lon_min': 114.86, 'lon_max': 115.5,
        'lat_min': 3.05, 'lat_max': 4.29
    },
    {
        'name': 'Yucatan_Peninsula_Mexico_Belize_Guatemala',
        'lon_min': -91.0, 'lon_max': -86.6,
        'lat_min': 16.0, 'lat_max': 21.7
    },
    {
        'name': 'Northern_Territory_Australia',
        'lon_min': 129.0, 'lon_max': 138.0,
        'lat_min': -17.0, 'lat_max': -10.9
    }
]

# Initialize data storage
data = {region['name']: [] for region in regions}

# Regex to extract YYYYMMDD from filename
date_pattern = re.compile(r'ESACCI-SOILMOISTURE-L3S-SSMV-COMBINED_GAPFILLED-(\d{8})000000-fv09\.1r1')

print("Starting processing of daily NetCDF files...\n")

# Process each file in chronological order
for i, file_path in enumerate(sorted(nc_files), 1):
    filename = os.path.basename(file_path)

    # Show progress every 100 files
    if i % 100 == 0 or i == 1 or i == len(nc_files):
        print(f"Processing file {i}/{len(nc_files)}: {filename}")

    # Extract date from filename
    match = date_pattern.search(filename)
    if not match:
        print(f"  → Skipping (filename does not match pattern): {filename}")
        continue

    date_str = match.group(1)
    try:
        date_obj = datetime.strptime(date_str, '%Y%m%d').date()
    except ValueError:
        print(f"  → Skipping (invalid date in filename): {filename}")
        continue

    # Open NetCDF file
    try:
        ds = xr.open_dataset(file_path)
        if 'sm' not in ds.variables:
            print(f"  → Warning: 'sm' variable not found in {filename}")
            ds.close()
            continue
        sm = ds['sm']
    except Exception as e:
        print(f"  → Error opening {filename}: {e}")
        continue

    # Check if latitude is decreasing (common in ESA CCI SM: 89.875 to -89.875)
    lat_decreasing = ds.lat[0] > ds.lat[-1] if 'lat' in ds.coords else False
    print(f"  → Latitude coordinate is {'decreasing' if lat_decreasing else 'increasing'}")

    # Process each region
    valid_regions_this_day = 0
    for region in regions:
        try:
            # Adjust latitude slice based on coordinate order
            lat_start = region['lat_max'] if lat_decreasing else region['lat_min']
            lat_stop = region['lat_min'] if lat_decreasing else region['lat_max']
            lat_slice = slice(lat_start, lat_stop)

            # Longitude is assumed increasing (-179.875 to 179.875)
            lon_slice = slice(region['lon_min'], region['lon_max'])

            # Select spatial subset
            selected = sm.sel(lat=lat_slice, lon=lon_slice)

            # For debugging: print shape of selected area
            print(f"    Region {region['name']}: Selected shape {selected.shape}")

            # Compute spatial mean (ignoring NaNs)
            mean_sm = float(selected.mean(skipna=True).values)

            # Only append if there's at least one valid pixel
            if not pd.isna(mean_sm):
                data[region['name']].append((date_obj, mean_sm))
                valid_regions_this_day += 1
            else:
                print(f"    Region {region['name']}: Mean is NaN (all data missing or empty selection)")

        except Exception as e:
            print(f"  → Error in region {region['name']} for {date_str}: {e}")
            continue

    ds.close()

    # Brief summary per file
    if valid_regions_this_day == 0:
        print(f"  → No valid data extracted for any region on {date_str}")

print("\n" + "=" * 60)
print("Processing complete!")
print("=" * 60)

# Summary of extracted data
print("Data summary per region:")
for region_name in data:
    num_days = len(data[region_name])
    if num_days > 0:
        dates = [d for d, _ in data[region_name]]
        print(f"  {region_name}: {num_days} days (from {min(dates)} to {max(dates)})")
    else:
        print(f"  {region_name}: No data extracted")

# Write to Excel file with one sheet per region in the specified directory
output_dir = r'D:\WUR\ESA_CCI_Soil_Moisture'
output_file = os.path.join(output_dir, 'soil_moisture_data.xlsx')

print(f"\nWriting results to '{output_file}'...")

with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    for region_name, entries in data.items():
        if not entries:
            print(f"  → No data for {region_name}, skipping sheet")
            continue

        df = pd.DataFrame(entries, columns=['date', 'soil_moisture'])
        df = df.sort_values('date').reset_index(drop=True)

        # Format date nicely
        df['date'] = pd.to_datetime(df['date'])

        sheet_name = region_name[:31]  # Excel sheet names max 31 chars
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"  → Sheet '{sheet_name}' written ({len(df)} rows)")

print(f"\nDone! Excel file saved as: {os.path.abspath(output_file)}")