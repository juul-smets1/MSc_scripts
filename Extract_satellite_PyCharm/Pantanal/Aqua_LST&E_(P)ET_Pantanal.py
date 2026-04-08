# ============================================================
# Script: extract_modis_aqua_LST_ET_PET_Pantanal_timeseries.py
# Purpose:
#   - Loop through MODIS Aqua LST&E and ET-only HDF files
#   - Use Pantanal-specific granule boundaries
#   - Clip to Pantanal VIC boundary
#   - Compute spatial means per date
#   - Save ONE combined CSV
# ============================================================

import numpy as np
import os
import re
import pandas as pd
from datetime import datetime
from netCDF4 import Dataset

# ============================================================
# 1. Pantanal VIC boundary
# ============================================================
vic_boundary = {
    "lat_min": -18.5,
    "lat_max": -16.5,
    "lon_min": -59.5,
    "lon_max": -56.0
}

# ============================================================
# 2. Pantanal granule boundaries
#    (different for LST&E and ET-only)
# ============================================================
granule_boundaries = {
    "ET_only": [
        (-52.9885896490026, -20.0151416658559),
        (-50.5717093742954, -9.96742499665193),
        (-60.9332459081005, -9.95174301126409),
        (-63.8506663420922, -19.9999999982039)
    ],
    "LST_E": [
        (-63.855103293672, -19.9958333333333),
        (-53.2133437928847, -19.9958333333333),
        (-50.7768724960413, -10.0041666666667),
        (-60.9313825214595, -10.0041666666667)
    ]
}

# ============================================================
# 3. Compute lat/lon arrays from granule boundary
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
# 5. Extract date from MODIS filename
# ============================================================
def extract_date_from_filename(filename):
    match = re.search(r"A(\d{4})(\d{3})", filename)
    if not match:
        return None
    year = int(match.group(1))
    doy = int(match.group(2))
    return (datetime(year, 1, 1) + pd.to_timedelta(doy - 1, unit="D")).date()

# ============================================================
# 6. Load MODIS variable safely
# ============================================================
def load_variable(file_path, variable):
    with Dataset(file_path, "r") as hdf:
        data = hdf.variables[variable][:]
    return data, data.shape

# ============================================================
# 7. Process single file
# ============================================================
def process_file(file_path, variable, granule_type, valid_mask):
    try:
        data, (n_rows, n_cols) = load_variable(file_path, variable)
    except Exception as e:
        print(f"⚠ Failed to read {variable} from {os.path.basename(file_path)}: {e}")
        return np.nan

    lat, lon = compute_lat_lon(
        granule_boundaries[granule_type], n_rows, n_cols
    )

    subset = clip_to_vic(data, lat, lon)
    valid = subset[valid_mask(subset)]

    return np.mean(valid) if valid.size > 0 else np.nan

# ============================================================
# 8. Main processing
# ============================================================
def main():

    lst_dir = r"D:\WUR\NASA_ESDS\Pantanal\MODISAqua_Pantanal_LSurfT_Data"
    et_dir  = r"D:\WUR\NASA_ESDS\Pantanal\MODISAqua_PantanalETData"
    out_csv = r"D:\WUR\NASA_ESDS\Pantanal\MODIS_Aqua_LST_ET_PET_Pantanal.csv"

    all_files = (
        [(lst_dir, f, "LST_E") for f in os.listdir(lst_dir) if f.endswith(".hdf")] +
        [(et_dir, f, "ET_only") for f in os.listdir(et_dir) if f.endswith(".hdf")]
    )

    files_by_date = {}
    for base, fname, gtype in all_files:
        date = extract_date_from_filename(fname)
        if date:
            files_by_date.setdefault(date, []).append((base, fname, gtype))

    results = []

    for date in sorted(files_by_date.keys()):
        print(f"Processing {date}")

        lst_vals, et_vals, pet_vals = [], [], []

        for base, fname, gtype in files_by_date[date]:
            path = os.path.join(base, fname)

            if gtype == "LST_E":
                lst_vals.append(
                    process_file(path, "LST_Day_1km", "LST_E", lambda x: x > 0)
                )

            if gtype == "ET_only":
                et_vals.append(
                    process_file(path, "ET_500m", "ET_only", lambda x: x <= 10000)
                )
                pet_vals.append(
                    process_file(path, "PET_500m", "ET_only", lambda x: x <= 10000)
                )

        avg_lst = np.nanmean(lst_vals) if lst_vals else np.nan
        avg_et  = np.nanmean(et_vals)  if et_vals else np.nan
        avg_pet = np.nanmean(pet_vals) if pet_vals else np.nan

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

    print(f"✅ Saved MODIS Aqua Pantanal time series to:\n{out_csv}")

# ============================================================
# 9. Run
# ============================================================
if __name__ == "__main__":
    main()