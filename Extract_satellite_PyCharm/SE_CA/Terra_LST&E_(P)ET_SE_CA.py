# ============================================================
# Script: extract_modis_terra_LST_ET_PET_SECA_timeseries_safe.py
# Purpose:
#   - Loop through MODIS Terra LST, ET, PET HDF files across years
#   - Match SE/CA VIC boundaries
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
# 1. VIC study area boundaries — SE / Central Africa
# ============================================================
vic_boundary = {
    "lat_min": -22.5,
    "lat_max": -15.5,
    "lon_min": 17.0,
    "lon_max": 28.0
}

# ============================================================
# 2. MODIS tile grid geometries for SE/CA
# ============================================================
ET_GEOMETRIES = {
    "h20v11": [(34.6472, -29.9997), (31.9280, -19.9130), (21.1986, -19.9254), (23.0001, -30.0129)],
    "h20v10": [(31.9321, -19.9998), (30.4737, -9.9571), (20.2324, -9.9645), (21.1986, -20.0072)],
    "h19v11": [(23.1013, -29.9997), (21.2877, -19.9160), (10.5996, -19.9237), (11.4987, -30.0080)],
    "h19v10": [(21.2910, -19.9998), (20.3182, -9.9589), (10.1165, -9.9635), (10.5988, -20.0045)]
}

LST_GEOMETRIES = {
    "h20v11": [(23.0892, -29.9958), (34.6362, -29.9958), (31.9226, -20.0042), (21.2803, -20.0042)],
    "h20v10": [(21.2791, -19.9958), (31.9209, -19.9958), (30.4593, -10.0042), (20.3048, -10.0042)],
    "h19v11": [(11.5422, -29.9958), (23.0892, -29.9958), (21.2802, -20.0042), (10.6379, -20.0042)],
    "h19v10": [(10.6373, -19.9958), (21.2791, -19.9958), (20.3048, -10.0042), (10.1503, -10.0042)]
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
# 6. Load MODIS variable with error handling
# ============================================================
def load_modis_variable(file_path, variable_name):
    try:
        with Dataset(file_path, mode="r") as hdf:
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
            continue  # skip unreadable file

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
    lst_dir = r"D:\WUR\NASA_ESDS\SE_CA\MODISTerra_SECA_LSurfT_Data"
    et_pet_dir = r"D:\WUR\NASA_ESDS\SE_CA\MODISTerra_SECA_ETData"
    output_csv = r"D:\WUR\NASA_ESDS\SE_CA\MODIS_Terra_LST_ET_PET_SECA.csv"

    # Collect all HDF files
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

        avg_lst = process_product_for_date(lst_files, lst_dir, "LST_Day_1km", LST_GEOMETRIES, lambda x: x > 0)
        avg_et = process_product_for_date(et_pet_files, et_pet_dir, "ET_500m", ET_GEOMETRIES, lambda x: x <= 10000)
        avg_pet = process_product_for_date(et_pet_files, et_pet_dir, "PET_500m", ET_GEOMETRIES, lambda x: x <= 10000)

        lst_str = f"{avg_lst:.2f}" if not np.isnan(avg_lst) else "nan"
        et_str = f"{avg_et:.2f}" if not np.isnan(avg_et) else "nan"
        pet_str = f"{avg_pet:.2f}" if not np.isnan(avg_pet) else "nan"

        print(f"  LST: {lst_str} | ET: {et_str} | PET: {pet_str}\n")

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
    print(f"✅ Combined MODIS Terra LST–ET–PET time series saved to:\n{output_csv}")

# ============================================================
# 9. Run script
# ============================================================
if __name__ == "__main__":
    main()