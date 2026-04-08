# ============================================================
# Script: extract_modis_terra_LST_ET_PET_combined_timeseries.py
# Purpose:
#   - Loop through MODIS Terra LST, ET, PET HDF files across years
#   - Match VIC boundaries
#   - Apply product-specific invalid value filtering
#   - Compute spatial averages per date
#   - Save ONE combined CSV file
# ============================================================

import numpy as np
import os
import re
import pandas as pd
from datetime import datetime
from netCDF4 import Dataset

# ============================================================
# 1. VIC study area boundaries
# ============================================================
vic_boundary = {
    "lat_min": 8.54167,
    "lat_max": 11.4583,
    "lon_min": 104.042,
    "lon_max": 106.958
}

# ============================================================
# 2. MODIS tile grid geometries
# ============================================================
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

# ============================================================
# 3. Compute lat/lon arrays for a tile
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
# 4. Filter data by VIC boundary
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
# 5. Extract date from MODIS filename (AYYYYDDD)
# ============================================================
def extract_date_from_filename(filename):
    match = re.search(r"A(\d{4})(\d{3})", filename)
    if match:
        year = int(match.group(1))
        doy = int(match.group(2))
        return (datetime(year, 1, 1) + pd.to_timedelta(doy - 1, unit="D")).date()
    return None

# ============================================================
# 6. Load MODIS variable
# ============================================================
def load_modis_variable(file_path, variable_name):
    with Dataset(file_path, mode="r") as hdf:
        data = hdf.variables[variable_name][:]
    return data, data.shape

# ============================================================
# 7. Process one product for a given date
# ============================================================
def process_product_for_date(files, base_dir, variable_name, valid_mask_func):
    all_valid = []

    for grid_name in ["h28v07", "h28v08"]:
        matches = [f for f in files if grid_name in f]
        if not matches:
            continue

        file_path = os.path.join(base_dir, matches[0])
        data, (n_rows, n_cols) = load_modis_variable(file_path, variable_name)

        lat_array, lon_array = compute_lat_lon(grid_geometries[grid_name], n_rows, n_cols)
        subset = filter_data_by_vic_boundary(data, lat_array, lon_array)
        valid = subset[valid_mask_func(subset)]

        if valid.size > 0:
            all_valid.append(valid)

    if all_valid:
        return np.mean(np.concatenate(all_valid))
    else:
        return np.nan

# ============================================================
# 8. Main processing
# ============================================================
def main():

    # ----------------------------
    # Directories for Terra products
    # ----------------------------
    lst_dir = r"D:\WUR\NASA_ESDS\MODISTerra_Mekong_LST&E_Data_F19"
    et_pet_dir = r"D:\WUR\NASA_ESDS\MODISTerra_MekongETData_F19"

    output_csv = os.path.join(lst_dir, "MODIS_Terra_LST_ET_PET_timeseries.csv")

    # ----------------------------
    # Collect all HDF files
    # ----------------------------
    all_files = (
        [(lst_dir, f) for f in os.listdir(lst_dir) if f.endswith(".hdf")] +
        [(et_pet_dir, f) for f in os.listdir(et_pet_dir) if f.endswith(".hdf")]
    )

    # ----------------------------
    # Group files by date
    # ----------------------------
    files_by_date = {}
    for base_dir, fname in all_files:
        date = extract_date_from_filename(fname)
        if date:
            files_by_date.setdefault(date, []).append((base_dir, fname))

    print(f"Found {len(files_by_date)} unique dates.\n")
    results = []

    # ----------------------------
    # Process each date
    # ----------------------------
    for date in sorted(files_by_date.keys()):
        print(f"Processing date: {date}")

        files = files_by_date[date]

        lst_files = [f for d, f in files if d == lst_dir]
        et_pet_files = [f for d, f in files if d == et_pet_dir]

        avg_lst = process_product_for_date(lst_files, lst_dir, "LST_Day_1km", lambda x: x > 0)
        avg_et = process_product_for_date(et_pet_files, et_pet_dir, "ET_500m", lambda x: x <= 10000)
        avg_pet = process_product_for_date(et_pet_files, et_pet_dir, "PET_500m", lambda x: x <= 10000)

        print(f"  LST: {avg_lst:.2f} | ET: {avg_et:.2f} | PET: {avg_pet:.2f}\n")

        results.append({
            "Date": date,
            "Average_LST": avg_lst,
            "Average_ET": avg_et,
            "Average_PET": avg_pet
        })

    # ----------------------------
    # Save combined CSV
    # ----------------------------
    df = pd.DataFrame(results)
    df.sort_values("Date", inplace=True)
    df.to_csv(output_csv, index=False)
    print(f"✅ Combined MODIS Terra LST–ET–PET time series saved to:\n{output_csv}")

# ============================================================
# 9. Run script
# ============================================================
if __name__ == "__main__":
    main()