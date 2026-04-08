# ============================================================
# Script: extract_viirs_LST_ET_PET_BKJ_timeseries.py
# Purpose:
#   - Loop through VIIRS LST, ET, PET HDF5 files across years
#   - Match VIC boundaries (Bornean Karst Jungle)
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
import h5py

# ============================================================
# 1. VIC study area boundaries — BORNEAN KARST JUNGLE (BKJ)
# ============================================================
vic_boundary = {
    "lat_min": 3.05,
    "lat_max": 4.29,
    "lon_min": 114.86,
    "lon_max": 115.50
}

# ============================================================
# 2. VIIRS tile grid geometry — SINGLE GRANULE (h30v08)
# ============================================================
grid_geometries = {
    "h29v08": [
        (109.5885, 0.0005),     # bottom-left
        (120.0192, -0.0112),    # bottom-right
        (121.8612, 9.9998),     # top-right
        (111.2665, 10.0097)     # top-left
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
# 5. Extract date from filename (AYYYYDDD)
# ============================================================
def extract_date_from_filename(filename):
    match = re.search(r"A(\d{4})(\d{3})", filename)
    if match:
        year = int(match.group(1))
        doy = int(match.group(2))
        return (datetime(year, 1, 1) + pd.to_timedelta(doy - 1, unit="D")).date()
    return None

# ============================================================
# 6. Load VIIRS variable
# ============================================================
def load_viirs_variable(file_path, product):
    if product == "LST":
        with Dataset(file_path, mode="r") as hdf:
            grid = (
                hdf.groups["HDFEOS"]
                   .groups["GRIDS"]
                   .groups["VIIRS_Grid_8Day_1km_LST21"]
                   .groups["Data Fields"]
            )
            data = grid.variables["LST_Day_1KM"][:]
    else:
        dataset_path = f"/HDFEOS/GRIDS/VIIRS_Grid_ETLE/Data Fields/{product}_500m"
        with h5py.File(file_path, "r") as hdf:
            data = hdf[dataset_path][:]

    return data, data.shape

# ============================================================
# 7. Process one product for a given date
# ============================================================
def process_product_for_date(files, base_dir, product, valid_mask_func):
    all_valid = []

    for grid_name in ["h29v08"]:
        matches = [f for f in files if grid_name in f]
        if not matches:
            continue

        file_path = os.path.join(base_dir, matches[0])

        try:
            data, (n_rows, n_cols) = load_viirs_variable(file_path, product)
        except Exception as e:
            print(f"⚠ WARNING: failed to read {product} from {matches[0]} ({e})")
            continue

        lat_array, lon_array = compute_lat_lon(
            grid_geometries[grid_name], n_rows, n_cols
        )

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

    lst_dir = r"D:\WUR\NASA_ESDS\BKJ\VIIRS_NPP_BKJ_LSurfT_Data"
    et_pet_dir = r"D:\WUR\NASA_ESDS\BKJ\VIIRS_NPP_BKJ_ETData"
    output_csv = r"D:\WUR\NASA_ESDS\BKJ\VIIRS_NPP_LST_ET_PET_timeseries.csv"

    all_files = (
        [(lst_dir, f) for f in os.listdir(lst_dir) if f.endswith(".h5")] +
        [(et_pet_dir, f) for f in os.listdir(et_pet_dir) if f.endswith(".h5")]
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

    df = pd.DataFrame(results)
    df.sort_values("Date", inplace=True)
    df.to_csv(output_csv, index=False)

    print(f"\n✅ Combined VIIRS LST–ET–PET time series saved to:\n{output_csv}")

# ============================================================
# 9. Run script
# ============================================================
if __name__ == "__main__":
    main()