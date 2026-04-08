#!/usr/bin/env python3
"""
Crop VIC parameter file to exact weak-scaling rectangles.
Preserves original dtypes, _FillValue, missing_value, attributes.
Removes unsupported encoding keys for NETCDF4_CLASSIC backend.
Only changes spatial extent (lat/lon dimensions).
"""

import os
import xarray as xr
import numpy as np

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────

INPUT_FILE = "/lustre/nobackup/WUR/ESG/smets008/mGV/validations/global/param/vic_global_5min_params_nogl.nc"
OUTPUT_DIR = "/lustre/nobackup/WUR/ESG/smets008/VRAM_zarr_mGV/input_data/Weak_Scaling/param"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Fixed lower-left corner (lon_idx, lat_idx)
I_START = 2040
J_START = 875

# Configurations: (i_end, j_end, ws_number, name_part, cell_count_comment)
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

# ────────────────────────────────────────────────

print("Loading full parameter file ...")
ds_full = xr.open_dataset(INPUT_FILE)

print(f"Original dimensions: lat={ds_full.sizes['lat']}, lon={ds_full.sizes['lon']}")

for i_end, j_end, ws_num, name, cell_comment in configs:
    print(f"\nProcessing {name} – {cell_comment} ...")

    # Inclusive coordinate-based slices
    lon_slice = ds_full.lon[slice(I_START, i_end + 1)]
    lat_slice = ds_full.lat[slice(J_START, j_end + 1)]

    lon_count = len(lon_slice)
    lat_count = len(lat_slice)
    total_cells = lon_count * lat_count
    print(f"  lon range: {I_START} to {i_end} ({lon_count} cells)")
    print(f"  lat range: {J_START} to {j_end} ({lat_count} cells)")
    print(f"  total cells: {total_cells}")

    # Subset using .sel() to keep exact coordinate values
    ds_cropped = ds_full.sel(lon=lon_slice, lat=lat_slice)

    # Remove unwanted NaN FillValue from variables that didn't have explicit FillValue originally
    for var in ds_cropped.variables:
        if '_FillValue' in ds_cropped[var].encoding and np.isnan(ds_cropped[var].encoding['_FillValue']):
            if '_FillValue' not in ds_full[var].encoding:
                del ds_cropped[var].encoding['_FillValue']

    # Prepare safe encoding: copy original, remove unsupported keys, force zlib
    encoding_dict = {}
    for var in ds_cropped.variables:
        if var in ['lat', 'lon', 'snow_band', 'veg_class', 'nlayer', 'month', 'root_zone']:
            # Coordinate/index vars — no compression
            encoding_dict[var] = {}
            continue

        # Copy original encoding
        orig_enc = ds_full[var].encoding.copy()

        # Remove keys not supported by NETCDF4_CLASSIC/netCDF4-python
        unsupported_keys = ['szip', 'zstd', 'bzip2', 'blosc', 'preferred_chunks',
                            'fletcher32', 'contiguous', 'chunksizes']
        for k in list(orig_enc.keys()):
            if k in unsupported_keys:
                del orig_enc[k]

        # Force safe compression (zlib is universally supported)
        orig_enc['zlib'] = True
        orig_enc['complevel'] = 5
        orig_enc['shuffle'] = True

        # Preserve original dtype and FillValue if present
        if 'dtype' in ds_full[var].encoding:
            orig_enc['dtype'] = ds_full[var].encoding['dtype']
        if '_FillValue' in ds_full[var].encoding:
            orig_enc['_FillValue'] = ds_full[var].encoding['_FillValue']

        encoding_dict[var] = orig_enc

    # Output filename
    out_name = f"vic_{name}_5min_params_nogl.nc"
    out_path = os.path.join(OUTPUT_DIR, out_name)
    print(f"  Writing cropped parameter file → {out_path}")

    ds_cropped.to_netcdf(
        out_path,
        format='NETCDF4_CLASSIC',
        engine='netcdf4',
        encoding=encoding_dict
    )

    # Print file size
    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"  File size: {size_mb:.1f} MB")

print("\nAll weak-scaling parameter files created (cropped, original types/attributes preserved).")
print(f"Check directory: {OUTPUT_DIR}")
