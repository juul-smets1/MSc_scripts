# ============================================================
# Script: extract_modis_pet_timeseries_netCDF.py
# Purpose: Loop through MODIS Terra PET_500m HDF files across years
#          Match VIC boundaries, exclude invalid values (>10000),
#          compute average PET per date, and save as CSV
# ============================================================

import numpy as np
import os
import re
import pandas as pd
from datetime import datetime
from netCDF4 import Dataset  # Use netCDF4 to read MODIS HDF4

# -------------------------------
# 1. Define VIC study area boundaries
# -------------------------------
vic_boundary = {
    "lat_min": 8.54167,
    "lat_max": 11.4583,
    "lon_min": 104.042,
    "lon_max": 106.958
}

# -------------------------------
# 2. Define satellite grid geometries (boundaries stay fixed)
# -------------------------------
grid_geometries = {
    "h28v08": [
        (99.6259, 0.0004),
        (110.0184, -0.0102),
        (111.7068, 9.9998),
        (101.1513, 10.0088)
    ],
    "h28v07": [
        (101.1705, 9.9726),
        (111.7183, 9.9416),
        (117.0729, 19.9995),
        (106.0116, 20.0297)
    ]
}

# -------------------------------
# 3. Compute lat/lon arrays for a grid
# -------------------------------
def compute_lat_lon(boundary_points, n_rows, n_cols):
    """Vectorized bilinear interpolation for lat/lon arrays."""
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

# -------------------------------
# 4. Load PET_500m dataset from MODIS HDF4 via netCDF4
# -------------------------------
def load_pet_data(file_path):
    """Load PET_500m dataset from MODIS HDF4 file using netCDF4."""
    with Dataset(file_path, mode='r') as hdf:
        # PET dataset is typically named 'PET_500m'
        data = hdf.variables['PET_500m'][:]
    return data, data.shape

# -------------------------------
# 5. Filter data by VIC boundary
# -------------------------------
def filter_data_by_vic_boundary(data, lat_array, lon_array, vic_boundary):
    """Extract pixels within VIC boundary."""
    mask = (
        (lat_array >= vic_boundary["lat_min"]) &
        (lat_array <= vic_boundary["lat_max"]) &
        (lon_array >= vic_boundary["lon_min"]) &
        (lon_array <= vic_boundary["lon_max"])
    )
    return data[mask]

# -------------------------------
# 6. Extract Julian day and convert to date
# -------------------------------
def extract_date_from_filename(filename):
    """
    Extract AYYYYDDD and convert to YYYY-MM-DD.
    Works correctly even when year changes (e.g., 2000361 -> 2000-12-26).
    """
    match = re.search(r"A(\d{4})(\d{3})", filename)
    if match:
        year = int(match.group(1))
        doy = int(match.group(2))
        try:
            date = datetime(year, 1, 1) + pd.to_timedelta(doy - 1, unit='D')
            return date.date()
        except Exception:
            return None
    return None

# -------------------------------
# 7. Main processing
# -------------------------------
def main():
    base_dir = r"D:\WUR\NASA_ESDS\MODISTerra_MekongETData_F19"
    output_csv = os.path.join(base_dir, "MODIS_PET_timeseries.csv")

    results = []

    # Find all HDF files in the directory
    all_files = [f for f in os.listdir(base_dir) if f.endswith(".hdf")]

    # Group files by date
    dates = {}
    for f in all_files:
        date = extract_date_from_filename(f)
        if date:
            dates.setdefault(date, []).append(f)

    print(f"Found {len(dates)} unique dates in folder.\n")

    for date, files in sorted(dates.items()):
        print(f"Processing date: {date}")

        all_valid_data = []

        for grid_name in ["h28v07", "h28v08"]:
            # Find corresponding file for this grid
            matching_files = [f for f in files if grid_name in f]
            if not matching_files:
                continue

            file_path = os.path.join(base_dir, matching_files[0])
            data, (n_rows, n_cols) = load_pet_data(file_path)

            lat_array, lon_array = compute_lat_lon(grid_geometries[grid_name], n_rows, n_cols)
            filtered_data = filter_data_by_vic_boundary(data, lat_array, lon_array, vic_boundary)
            valid_data = filtered_data[filtered_data <= 10000]

            if valid_data.size > 0:
                all_valid_data.append(valid_data)

        if all_valid_data:
            combined = np.concatenate(all_valid_data)
            avg_pet = np.mean(combined)
            print(f"  Average PET: {avg_pet:.2f}\n")
            results.append({"Date": date, "Average_PET": avg_pet})
        else:
            print("  No valid data for this date.\n")

    # Save results to CSV
    df = pd.DataFrame(results)
    df.sort_values("Date", inplace=True)
    df.to_csv(output_csv, index=False)
    print(f"\n✅ Saved MODIS Terra PET time series to {output_csv}")

# -------------------------------
# 8. Run the script
# -------------------------------
if __name__ == "__main__":
    main()
