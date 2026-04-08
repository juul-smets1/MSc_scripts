#!/usr/bin/env python3
"""
Create weak-scaling domain files by modifying only the mask variable.
Keeps area and frac unchanged.
Uses xarray + dask threaded scheduler for parallelism.
New layout (area doubles each time, asymmetric expansion).
"""

import os
import xarray as xr
import numpy as np
import dask

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────

INPUT_FILE = "/lustre/nobackup/WUR/ESG/smets008/mGV/validations/global/param/vic_global_5min_domain_nogl.nc"
OUTPUT_DIR = "/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/Weak_Scaling/new_domain_files"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Fixed lower-left corner for ALL weak scaling levels
I_START = 2040   # lon index
J_START = 875    # lat index

# New configurations: (i_end, j_end, ws_number, name_part, cell_count_comment)
# i_end = last lon index (inclusive), j_end = last lat index (inclusive)
configs = [
    (2044, 879,  1, "WS1_25cells",    "25 grid cells"),
    (2049, 879,  2, "WS2_50cells",    "50 grid cells"),
    (2049, 884,  3, "WS3_100cells",   "100 grid cells"),
    (2059, 884,  4, "WS4_200cells",   "200 grid cells"),
    (2059, 894,  5, "WS5_400cells",   "400 grid cells"),
    (2079, 894,  6, "WS6_800cells",   "800 grid cells"),
    (2079, 914,  7, "WS7_1600cells",  "1600 grid cells"),
    (2079, 954,  8, "WS8_3200cells",  "3200 grid cells"),
    (2119, 954,  9, "WS9_6400cells",  "6400 grid cells"),
    (2199, 954, 10, "WS10_12800cells","12800 grid cells"),
    (2359, 954, 11, "WS11_25600cells","25600 grid cells"),
]

NUM_THREADS = 32
dask.config.set(scheduler='threads', num_workers=NUM_THREADS)
print(f"Dask configured to use {NUM_THREADS} threads (threaded scheduler)")

# ────────────────────────────────────────────────

print("Loading input domain file ...")
ds = xr.open_dataset(INPUT_FILE, chunks={'lat': 200, 'lon': 200})

# Debug original
print(f"Original mask dtype: {ds['mask'].dtype}")
print(f"Original mask _FillValue: {ds['mask'].attrs.get('_FillValue', 'not set')}")

# Get shape and coordinates once
mask_shape = ds['mask'].shape
lat_coord = ds['lat'].values
lon_coord = ds['lon'].values

for i_end, j_end, ws_num, name, cell_comment in configs:
    print(f"\nProcessing {name} – {cell_comment} ...")

    # Calculate side lengths (inclusive)
    lon_count = i_end - I_START + 1
    lat_count = j_end - J_START + 1
    total_cells = lon_count * lat_count
    print(f"  lon range: {I_START} to {i_end} ({lon_count} cells)")
    print(f"  lat range: {J_START} to {j_end} ({lat_count} cells)")
    print(f"  total cells: {total_cells}")

    # Create fresh integer mask as numpy array (int32)
    mask_np = np.zeros(mask_shape, dtype=np.int32)
    mask_np[J_START:j_end+1, I_START:i_end+1] = 1

    # Wrap as DataArray
    new_mask_da = xr.DataArray(
        mask_np,
        dims=['lat', 'lon'],
        coords={'lat': lat_coord, 'lon': lon_coord},
        name='mask',
        attrs={
            'long_name': 'land mask (1=land, 0=non-land)',
            'standard_name': 'land_binary_mask'
        }
    )

    # Copy original dataset and replace mask
    ds_new = ds.copy(deep=True)
    ds_new['mask'] = new_mask_da

    # Force integer encoding
    ds_new['mask'].encoding = {
        'dtype': 'i4',              # NC_INT = 32-bit integer
        '_FillValue': 0,
        'zlib': True,
        'complevel': 5,
        'shuffle': True,
    }

    # Remove any conflicting attrs
    if '_FillValue' in ds_new['mask'].attrs:
        del ds_new['mask'].attrs['_FillValue']

    # Output filename
    out_name = f"vic_{name}_5min_domain_nogl.nc"
    out_path = os.path.join(OUTPUT_DIR, out_name)
    print(f"  Writing → {out_path}")

    ds_new.to_netcdf(
        out_path,
        format='NETCDF4_CLASSIC',
        engine='netcdf4',
        encoding={
            'area': {'zlib': True, 'complevel': 5},
            'frac': {'zlib': True, 'complevel': 5},
        }
    )

    ds_new.close()

print("\nAll weak-scaling domain files created.")
print(f"Check directory: {OUTPUT_DIR}")
