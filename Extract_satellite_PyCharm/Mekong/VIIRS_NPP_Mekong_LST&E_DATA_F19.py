# ============================================================
# Script: extract_viirs_LST_timeseries.py
# Purpose: Loop through VIIRS-NPP 8-day LST HDF5 files
#          Match VIC boundaries, filter fill value (=0),
#          compute average LST per date, and save as CSV
# Methodology strictly follows original MODIS ET script
# ============================================================

import numpy as np
import os
import re
import pandas as pd
from datetime import datetime
from netCDF4 import Dataset  # can read HDF5/HDFEOS

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
# 2. Define VIIRS grid geometries (same as MODIS h28v07, h28v08)
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
# 4. Load VIIRS LST Day 1KM dataset
# -------------------------------
def load_lst_data(file_path):
    """Load LST_Day_1KM from VIIRS HDF5/HDFEOS file."""
    with Dataset(file_path, mode="r") as hdf:
        grid = (
            hdf.groups["HDFEOS"]
               .groups["GRIDS"]
               .groups["VIIRS_Grid_8Day_1km_LST21"]
               .groups["Data Fields"]
        )
        data = grid.variables["LST_Day_1KM"][:]
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
# 6. Extract AYYYYDDD date from filename
# -------------------------------
def extract_date_from_filename(filename):
    match = re.search(r"A(\d{4})(\d{3})", filename)
    if match:
        year = int(match.group(1))
        doy = int(match.group(2))
        return (datetime(year, 1, 1) + pd.to_timedelta(doy - 1, unit="D")).date()
    return None

# -------------------------------
# 7. Main processing loop
# -------------------------------
def main():

    base_dir = r"D:\WUR\NASA_ESDS\VIIRS_NPP_Mekong_LST&E_Data_F19"
    output_csv = os.path.join(base_dir, "VIIRS_NPP_LST_timeseries.csv")

    results = []

    # Load only .h5 files
    all_files = [f for f in os.listdir(base_dir) if f.endswith(".h5")]

    # Group files by date
    dates = {}
    for f in all_files:
        date = extract_date_from_filename(f)
        if date:
            dates.setdefault(date, []).append(f)

    print(f"Found {len(dates)} unique dates.\n")

    for date, files in sorted(dates.items()):
        print(f"Processing date: {date}")

        all_valid_pixels = []

        for grid_name in ["h28v07", "h28v08"]:

            matches = [f for f in files if grid_name in f]
            if not matches:
                continue

            file_path = os.path.join(base_dir, matches[0])

            data, (n_rows, n_cols) = load_lst_data(file_path)

            # Expect 1200×1200 VIIRS grid
            if (n_rows, n_cols) != (1200, 1200):
                print(f"Warning: unexpected grid size {data.shape}")

            lat_array, lon_array = compute_lat_lon(
                grid_geometries[grid_name], n_rows, n_cols
            )

            subset = filter_data_by_vic_boundary(
                data, lat_array, lon_array, vic_boundary
            )

            # VIIRS LST fill value = 0
            valid_pixels = subset[subset > 0]

            if valid_pixels.size > 0:
                all_valid_pixels.append(valid_pixels)

        # Compute regional average if data exists
        if all_valid_pixels:
            combined = np.concatenate(all_valid_pixels)
            avg_lst = np.mean(combined)
            print(f"  Average LST = {avg_lst:.2f}")
            results.append({"Date": date, "Average_LST": avg_lst})
        else:
            print("  No valid LST data for this date.\n")

    # Save CSV
    df = pd.DataFrame(results)
    df.sort_values("Date", inplace=True)
    df.to_csv(output_csv, index=False)

    print(f"\n✅ Saved VIIRS LST time series → {output_csv}")

# -------------------------------
# 8. Run script
# -------------------------------
if __name__ == "__main__":
    main()
