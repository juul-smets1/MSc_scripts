#!/usr/bin/env python3
"""
Crop VIC forcing files (lwdown, prec, psurf, swdown, tair, vp, wind) to exact weak-scaling rectangles.
Only keeps years 1990–2019 (inclusive).
Uses index-based slicing (.isel) to avoid coordinate floating-point mismatch.
Preserves original dtypes, _FillValue, missing_value, attributes.
Removes unsupported encoding keys for NETCDF4_CLASSIC backend.
Outputs go into WSx/<variable>/ folders.
"""

import os
import xarray as xr
import numpy as np
from pathlib import Path

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────

BASE_FORCING_DIR = "/lustre/nobackup/WUR/ESG/smets008/l_o_b_mGV/input_data/global/forcing"
BASE_OUTPUT_DIR = "/lustre/nobackup/WUR/ESG/smets008/VRAM_zarr_mGV/input_data/Weak_Scaling"

# Fixed lower-left corner (lon_idx, lat_idx) — 0-based indices
I_START = 2040
J_START = 875

# Years to keep (inclusive)
START_YEAR = 1990
END_YEAR = 2019

# Forcing variables and their file prefixes
FORCING_VARS = {
    "lwdown": "lwdown_WFDE5_v2.0_5arcmin_",
    "prec":   "prec_WFDE5_CRU+GPCC_v2.0_5arcmin_",
    "psurf":  "psurf_WFDE5_v2.0_5arcmin_",
    "swdown": "swdown_WFDE5_v2.0_5arcmin_",
    "tair":   "tair_WFDE5_v2.0_5arcmin_",
    "vp":     "vp_WFDE5_v2.0_5arcmin_",
    "wind":   "wind_WFDE5_v2.0_5arcmin_",
}

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

print("Script started. Using index-based cropping (.isel) to avoid coordinate mismatch.")

for i_end, j_end, ws_num, name, cell_comment in configs:
    print(f"\n=== Processing {name} – {cell_comment} ===")

    # Inclusive index ranges (0-based)
    lon_slice = slice(I_START, i_end + 1)
    lat_slice = slice(J_START, j_end + 1)

    lon_count = i_end - I_START + 1
    lat_count = j_end - J_START + 1
    total_cells = lon_count * lat_count
    print(f"  lon range: {I_START} to {i_end} ({lon_count} cells)")
    print(f"  lat range: {J_START} to {j_end} ({lat_count} cells)")
    print(f"  total cells: {total_cells}")

    # Base output directory for this WS
    ws_dir = os.path.join(BASE_OUTPUT_DIR, f"WS{ws_num}")
    os.makedirs(ws_dir, exist_ok=True)

    for var_name, file_prefix in FORCING_VARS.items():
        print(f"  → Cropping {var_name} ...")

        var_output_dir = os.path.join(ws_dir, var_name)
        os.makedirs(var_output_dir, exist_ok=True)

        # Process each year separately (1990–2019)
        for year in range(START_YEAR, END_YEAR + 1):
            input_file = os.path.join(BASE_FORCING_DIR, var_name, f"{file_prefix}{year}.nc")
            if not os.path.exists(input_file):
                print(f"    WARNING: File missing: {input_file}")
                continue

            out_name = f"{file_prefix}{year}.nc"
            out_path = os.path.join(var_output_dir, out_name)

            # Skip if already exists
            if os.path.exists(out_path):
                print(f"    Skipping (already exists): {out_path}")
                continue

            print(f"    Cropping year {year}: {input_file} → {out_path}")

            # Open yearly file
            ds_year = xr.open_dataset(input_file)

            # Subset spatial dimensions using **index-based** slicing
            ds_cropped = ds_year.isel(lon=lon_slice, lat=lat_slice)

            # Prepare safe encoding: copy original, remove unsupported, force zlib
            encoding_dict = {}
            for var in ds_cropped.variables:
                if var in ['time', 'lon', 'lat', 'crs']:
                    encoding_dict[var] = {}
                    continue

                orig_enc = ds_year[var].encoding.copy()

                # Remove unsupported keys
                unsupported_keys = ['szip', 'zstd', 'bzip2', 'blosc', 'preferred_chunks',
                                    'fletcher32', 'contiguous', 'chunksizes']
                for k in list(orig_enc.keys()):
                    if k in unsupported_keys:
                        del orig_enc[k]

                # Force safe compression
                orig_enc['zlib'] = True
                orig_enc['complevel'] = 5
                orig_enc['shuffle'] = True

                # Preserve dtype and FillValue
                if 'dtype' in ds_year[var].encoding:
                    orig_enc['dtype'] = ds_year[var].encoding['dtype']
                if '_FillValue' in ds_year[var].encoding:
                    orig_enc['_FillValue'] = ds_year[var].encoding['_FillValue']

                encoding_dict[var] = orig_enc

            # Remove unwanted NaN FillValue on vars without original explicit fill
            for var in ds_cropped.variables:
                if '_FillValue' in ds_cropped[var].encoding and np.isnan(ds_cropped[var].encoding['_FillValue']):
                    if '_FillValue' not in ds_year[var].encoding:
                        del ds_cropped[var].encoding['_FillValue']

            # Write cropped file
            ds_cropped.to_netcdf(
                out_path,
                format='NETCDF4_CLASSIC',
                engine='netcdf4',
                encoding=encoding_dict
            )

            size_mb = os.path.getsize(out_path) / (1024 * 1024)
            print(f"    Written: {out_path} ({size_mb:.1f} MB)")

            # Close file
            ds_year.close()

print("\nAll forcing data cropping completed for 1990–2019.")
print(f"Check output directories under: {BASE_OUTPUT_DIR}/WS*/")
