# ============================================================
# Script: extract_modis_terra_LST_ET_PET_NT_timeseries_safe.py
# Purpose:
#   - Loop through MODIS Terra LST, ET, PET HDF files across years
#   - Match Northern Territory (Australia) VIC boundaries
#   - Apply product-specific invalid value filtering
#   - Compute spatial averages per date
#   - Save ONE combined CSV file
#   - Gracefully handle unreadable/missing files
# ============================================================

import numpy as np
import os
import re
import pandas as pd
from datetime import datetime
from netCDF4 import Dataset

# ============================================================
# 1. VIC study area boundaries — Northern Territory, Australia
# ============================================================
vic_boundary = {
    "lat_min": -17.0,
    "lat_max": -10.9,
    "lon_min": 129.0,
    "lon_max": 138.0
}

# ============================================================
# 2. MODIS tile geometries — NT
# ============================================================

# --- ET / PET geometries ---
ET_GEOMETRIES = {
    "h31v10": [
        (148.984888131549, -19.9999999982039),
        (142.175397358673, -9.93527477182093),
        (131.530219601717, -9.97545162476126),
        (137.825020464527, -20.0385919212958)
    ],
    "h30v10": [
        (138.343110407867, -19.9999999982039),
        (132.020927894706, -9.93746671411948),
        (121.409671246333, -9.97449019926359),
        (127.219958378815, -20.0355981480789)
    ]
}

# --- LST&E geometries ---
LST_GEOMETRIES = {
    "h30v10": [
        (127.696886969706, -19.9958333333333),
        (138.338646470494, -19.9958333333333),
        (132.004612593373, -10.0041666666667),
        (121.850102567955, -10.0041666666667)
    ],
    "h31v10": [
        (138.338664206561, -19.9958333333333),
        (148.980423707348, -19.9958333333333),
        (142.159139542785, -10.0041666666667),
        (132.004629517367, -10.0041666666667)
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
# 4. Clip data to VIC boundary
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
# 6. Load MODIS variable safely
# ============================================================
def load_modis_variable(file_path, variable_name):
    try:
        with Dataset(file_path, "r") as hdf:
            data = hdf.variables[variable_name][:]
        return data, data.shape
    except Exception as e:
        print(f"⚠ Failed to read {variable_name} from {file_path}: {e}")
        return None, (0, 0)

# ============================================================
# 7. Process one product for a given date
# ============================================================
def process_product_for_date(files, base_dir, variable_name, geometries, valid_mask_func):
    all_valid = []

    for tile_name in geometries.keys():
        matches = [f for f in files if tile_name in f]
        if not matches:
            continue

        file_path = os.path.join(base_dir, matches[0])
        data, (n_rows, n_cols) = load_modis_variable(file_path, variable_name)
        if data is None:
            continue

        lat_array, lon_array = compute_lat_lon(geometries[tile_name], n_rows, n_cols)
        subset = filter_data_by_vic_boundary(data, lat_array, lon_array)
        valid = subset[valid_mask_func(subset)]

        if valid.size > 0:
            all_valid.append(valid)

    return np.mean(np.concatenate(all_valid)) if all_valid else np.nan

# ============================================================
# 8. Main processing
# ============================================================
def main():
    lst_dir = r"D:\WUR\NASA_ESDS\NT_AUS\MODISTerra_NT_LSurfT_Data"
    et_pet_dir = r"D:\WUR\NASA_ESDS\NT_AUS\MODISTerra_NT_ETData"
    output_csv = r"D:\WUR\NASA_ESDS\NT_AUS\MODIS_Terra_LST_ET_PET_NT.csv"

    all_files = (
        [(lst_dir, f) for f in os.listdir(lst_dir) if f.endswith(".hdf")] +
        [(et_pet_dir, f) for f in os.listdir(et_pet_dir) if f.endswith(".hdf")]
    )

    files_by_date = {}
    for base_dir, fname in all_files:
        date = extract_date_from_filename(fname)
        if date:
            files_by_date.setdefault(date, []).append((base_dir, fname))

    print(f"Found {len(files_by_date)} unique dates.\n")
    results = []

    for date in sorted(files_by_date.keys()):
        print(f"Processing date: {date}")
        files = files_by_date[date]

        lst_files = [f for d, f in files if d == lst_dir]
        et_pet_files = [f for d, f in files if d == et_pet_dir]

        avg_lst = process_product_for_date(
            lst_files, lst_dir, "LST_Day_1km", LST_GEOMETRIES, lambda x: x > 0
        )
        avg_et = process_product_for_date(
            et_pet_files, et_pet_dir, "ET_500m", ET_GEOMETRIES, lambda x: x <= 10000
        )
        avg_pet = process_product_for_date(
            et_pet_files, et_pet_dir, "PET_500m", ET_GEOMETRIES, lambda x: x <= 10000
        )

        print(f"  LST: {avg_lst:.2f} | ET: {avg_et:.2f} | PET: {avg_pet:.2f}\n")

        results.append({
            "Date": date,
            "Average_LST": avg_lst,
            "Average_ET": avg_et,
            "Average_PET": avg_pet
        })

    df = pd.DataFrame(results)
    df.sort_values("Date", inplace=True)
    df.to_csv(output_csv, index=False)

    print(f"✅ Combined MODIS Terra NT LST–ET–PET time series saved to:\n{output_csv}")

# ============================================================
# 9. Run script
# ============================================================
if __name__ == "__main__":
    main()