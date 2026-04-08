# ============================================================
# Script: extract_modis_LST_timeseries.py
# Purpose: Loop through MODIS Terra LST 1km HDF files across years
#          Match VIC boundaries, remove fill values (=0),
#          compute average LST per date, and save as CSV
# ============================================================

import numpy as np
import os
import re
import pandas as pd
from datetime import datetime
from netCDF4 import Dataset  # Reads MODIS HDF4

# -------------------------------
# 1. Define VIC study area boundaries
# -------------------------------
vic_boundary = {
    "lat_min": 8.54167,
    "lat_max": 11.4583,
    "lon_min": 104.042,
    "lon_max": 106.958
}

# -------------------------------
# 2. Define satellite grid geometries (unchanged)
# -------------------------------
grid_geometries = {
    "h28v08": [
        (99.6259, 0.0004),
        (110.0184, -0.0102),
        (111.7068, 9.9998),
        (101.1513, 10.0088)
    ],
    "h28v07": [
        (101.1705, 9.9726),
        (111.7183, 9.9416),
        (117.0729, 19.9995),
        (106.0116, 20.0297)
    ]
}

# -------------------------------
# 3. Compute lat/lon arrays
# -------------------------------
def compute_lat_lon(boundary_points, n_rows, n_cols):
    bl, br, tr, tl = boundary_points
    t = np.linspace(0, 1, n_rows)[:, None]
    s = np.linspace(0, 1, n_cols)[None, :]

    left_lon = bl[0] + t * (tl[0] - bl[0])
    left_lat = bl[1] + t * (tl[1] - bl[1])
    right_lon = br[0] + t * (tr[0] - br[0])
    right_lat = br[1] + t * (tr[1] - br[1])

    lon_array = left_lon + s * (right_lon - left_lon)
    lat_array = left_lat + s * (right_lat - left_lat)
    return lat_array, lon_array

# -------------------------------
# 4. Load LST data (corrected)
# -------------------------------
def load_lst_data(file_path):
    """Load LST_Day_1km from MODIS HDF (variables are at root)."""
    with Dataset(file_path, mode='r') as hdf:
        data = hdf.variables["LST_Day_1km"][:]   # correct final location of data
    return data, data.shape

# -------------------------------
# 5. Filter by VIC boundary
# -------------------------------
def filter_data_by_vic_boundary(data, lat_array, lon_array, vic_boundary):
    mask = (
        (lat_array >= vic_boundary["lat_min"]) &
        (lat_array <= vic_boundary["lat_max"]) &
        (lon_array >= vic_boundary["lon_min"]) &
        (lon_array <= vic_boundary["lon_max"])
    )
    return data[mask]

# -------------------------------
# 6. Extract date from filename
# -------------------------------
def extract_date_from_filename(filename):
    match = re.search(r"A(\d{4})(\d{3})", filename)
    if match:
        year = int(match.group(1))
        doy = int(match.group(2))
        return (datetime(year, 1, 1) + pd.to_timedelta(doy - 1, unit='D')).date()
    return None

# -------------------------------
# 7. Main processing loop
# -------------------------------
def main():

    base_dir = r"D:\WUR\NASA_ESDS\MODISAqua_Mekong_LST&E_Data_F19"
    output_csv = os.path.join(base_dir, "MODIS_Aqua_LST_timeseries.csv")

    results = []

    # Load only .hdf files
    all_files = [f for f in os.listdir(base_dir) if f.endswith(".hdf")]

    # Group by date
    dates = {}
    for f in all_files:
        date = extract_date_from_filename(f)
        if date:
            dates.setdefault(date, []).append(f)

    print(f"Found {len(dates)} unique dates.\n")

    # Process each date
    for date, files in sorted(dates.items()):
        print(f"Processing date: {date}")
        all_valid = []

        for grid_name in ["h28v07", "h28v08"]:

            matches = [f for f in files if grid_name in f]
            if not matches:
                continue

            file_path = os.path.join(base_dir, matches[0])

            # Load data
            data, (n_rows, n_cols) = load_lst_data(file_path)

            # Expect 1200×1200
            if (n_rows, n_cols) != (1200, 1200):
                print(f"Warning: unexpected grid size {data.shape}")

            # Compute lat/lon grid
            lat_array, lon_array = compute_lat_lon(grid_geometries[grid_name], n_rows, n_cols)

            # Spatially filter
            subset = filter_data_by_vic_boundary(data, lat_array, lon_array, vic_boundary)

            # Fill values for LST = 0 → invalid
            valid = subset[subset > 0]

            if valid.size > 0:
                all_valid.append(valid)

        # Compute statistics
        if all_valid:
            combined = np.concatenate(all_valid)
            avg_lst = np.mean(combined)

            print(f"  Average LST: {avg_lst:.2f}")
            results.append({"Date": date, "Average_LST": avg_lst})
        else:
            print("  No valid data for this date.\n")

    # Save CSV
    df = pd.DataFrame(results)
    df.sort_values("Date", inplace=True)
    df.to_csv(output_csv, index=False)

    print(f"\n✅ Saved MODIS Aqua LST time series to {output_csv}")

# -------------------------------
# 8. Run script
# -------------------------------
if __name__ == "__main__":
    main()
