# ============================================================
# Script: VIIRS_NPP_LST_ET_PET_Pantanal.py
# Purpose:
#   - Loop through VIIRS LST, ET, PET files for Pantanal region
#   - Apply VIC boundary mask
#   - Apply product-specific valid-value filters
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
# 1. VIC study area boundaries (Pantanal)
# ============================================================
vic_boundary = {
    "lat_min": -18.5,
    "lat_max": -16.5,
    "lon_min": -59.5,
    "lon_max": -56.0
}

# ============================================================
# 2. Pantanal VIIRS granule boundary (only 1 tile)
# ============================================================
grid_geometry = [
    (-63.8507, -20),
    (-52.9886, -20.0151),
    (-50.5717, -9.9674),
    (-60.9332, -9.9517),
    (-63.8507, -20)
]

# ============================================================
# 3. Compute lat/lon arrays
# ============================================================
def compute_lat_lon(boundary_points, n_rows, n_cols):
    # Linear interpolation along rows/cols
    bl, br, tr, tl, _ = boundary_points
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
# 4. Filter by VIC boundary
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
    """
    Load a single variable.
    LST -> NetCDF4
    ET/PET -> HDF5 per variable to avoid sync read error
    """
    if product == "LST":
        with Dataset(file_path, mode="r") as hdf:
            grid = hdf.groups["HDFEOS"].groups["GRIDS"].groups["VIIRS_Grid_8Day_1km_LST21"].groups["Data Fields"]
            data = grid.variables["LST_Day_1KM"][:]
    else:  # ET or PET
        dataset_path = f"/HDFEOS/GRIDS/VIIRS_Grid_ETLE/Data Fields/{product}_500m"
        data = None
        try:
            with h5py.File(file_path, "r") as hdf:
                if dataset_path in hdf:
                    data = hdf[dataset_path][()]  # load variable safely
        except Exception as e:
            print(f"⚠ Failed to read {product} from {file_path}: {e}")
    if data is None:
        return None, (0, 0)
    return data, data.shape

# ============================================================
# 7. Process a product for a date
# ============================================================
def process_product(file_path, product, valid_mask_func):
    if not os.path.exists(file_path):
        return np.nan

    data, (n_rows, n_cols) = load_viirs_variable(file_path, product)
    if data is None:
        return np.nan

    lat_array, lon_array = compute_lat_lon(grid_geometry, n_rows, n_cols)
    subset = filter_data_by_vic_boundary(data, lat_array, lon_array)
    valid = subset[valid_mask_func(subset)]

    if valid.size > 0:
        return np.mean(valid)
    else:
        return np.nan

# ============================================================
# 8. Main processing
# ============================================================
def main():
    lst_dir = r"D:\WUR\NASA_ESDS\Pantanal\VIIRS_NPP_Pantanal_LSurfT_Data"
    et_pet_dir = r"D:\WUR\NASA_ESDS\Pantanal\VIIRS_NPP_PantanalETData"
    output_csv = r"D:\WUR\NASA_ESDS\Pantanal\VIIRS_NPP_LST_ET_PET_timeseries.csv"

    # Collect files
    lst_files = [f for f in os.listdir(lst_dir) if f.endswith(".h5")]
    et_pet_files = [f for f in os.listdir(et_pet_dir) if f.endswith(".h5")]

    # Group files by date
    files_by_date = {}
    for f in lst_files + et_pet_files:
        date = extract_date_from_filename(f)
        if date:
            files_by_date.setdefault(date, []).append(f)

    print(f"Found {len(files_by_date)} unique dates.\n")
    results = []

    for date in sorted(files_by_date.keys()):
        print(f"Processing {date}")
        lst_file  = next((f for f in lst_files if extract_date_from_filename(f)==date), None)
        et_file   = next((f for f in et_pet_files if extract_date_from_filename(f)==date), None)
        pet_file  = next((f for f in et_pet_files if extract_date_from_filename(f)==date), None)

        avg_lst  = process_product(os.path.join(lst_dir, lst_file), "LST", lambda x: x > 0) if lst_file else np.nan
        avg_et   = process_product(os.path.join(et_pet_dir, et_file), "ET", lambda x: x <= 10000) if et_file else np.nan
        avg_pet  = process_product(os.path.join(et_pet_dir, pet_file), "PET", lambda x: x <= 10000) if pet_file else np.nan

        print(f"  LST: {avg_lst:.2f} | ET: {avg_et:.2f} | PET: {avg_pet:.2f}\n")

        results.append({
            "Date": date,
            "Average_LST": avg_lst,
            "Average_ET": avg_et,
            "Average_PET": avg_pet
        })

    # Save CSV
    df = pd.DataFrame(results)
    df.sort_values("Date", inplace=True)
    df.to_csv(output_csv, index=False)
    print(f"\n✅ Combined VIIRS Pantanal LST–ET–PET time series saved to:\n{output_csv}")

# ============================================================
# 9. Run script
# ============================================================
if __name__ == "__main__":
    main()
