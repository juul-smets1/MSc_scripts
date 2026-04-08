# ============================================================
# Script: extract_viirs_LST_ET_PET_NT_timeseries.py
# Purpose:
# - Loop through VIIRS NPP LST (VNP21A2 Collection 2), ET/PET HDF5 files
# - Handle multiple granules per date (Northern Territory tiles: h30v10, h31v10)
# - Clip to Northern Territory VIC boundary
# - Compute spatial averages per date (using Day LST)
# - Save ONE combined CSV
# ============================================================

import numpy as np
import os
import re
import pandas as pd
from datetime import datetime
import h5py

# ============================================================
# 1. VIC boundary — Northern Territory (Australia)
# ============================================================
vic_boundary = {
    "lat_min": -17.0,
    "lat_max": -10.9,
    "lon_min": 129.0,
    "lon_max": 138.0
}

# ============================================================
# 2. VIIRS granule geometries (NT tiles)
# ============================================================
granule_geometries = {
    "h31v10": [
        (137.825, -20.0386),
        (148.9849, -20.0),
        (142.1754, -9.9353),
        (131.5302, -9.9755),
        (137.825, -20.0386)
    ],
    "h30v10": [
        (127.22, -20.0356),
        (138.3431, -20.0),
        (132.0209, -9.9375),
        (121.4097, -9.9745),
        (127.22, -20.0356)
    ]
}

# ============================================================
# 3. Compute lat/lon grid
# ============================================================
def compute_lat_lon(boundary_points, n_rows, n_cols):
    bl, br, tr, tl, _ = boundary_points
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
    """
    Load LST_Day_1KM, ET_500m or PET_500m using h5py.
    LST path: /HDFEOS/GRIDS/VIIRS_Grid_8Day_1km_LST21/Data Fields/LST_Day_1KM
    ET/PET path: /HDFEOS/GRIDS/VIIRS_Grid_ETLE/Data Fields/{product}_500m
    """
    try:
        with h5py.File(file_path, "r") as hdf:
            if product == "LST":
                dataset_path = "/HDFEOS/GRIDS/VIIRS_Grid_8Day_1km_LST21/Data Fields/LST_Day_1KM"
            else:
                dataset_path = f"/HDFEOS/GRIDS/VIIRS_Grid_ETLE/Data Fields/{product}_500m"

            if dataset_path not in hdf:
                raise KeyError(f"Dataset {dataset_path} not found in {file_path}")

            data = hdf[dataset_path][:]
        return data, data.shape
    except Exception as e:
        print(f"⚠ Failed to read {product} from {os.path.basename(file_path)}: {e}")
        return None, (0, 0)

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
        data, (n_rows, n_cols) = load_viirs_variable(file_path, product)
        if data is None or n_rows == 0:
            continue
        lat, lon = compute_lat_lon(granule_geometries[tile], n_rows, n_cols)
        subset = clip_to_vic(data, lat, lon)
        valid = subset[valid_mask(subset)]
        if valid.size > 0:
            all_valid.append(valid)
    return np.mean(np.concatenate(all_valid)) if all_valid else np.nan

# ============================================================
# 8. Main processing
# ============================================================
def main():
    lst_dir = r"D:\WUR\NASA_ESDS\NT_AUS\VIIRS_NPP_NT_LSurfT_Data"
    et_dir = r"D:\WUR\NASA_ESDS\NT_AUS\VIIRS_NPP_NT_ETData"
    out_csv = r"D:\WUR\NASA_ESDS\NT_AUS\VIIRS_NPP_NT_LST_ET_PET_timeseries.csv"

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
        et_files = [f for d, f in files if d == et_dir]

        avg_lst = process_product_for_date(
            lst_files, lst_dir, "LST", lambda x: x > 0
        )
        avg_et = process_product_for_date(
            et_files, et_dir, "ET", lambda x: x <= 10000
        )
        avg_pet = process_product_for_date(
            et_files, et_dir, "PET", lambda x: x <= 10000
        )

        print(f" LST: {avg_lst:.2f} | ET: {avg_et:.2f} | PET: {avg_pet:.2f}\n")
        results.append({
            "Date": date,
            "Average_LST": avg_lst,
            "Average_ET": avg_et,
            "Average_PET": avg_pet
        })

    df = pd.DataFrame(results)
    df.sort_values("Date", inplace=True)
    df.to_csv(out_csv, index=False)
    print(f"✅ Saved VIIRS NT LST–ET–PET time series to:\n{out_csv}")

# ============================================================
# 9. Run
# ============================================================
if __name__ == "__main__":
    main()