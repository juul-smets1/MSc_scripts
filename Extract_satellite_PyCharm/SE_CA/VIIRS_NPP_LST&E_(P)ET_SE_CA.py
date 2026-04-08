# ============================================================
# Script: extract_viirs_LST_ET_PET_SECA_timeseries.py
# Purpose:
#   - Loop through VIIRS NPP LST, ET, PET HDF5 files
#   - Handle multiple granules per date (Africa tiles)
#   - Clip to SE/Central Africa VIC boundary
#   - Compute spatial averages per date
#   - Save ONE combined CSV
# ============================================================

import numpy as np
import os
import re
import pandas as pd
from datetime import datetime
from netCDF4 import Dataset
import h5py

# ============================================================
# 1. VIC boundary — SE / Central Africa
# ============================================================
vic_boundary = {
    "lat_min": -22.5,
    "lat_max": -15.5,
    "lon_min": 17.0,
    "lon_max": 28.0
}

# ============================================================
# 2. VIIRS granule geometries (Africa)
# ============================================================
granule_geometries = {
    "h19v11": [
        (11.4987, -30.008),
        (23.1013, -29.9997),
        (21.2877, -19.916),
        (10.5996, -19.9237)
    ],
    "h19v10": [
        (10.5988, -20.0045),
        (21.2910, -19.9998),
        (20.3182, -9.9589),
        (10.1165, -9.9635)
    ],
    "h20v11": [
        (23.0001, -30.0129),
        (34.6472, -29.9997),
        (31.9280, -19.913),
        (21.1986, -19.9254)
    ],
    "h20v10": [
        (21.1986, -20.0072),
        (31.9321, -19.9998),
        (30.4737, -9.9571),
        (20.2324, -9.9645)
    ]
}

# ============================================================
# 3. Compute lat/lon grid
# ============================================================
def compute_lat_lon(boundary_points, n_rows, n_cols):
    bl, br, tr, tl = boundary_points
    t = np.linspace(0, 1, n_rows)[:, None]
    s = np.linspace(0, 1, n_cols)[None, :]

    left_lon = bl[0] + t * (tl[0] - bl[0])
    left_lat = bl[1] + t * (tl[1] - bl[1])
    right_lon = br[0] + t * (tr[0] - br[0])
    right_lat = br[1] + t * (tr[1] - br[1])

    lon = left_lon + s * (right_lon - left_lon)
    lat = left_lat + s * (right_lat - left_lat)

    return lat, lon

# ============================================================
# 4. Clip to VIC boundary
# ============================================================
def clip_to_vic(data, lat, lon):
    mask = (
        (lat >= vic_boundary["lat_min"]) &
        (lat <= vic_boundary["lat_max"]) &
        (lon >= vic_boundary["lon_min"]) &
        (lon <= vic_boundary["lon_max"])
    )
    return data[mask]

# ============================================================
# 5. Extract date from filename
# ============================================================
def extract_date_from_filename(filename):
    match = re.search(r"A(\d{4})(\d{3})", filename)
    if not match:
        return None
    year = int(match.group(1))
    doy = int(match.group(2))
    return (datetime(year, 1, 1) + pd.to_timedelta(doy - 1, unit="D")).date()

# ============================================================
# 6. Load VIIRS variable
# ============================================================
def load_viirs_variable(file_path, product):
    if product == "LST":
        with Dataset(file_path, "r") as hdf:
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
# 7. Process one product for one date
# ============================================================
def process_product_for_date(files, base_dir, product, valid_mask):
    all_valid = []

    for fname in files:
        tile = next((t for t in granule_geometries if t in fname), None)
        if tile is None:
            continue

        file_path = os.path.join(base_dir, fname)

        try:
            data, (n_rows, n_cols) = load_viirs_variable(file_path, product)
        except Exception as e:
            print(f"⚠ Failed to read {product} from {fname}: {e}")
            continue

        lat, lon = compute_lat_lon(
            granule_geometries[tile], n_rows, n_cols
        )

        subset = clip_to_vic(data, lat, lon)
        valid = subset[valid_mask(subset)]

        if valid.size > 0:
            all_valid.append(valid)

    return np.mean(np.concatenate(all_valid)) if all_valid else np.nan

# ============================================================
# 8. Main processing
# ============================================================
def main():

    lst_dir = r"D:\WUR\NASA_ESDS\SE_CA\VIIRS_NPP_SECA_LSurfT_Data"
    et_dir  = r"D:\WUR\NASA_ESDS\SE_CA\VIIRS_NPP_SECA_ETData"
    out_csv = r"D:\WUR\NASA_ESDS\SE_CA\VIIRS_NPP_LST_ET_PET_SECA.csv"

    all_files = (
        [(lst_dir, f) for f in os.listdir(lst_dir) if f.endswith(".h5")] +
        [(et_dir, f) for f in os.listdir(et_dir) if f.endswith(".h5")]
    )

    files_by_date = {}
    for base, fname in all_files:
        date = extract_date_from_filename(fname)
        if date:
            files_by_date.setdefault(date, []).append((base, fname))

    print(f"Found {len(files_by_date)} unique dates.\n")
    results = []

    for date in sorted(files_by_date):
        print(f"Processing {date}")

        files = files_by_date[date]
        lst_files = [f for d, f in files if d == lst_dir]
        et_files  = [f for d, f in files if d == et_dir]

        avg_lst = process_product_for_date(
            lst_files, lst_dir, "LST", lambda x: x > 0
        )

        avg_et = process_product_for_date(
            et_files, et_dir, "ET", lambda x: x <= 10000
        )

        avg_pet = process_product_for_date(
            et_files, et_dir, "PET", lambda x: x <= 10000
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
    df.to_csv(out_csv, index=False)

    print(f"✅ Saved VIIRS SE/CA LST–ET–PET time series to:\n{out_csv}")

# ============================================================
# 9. Run
# ============================================================
if __name__ == "__main__":
    main()