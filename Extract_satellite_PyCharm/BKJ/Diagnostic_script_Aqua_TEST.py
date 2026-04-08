# ============================================================
# Diagnostic script for MODIS Aqua LST — BKJ region
# ============================================================

import os
import re
import numpy as np
from netCDF4 import Dataset
from datetime import datetime, timedelta

# ============================================================
# VIC boundary — BKJ
# ============================================================
vic_boundary = {
    "lat_min": 3.05,
    "lat_max": 4.29,
    "lon_min": 114.86,
    "lon_max": 115.5
}

# ============================================================
# MODIS Aqua LST granule geometry (h29v08)
# ============================================================
grid_geometry = [
    (109.995843579946, 0.00416666666666217),
    (119.995827169535, 0.00416666666666217),
    (121.846940515072, 9.99583333333334),
    (111.692691623892, 9.99583333333334)
]

# ============================================================
# Directory with MODIS Aqua LST HDF files
# ============================================================
lst_dir = r"D:\WUR\NASA_ESDS\BKJ\MODISAqua_BKJ_LSurfT_Data"

# ============================================================
# Compute lat/lon arrays for a tile
# ============================================================
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

# ============================================================
# Filter data by VIC boundary
# ============================================================
def filter_data_by_vic_boundary(data, lat_array, lon_array):
    mask = (
        (lat_array >= vic_boundary["lat_min"]) &
        (lat_array <= vic_boundary["lat_max"]) &
        (lon_array >= vic_boundary["lon_min"]) &
        (lon_array <= vic_boundary["lon_max"])
    )
    return data[mask]

# ============================================================
# Extract date from MODIS filename
# ============================================================
def extract_date_from_filename(filename):
    match = re.search(r"A(\d{4})(\d{3})", filename)
    if match:
        year = int(match.group(1))
        doy = int(match.group(2))
        return datetime(year, 1, 1) + timedelta(days=doy-1)
    return None

# ============================================================
# Main diagnostic loop
# ============================================================
for fname in sorted(f for f in os.listdir(lst_dir) if f.endswith(".hdf")):
    file_path = os.path.join(lst_dir, fname)
    date = extract_date_from_filename(fname)
    if date is None:
        print(f"⚠ Could not parse date from filename: {fname}")
        continue

    print(f"\nChecking file: {fname} (Date: {date.date()})")

    try:
        with Dataset(file_path, "r") as hdf:
            if "LST_Day_1km" not in hdf.variables:
                print("  ⚠ Variable 'LST_Day_1km' NOT found in file!")
                continue

            data = hdf.variables["LST_Day_1km"][:]
            print(f"  Shape of LST array: {data.shape}")
            print(f"  Min/Max before filtering: {np.nanmin(data)}, {np.nanmax(data)}")

            n_rows, n_cols = data.shape
            lat_array, lon_array = compute_lat_lon(grid_geometry, n_rows, n_cols)
            subset = filter_data_by_vic_boundary(data, lat_array, lon_array)
            print(f"  Subset size after VIC boundary: {subset.size}")

            if np.any(subset > 0):
                print("  ✅ Valid LST values exist in VIC boundary!")
            else:
                print("  ⚠ No valid LST values (>0) in VIC boundary")

    except Exception as e:
        print(f"  ⚠ Could not open/read file: {e}")