# ============================================================
# Script: extract_modis_aqua_LST_ET_PET_NT_timeseries_safe.py
# Purpose:
#   - Loop through MODIS Aqua LST, ET, PET HDF files across years
#   - Use Northern Territory–specific tile geometries
#   - Clip to NT VIC boundary
#   - Apply product-specific invalid-value filtering
#   - Compute spatial averages per date
#   - Save ONE combined CSV
#   - Fail safely on corrupt or missing files
# ============================================================

import numpy as np
import os
import re
import pandas as pd
from datetime import datetime
from netCDF4 import Dataset

# ============================================================
# 1. VIC study area boundary — Northern Territory, Australia
# ============================================================
vic_boundary = {
    "lat_min": -17.0,
    "lat_max": -10.9,
    "lon_min": 129.0,
    "lon_max": 138.0
}

# ============================================================
# 2. MODIS Aqua tile geometries — Northern Territory
# ============================================================

# ET / PET tiles
ET_GEOMETRIES = {
    "h30v10": [
        (138.343110407867, -19.9999999982039),
        (132.020927894706,  -9.93746671411948),
        (121.409671246333,  -9.97449019926359),
        (127.219958378815, -20.0355981480789)
    ],
    "h31v10": [
        (148.984888131549, -19.9999999982039),
        (142.175397358673,  -9.93527477182093),
        (131.530219601717,  -9.97545162476126),
        (137.825020464527, -20.0385919212958)
    ]
}

# LST tiles
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
# 3. Compute latitude / longitude arrays
# ============================================================
def compute_lat_lon(boundary_points, n_rows, n_cols):
    bl, br, tr, tl = boundary_points

    t = np.linspace(0, 1, n_rows)[:, None]
    s = np.linspace(0, 1, n_cols)[None, :]

    left_lon  = bl[0] + t * (tl[0] - bl[0])
    left_lat  = bl[1] + t * (tl[1] - bl[1])
    right_lon = br[0] + t * (tr[0] - br[0])
    right_lat = br[1] + t * (tr[1] - br[1])

    lon = left_lon + s * (right_lon - left_lon)
    lat = left_lat + s * (right_lat - left_lat)

    return lat, lon

# ============================================================
# 4. Clip data to VIC boundary
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
# 5. Extract date from MODIS filename (AYYYYDDD)
# ============================================================
def extract_date_from_filename(filename):
    match = re.search(r"A(\d{4})(\d{3})", filename)
    if not match:
        return None

    year = int(match.group(1))
    doy  = int(match.group(2))
    return (datetime(year, 1, 1) +
            pd.to_timedelta(doy - 1, unit="D")).date()

# ============================================================
# 6. Load MODIS variable safely
# ============================================================
def load_modis_variable(file_path, variable_name):
    try:
        with Dataset(file_path, "r") as hdf:
            data = hdf.variables[variable_name][:]
        return data, data.shape
    except Exception as e:
        print(f"⚠ Failed reading {variable_name} from {os.path.basename(file_path)}: {e}")
        return None, (0, 0)

# ============================================================
# 7. Process product for one date
# ============================================================
def process_product_for_date(files, base_dir, variable, geometries, valid_mask):
    all_valid = []

    for tile in geometries:
        matches = [f for f in files if tile in f]
        if not matches:
            continue

        file_path = os.path.join(base_dir, matches[0])
        data, (n_rows, n_cols) = load_modis_variable(file_path, variable)
        if data is None:
            continue

        lat, lon = compute_lat_lon(geometries[tile], n_rows, n_cols)
        subset = clip_to_vic(data, lat, lon)
        valid  = subset[valid_mask(subset)]

        if valid.size > 0:
            all_valid.append(valid)

    return np.mean(np.concatenate(all_valid)) if all_valid else np.nan

# ============================================================
# 8. Main processing
# ============================================================
def main():

    lst_dir = r"D:\WUR\NASA_ESDS\NT_AUS\MODISAqua_LSurfT_Data"
    et_dir  = r"D:\WUR\NASA_ESDS\NT_AUS\MODISAqua_NT_ETData"
    out_csv = r"D:\WUR\NASA_ESDS\NT_AUS\MODIS_Aqua_LST_ET_PET_NT.csv"

    all_files = (
        [(lst_dir, f) for f in os.listdir(lst_dir) if f.endswith(".hdf")] +
        [(et_dir,  f) for f in os.listdir(et_dir)  if f.endswith(".hdf")]
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
            lst_files, lst_dir, "LST_Day_1km",
            LST_GEOMETRIES, lambda x: x > 0
        )

        avg_et = process_product_for_date(
            et_files, et_dir, "ET_500m",
            ET_GEOMETRIES, lambda x: x <= 10000
        )

        avg_pet = process_product_for_date(
            et_files, et_dir, "PET_500m",
            ET_GEOMETRIES, lambda x: x <= 10000
        )

        print(
            f"  LST: {avg_lst:.2f} | "
            f"ET: {avg_et:.2f} | "
            f"PET: {avg_pet:.2f}\n"
        )

        results.append({
            "Date": date,
            "Average_LST": avg_lst,
            "Average_ET": avg_et,
            "Average_PET": avg_pet
        })

    df = pd.DataFrame(results)
    df.sort_values("Date", inplace=True)
    df.to_csv(out_csv, index=False)

    print(f"✅ MODIS Aqua NT LST–ET–PET time series saved to:\n{out_csv}")

# ============================================================
# 9. Run
# ============================================================
if __name__ == "__main__":
    main()