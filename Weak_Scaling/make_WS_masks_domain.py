#!/usr/bin/env python3
"""
Create weak-scaling domain files by modifying only the mask variable.
Keeps area and frac unchanged.
Uses xarray + dask threaded scheduler for parallelism.
"""

import os
import xarray as xr
import numpy as np
import dask

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────

INPUT_FILE = "/lustre/nobackup/WUR/ESG/smets008/mGV/validations/global/param/vic_global_5min_domain_nogl.nc"
OUTPUT_DIR = "/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/Weak_Scaling/domain_files"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Starting lower-left corner (lon_idx, lat_idx)
I_START = 2040
J_START = 875

# Configurations: (side_length, ws_number, name_part)
configs = [
    (5,  1, "WS1_25cells"),
    (10, 2, "WS2_100cells"),
    (20, 3, "WS3_400cells"),
    (40, 4, "WS4_1600cells"),
]

NUM_THREADS = 32
dask.config.set(scheduler='threads', num_workers=NUM_THREADS)
print(f"Dask configured to use {NUM_THREADS} threads (threaded scheduler)")

# ────────────────────────────────────────────────

print("Loading input domain file ...")
ds = xr.open_dataset(INPUT_FILE, chunks={'lat': 200, 'lon': 200})

# Debug original (will likely show float64)
print(f"Original mask dtype: {ds['mask'].dtype}")
print(f"Original mask _FillValue: {ds['mask'].attrs.get('_FillValue', 'not set')}")

# Get shape and coordinates once (we'll use these for the new mask)
mask_shape = ds['mask'].shape
lat_coord = ds['lat'].values
lon_coord = ds['lon'].values

for side, ws_num, name in configs:
    print(f"\nProcessing WS{ws_num} – {side}×{side} cells ...")

    # Create fresh integer mask as numpy array (int32 to match typical VIC expectation)
    mask_np = np.zeros(mask_shape, dtype=np.int32)
    mask_np[J_START:J_START + side, I_START:I_START + side] = 1

    # Wrap as DataArray with correct coordinates
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

    # IMPORTANT: Force integer type via encoding only (no attrs conflict)
    ds_new['mask'].encoding = {
        'dtype': 'i4',              # NC_INT = 32-bit integer
        '_FillValue': 0,
        'zlib': True,
        'complevel': 5,
        'shuffle': True,
    }

    # Remove any conflicting attrs that might cause promotion
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
