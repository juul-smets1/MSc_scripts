# ============================================================
# Script: MODIS_Terra_LST_ET_PET_Yucatan.py (Corrected)
# ============================================================

import numpy as np
import os
import re
import pandas as pd
from datetime import datetime
from netCDF4 import Dataset

# ============================================================
# 1. VIC study area boundaries — Yucatán Peninsula
# ============================================================
vic_boundary = {
    "lat_min": 16.0,
    "lat_max": 21.7,
    "lon_min": -91.0,
    "lon_max": -86.6
}

# ============================================================
# 2. Granule boundaries
# ============================================================
LST_E_GRANULES = {
    "h09v06": [
        (-95.7854936618109, 20.0041666666667),
        (-85.1431698709447, 20.0041666666667),
        (-92.3808679493012, 29.9958333333333),
        (-103.927853790562, 29.9958333333333),
        (-95.7854936618109, 20.0041666666667)
    ],
    "h09v07": [
        (-91.3949633696953, 10.0041666666667),
        (-81.2404533442771, 10.0041666666667),
        (-85.1386755034478, 19.9958333333333),
        (-95.7804350042351, 19.9958333333333),
        (-91.3949633696953, 10.0041666666667)
    ]
}

ET_ONLY_GRANULES = {
    "h09v06": [
        (-84.8251194107616, 19.9358874145633),
        (-92.0524964048955, 30.0438375723808),
        (-103.923048441979, 29.9999999973059),
        (-95.7583012079626, 19.8938932482369),
        (-84.8251194107616, 19.9358874145633)
    ],
    "h09v07": [
        (-80.927089274095, 9.9704855529409),
        (-84.8012409929684, 20.0238091465748),
        (-95.7759995131384, 19.9999999982039),
        (-91.3988008626617, 9.94589238812958),
        (-80.927089274095, 9.9704855529409)
    ]
}


# ============================================================
# 3. Compute lat/lon arrays for a tile
# ============================================================
def compute_lat_lon(boundary_points, n_rows, n_cols):
    # Use bottom-left (bl), bottom-right (br), top-right (tr), top-left (tl)
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
# 6. Load MODIS variable
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
# 7. Process a product from one file
# ============================================================
def process_product(file_path, variable_name, granule_dict, valid_mask_func):
    if not os.path.exists(file_path):
        return np.nan
    data, (n_rows, n_cols) = load_modis_variable(file_path, variable_name)
    if data is None:
        return np.nan

    # Detect tile from filename
    tile = next((t for t in granule_dict if t in os.path.basename(file_path)), None)
    if tile is None:
        return np.nan

    lat_array, lon_array = compute_lat_lon(granule_dict[tile], n_rows, n_cols)
    subset = filter_data_by_vic_boundary(data, lat_array, lon_array)

    if subset.size == 0:
        return np.nan

    valid = subset[valid_mask_func(subset)]
    return np.nanmean(valid) if valid.size > 0 else np.nan


# ============================================================
# 8. Main processing
# ============================================================
def main():
    lst_e_dir = r"D:\WUR\NASA_ESDS\Yucatán\MODISTerra_Yucatán_LSurfT_Data"
    et_dir = r"D:\WUR\NASA_ESDS\Yucatán\MODISTerra_YucatánETData"
    output_csv = r"D:\WUR\NASA_ESDS\Yucatán\MODIS_Terra_LST_ET_PET_Yucatán.csv"

    # Collect files
    all_files = (
            [(lst_e_dir, f, "LST_E") for f in os.listdir(lst_e_dir) if f.endswith(".hdf")] +
            [(et_dir, f, "ET_only") for f in os.listdir(et_dir) if f.endswith(".hdf")]
    )

    # Group files by date
    files_by_date = {}
    for base_dir, fname, granule_type in all_files:
        date = extract_date_from_filename(fname)
        if date:
            files_by_date.setdefault(date, []).append((base_dir, fname, granule_type))

    results = []

    for date in sorted(files_by_date.keys()):
        files = files_by_date[date]

        # LST from LST&E files
        lst_files = [f for f in files if f[2] == "LST_E"]
        avg_lst = np.nan
        if lst_files:
            file_path = os.path.join(lst_files[0][0], lst_files[0][1])
            avg_lst = process_product(file_path, "LST_Day_1km", LST_E_GRANULES, lambda x: x > 0)

        # ET & PET from ET-only files
        et_files = [f for f in files if f[2] == "ET_only"]
        avg_et = avg_pet = np.nan
        if et_files:
            file_path = os.path.join(et_files[0][0], et_files[0][1])
            avg_et = process_product(file_path, "ET_500m", ET_ONLY_GRANULES, lambda x: x <= 10000)
            avg_pet = process_product(file_path, "PET_500m", ET_ONLY_GRANULES, lambda x: x <= 10000)

        print(f"Processing {date} | LST: {avg_lst:.2f} | ET: {avg_et:.2f} | PET: {avg_pet:.2f}")

        results.append({
            "Date": date,
            "Average_LST": avg_lst,
            "Average_ET": avg_et,
            "Average_PET": avg_pet
        })

    df = pd.DataFrame(results)
    df.sort_values("Date", inplace=True)
    df.to_csv(output_csv, index=False)
    print(f"\n✅ Combined MODIS Terra LST–ET–PET time series saved to:\n{output_csv}")


# ============================================================
# 9. Run script
# ============================================================
if __name__ == "__main__":
    main()