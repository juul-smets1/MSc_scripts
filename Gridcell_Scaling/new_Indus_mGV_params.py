#!/usr/bin/env python3
"""
Crop VIC Indus Mirca-calibrated parameter file to the exact basin grid.
Uses EXACT same logic, encoding cleaning, and NETCDF4_CLASSIC handling
as your weak-scaling scripts. Only spatial cropping (full Indus domain).
"""
import os
import xarray as xr
import numpy as np

# ────────────────────────────────────────────────
# CONFIGURATION (EXACT same style as Weak Scaling)
# ────────────────────────────────────────────────
INPUT_FILE = "/lustre/nobackup/WUR/ESG/datad002/mGV/input_data/indus/VIC_params_Mirca_calibrated_Indus.nc"
OUTPUT_DIR = "/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/Gridcell_Scaling/config"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Full Indus domain (from ncdump: lat=180, lon=204 → 0-based indices)
I_START = 0
J_START = 0

# Single configuration: the entire Indus basin
configs = [
    (203, 179, 1, "Indus_full", "180x204 grid cells – full Indus basin"),
]

print("Loading full Indus Mirca parameter file ...")
ds_full = xr.open_dataset(INPUT_FILE)
print(f"Original dimensions: lat={ds_full.sizes['lat']}, lon={ds_full.sizes['lon']}, veg_class={ds_full.sizes['veg_class']}")

for i_end, j_end, indus_num, name, cell_comment in configs:
    print(f"\nProcessing {name} – {cell_comment} ...")
    
    # Inclusive coordinate-based slices (exact same method as Weak Scaling)
    lon_slice = ds_full.lon[slice(I_START, i_end + 1)]
    lat_slice = ds_full.lat[slice(J_START, j_end + 1)]
    lon_count = len(lon_slice)
    lat_count = len(lat_slice)
    total_cells = lon_count * lat_count
    print(f"  lon range: {I_START} to {i_end} ({lon_count} cells)")
    print(f"  lat range: {J_START} to {j_end} ({lat_count} cells)")
    print(f"  total cells: {total_cells}")

    # Subset
    ds_cropped = ds_full.sel(lon=lon_slice, lat=lat_slice)

    # Remove unwanted NaN FillValue from variables that didn't have explicit FillValue originally
    for var in ds_cropped.variables:
        if '_FillValue' in ds_cropped[var].encoding and np.isnan(ds_cropped[var].encoding['_FillValue']):
            if '_FillValue' not in ds_full[var].encoding:
                del ds_cropped[var].encoding['_FillValue']

    # Prepare safe encoding (EXACT same logic as your Weak Scaling script)
    encoding_dict = {}
    for var in ds_cropped.variables:
        if var in ['lat', 'lon', 'snow_band', 'veg_class', 'nlayer', 'month', 'root_zone']:
            encoding_dict[var] = {}
            continue
        orig_enc = ds_full[var].encoding.copy()
        unsupported_keys = ['szip', 'zstd', 'bzip2', 'blosc', 'preferred_chunks',
                            'fletcher32', 'contiguous', 'chunksizes']
        for k in list(orig_enc.keys()):
            if k in unsupported_keys:
                del orig_enc[k]
        orig_enc['zlib'] = True
        orig_enc['complevel'] = 5
        orig_enc['shuffle'] = True
        if 'dtype' in ds_full[var].encoding:
            orig_enc['dtype'] = ds_full[var].encoding['dtype']
        if '_FillValue' in ds_full[var].encoding:
            orig_enc['_FillValue'] = ds_full[var].encoding['_FillValue']
        encoding_dict[var] = orig_enc

    # Output filename (matches your Mekong / global naming style)
    out_name = "vic_indus_5min_params_nogl.nc"
    out_path = os.path.join(OUTPUT_DIR, out_name)
    print(f"  Writing cleaned Indus parameter file → {out_path}")

    ds_cropped.to_netcdf(
        out_path,
        format='NETCDF4_CLASSIC',
        engine='netcdf4',
        encoding=encoding_dict
    )

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"  File size: {size_mb:.1f} MB")

print("\nIndus parameter file created successfully (exact same format/encoding as global + Mekong).")
print(f"New file: {out_path}")
print("You can now point your vic_indus_config.txt to this file.")
