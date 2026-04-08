import numpy as np
import os
import re
import pandas as pd
from datetime import datetime
from netCDF4 import Dataset

# Pantanal VIC boundary
vic_boundary = {
    "lat_min": -18.5,
    "lat_max": -16.5,
    "lon_min": -59.5,
    "lon_max": -56.0
}

# Granule boundaries
granule_boundaries = {
    "LST_E": [  # LST&E granule
        (-63.855103293672, -19.9958333333333),
        (-53.2133437928847, -19.9958333333333),
        (-50.7768724960413, -10.0041666666667),
        (-60.9313825214595, -10.0041666666667)
    ],
    "ET_only": [  # ET-only granule
        (-52.9885896490026, -20.0151416658559),
        (-50.5717093742954, -9.96742499665193),
        (-60.9332459081005, -9.95174301126409),
        (-63.8506663420922, -19.9999999982039)
    ]
}

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

def filter_data_by_vic_boundary(data, lat_array, lon_array):
    mask = (
        (lat_array >= vic_boundary["lat_min"]) &
        (lat_array <= vic_boundary["lat_max"]) &
        (lon_array >= vic_boundary["lon_min"]) &
        (lon_array <= vic_boundary["lon_max"])
    )
    return data[mask]

def extract_date_from_filename(filename):
    match = re.search(r"A(\d{4})(\d{3})", filename)
    if match:
        year = int(match.group(1))
        doy = int(match.group(2))
        return (datetime(year, 1, 1) + pd.to_timedelta(doy - 1, unit="D")).date()
    return None

def load_modis_variable(file_path, variable_name):
    with Dataset(file_path, "r") as hdf:
        data = hdf.variables[variable_name][:]
    return data, data.shape

def process_product(file_path, variable_name, granule_type, valid_mask_func):
    try:
        data, (n_rows, n_cols) = load_modis_variable(file_path, variable_name)
    except Exception as e:
        print(f"⚠ Failed to read {variable_name} from {file_path}: {e}")
        return np.nan
    lat_array, lon_array = compute_lat_lon(granule_boundaries[granule_type], n_rows, n_cols)
    subset = filter_data_by_vic_boundary(data, lat_array, lon_array)
    valid = subset[valid_mask_func(subset)]
    return np.mean(valid) if valid.size > 0 else np.nan

def main():
    lst_e_dir = r"D:\WUR\NASA_ESDS\Pantanal\MODISTerra_Pantanal_LSurfT_Data"
    et_dir    = r"D:\WUR\NASA_ESDS\Pantanal\MODISTerra_PantanalETData"
    output_csv = r"D:\WUR\NASA_ESDS\Pantanal\MODIS_Terra_LST_ET_PET_timeseries_Pantanal.csv"

    # Collect files
    all_files = (
        [(lst_e_dir, f, "LST_E") for f in os.listdir(lst_e_dir) if f.endswith(".hdf")] +
        [(et_dir, f, "ET_only") for f in os.listdir(et_dir) if f.endswith(".hdf")]
    )

    # Group by date
    files_by_date = {}
    for base_dir, fname, granule_type in all_files:
        date = extract_date_from_filename(fname)
        if date:
            files_by_date.setdefault(date, []).append((base_dir, fname, granule_type))

    results = []

    for date in sorted(files_by_date.keys()):
        files = files_by_date[date]

        # LST from LST&E file
        lst_files = [f for f in files if f[2]=="LST_E"]
        if lst_files:
            file_path = os.path.join(lst_files[0][0], lst_files[0][1])
            avg_lst = process_product(file_path, "LST_Day_1km", "LST_E", lambda x: x>0)
        else:
            avg_lst = np.nan

        # ET & PET from ET-only file
        et_files = [f for f in files if f[2]=="ET_only"]
        if et_files:
            file_path = os.path.join(et_files[0][0], et_files[0][1])
            avg_et  = process_product(file_path, "ET_500m", "ET_only", lambda x: x<=10000)
            avg_pet = process_product(file_path, "PET_500m", "ET_only", lambda x: x<=10000)
        else:
            avg_et = avg_pet = np.nan

        print(f"Processing {date} | LST: {avg_lst:.2f} | ET: {avg_et:.2f} | PET: {avg_pet:.2f}")
        results.append({"Date": date, "Average_LST": avg_lst, "Average_ET": avg_et, "Average_PET": avg_pet})

    # Save CSV
    df = pd.DataFrame(results)
    df.to_csv(output_csv, index=False)
    print(f"✅ Saved to {output_csv}")

if __name__=="__main__":
    main()