# ============================================================
# Script: extract_modis_aqua_LST_ET_PET_BKJ_timeseries.py
# Purpose:
#   - Loop through MODIS Aqua LST, ET, PET HDF files across years
#   - Match VIC boundaries (Bornean Karst Jungle, Malaysia)
#   - Compute raw spatial averages per date (no scaling)
#   - Apply product-specific invalid value filtering like Mekong
#   - Save ONE combined CSV file
#   - Warning flags for missing/corrupt files or no valid pixels
# ============================================================

import numpy as np
import os
import re
import pandas as pd
from datetime import datetime
from netCDF4 import Dataset

# ============================================================
# 1. VIC study area boundaries — BKJ
# ============================================================
vic_boundary = {
    "lat_min": 3.05,
    "lat_max": 4.29,
    "lon_min": 114.86,
    "lon_max": 115.5
}

# ============================================================
# 2. MODIS tile grid geometries — separate for LST&E and ET
# ============================================================
grid_geometries = {
    # LST&E granule
    "h29v08_lst": [
        (109.995843579946, 0.00416666666666217),
        (119.995827169535, 0.00416666666666217),
        (121.846940515072, 9.99583333333334),
        (111.692691623892, 9.99583333333334)
    ],
    # ET granule
    "h29v08_et": [
        (120.019225310458, -0.0111963919892759),
        (121.861189186147, 9.99983232251618),
        (111.266536446994, 10.0096696280556),
        (109.588511675333, 0.000462182365887258)
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
# 6. Load raw MODIS variable (no scaling applied)
# ============================================================
def load_modis_variable(file_path, variable_name):
    try:
        with Dataset(file_path, mode="r") as hdf:
            data = hdf.variables[variable_name][:]
            return data, data.shape
    except Exception as e:
        print(f"⚠ WARNING: Could not read '{variable_name}' from {file_path} ({e})")
        return None, (0, 0)

# ============================================================
# 7. Process one product for a given date (Mekong-style)
# ============================================================
def process_product_for_date(files, base_dir, product, valid_mask_func):
    all_valid = []

    # Assign grid geometry key and variable name
    if product == "LST":
        grid_key = "h29v08_lst"
        variable_name = "LST_Day_1km"
    elif product in ["ET", "PET"]:
        grid_key = "h29v08_et"
        variable_name = f"{product}_500m"
    else:
        raise ValueError(f"Unknown product: {product}")

    # Only use h29v08 .hdf files
    matches = [f for f in files if "h29v08" in f and f.endswith(".hdf")]
    if not matches:
        print(f"⚠ WARNING: No {product} files for this date in {base_dir}")
        return np.nan

    file_path = os.path.join(base_dir, matches[0])
    data, (n_rows, n_cols) = load_modis_variable(file_path, variable_name)
    if data is None:
        return np.nan

    # Compute lat/lon for the granule
    lat_array, lon_array = compute_lat_lon(grid_geometries[grid_key], n_rows, n_cols)
    subset = filter_data_by_vic_boundary(data, lat_array, lon_array)

    # Mekong-style filtering to remove invalid values
    valid = subset[valid_mask_func(subset)]

    if valid.size == 0:
        print(f"⚠ No valid {product} values in VIC boundary for {matches[0]}")

    return np.mean(valid) if valid.size > 0 else np.nan

# ============================================================
# 8. Main processing
# ============================================================
def main():
    lst_dir = r"D:\WUR\NASA_ESDS\BKJ\MODISAqua_BKJ_LSurfT_Data"
    et_pet_dir = r"D:\WUR\NASA_ESDS\BKJ\MODISAqua_BKJ_ETData"
    output_csv = r"D:\WUR\NASA_ESDS\BKJ\MODIS_Aqua_BKJ_LST_ET_PET_timeseries.csv"

    # Collect only .hdf files
    all_files = (
        [(lst_dir, f) for f in os.listdir(lst_dir) if f.endswith(".hdf")] +
        [(et_pet_dir, f) for f in os.listdir(et_pet_dir) if f.endswith(".hdf")]
    )

    # Group files by date
    files_by_date = {}
    for base_dir, fname in all_files:
        date = extract_date_from_filename(fname)
        if date:
            files_by_date.setdefault(date, []).append((base_dir, fname))

    print(f"Found {len(files_by_date)} unique dates.\n")

    results = []

    # Process each date
    for date in sorted(files_by_date.keys()):
        print(f"Processing date: {date}")

        files = files_by_date[date]
        lst_files = [f for d, f in files if d == lst_dir]
        et_pet_files = [f for d, f in files if d == et_pet_dir]

        # === Mekong-style filtering applied here ===
        avg_lst = process_product_for_date(lst_files, lst_dir, "LST", lambda x: x > 0)
        avg_et = process_product_for_date(et_pet_files, et_pet_dir, "ET", lambda x: x <= 10000)
        avg_pet = process_product_for_date(et_pet_files, et_pet_dir, "PET", lambda x: x <= 10000)

        print(f"  LST: {avg_lst:.2f} | ET: {avg_et:.2f} | PET: {avg_pet:.2f}\n")

        results.append({
            "Date": date,
            "Average_LST": avg_lst,
            "Average_ET": avg_et,
            "Average_PET": avg_pet
        })

    # Save combined CSV
    df = pd.DataFrame(results)
    df.sort_values("Date", inplace=True)
    df.to_csv(output_csv, index=False)
    print(f"\n✅ Combined MODIS Aqua LST–ET–PET time series saved to:\n{output_csv}")

# ============================================================
# 9. Run
# ============================================================
if __name__ == "__main__":
    main()