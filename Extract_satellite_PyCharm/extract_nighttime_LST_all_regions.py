# =============================================================================
# Script: extract_nighttime_LST_all_regions.py
# Purpose:
#   Extract NIGHTTIME Land Surface Temperature (LST) from MODIS Terra, MODIS Aqua,
#   and VIIRS/NPP across multiple regions and save all time series into ONE Excel
#   file with one sheet per region.
#
# Regions & satellites supported:
#   - BKJ               → only VIIRS/NPP
#   - Yucatán           → only VIIRS/NPP
#   - Mekong            → MODIS Terra + MODIS Aqua + VIIRS/NPP
#   - Pantanal          → MODIS Terra + MODIS Aqua + VIIRS/NPP
#   - Northern Territory (NT_AUS) → MODIS Terra + MODIS Aqua + VIIRS/NPP
#   - SE / Central Africa (SE_CA) → MODIS Terra + MODIS Aqua + VIIRS/NPP
#
# Output: D:\WUR\NASA_ESDS\LST&E_Night.xlsx
#         (one sheet per region)
# =============================================================================

import numpy as np
import os
import re
import pandas as pd
from datetime import datetime
from netCDF4 import Dataset
import h5py
from pathlib import Path

# =============================================================================
#  CONFIGURATION – Directories & output
# =============================================================================
BASE_ROOT = r"D:\WUR\NASA_ESDS"

OUTPUT_FILE = Path(BASE_ROOT) / "LST&E_Night.xlsx"

# Region → subfolder mapping (adjust if your folder names differ slightly)
REGION_DIRS = {
    "BKJ": {
        "VIIRS": r"BKJ\VIIRS_NPP_BKJ_LSurfT_Data",
    },
    "Yucatán": {
        "VIIRS": r"Yucatan\VIIRS_NPP_Yucatan_LSurfT_Data", # the old á is now an a in Yucatan because of an error
    },
    "Mekong": {
        "Terra": r"MODISTerra_Mekong_LST&E_Data_F19",
        "Aqua":  r"MODISAqua_Mekong_LST&E_Data_F19",
        "VIIRS": r"VIIRS_NPP_Mekong_LST&E_DATA_F19",
    },
    "Pantanal": {
        "Terra":   r"Pantanal\MODISTerra_Pantanal_LSurfT_Data",
        "Aqua":    r"Pantanal\MODISAqua_Pantanal_LSurfT_Data",
        "VIIRS":   r"Pantanal\VIIRS_NPP_Pantanal_LSurfT_Data",
    },
    "NT_AUS": {
        "Terra": r"NT_AUS\MODISTerra_NT_LSurfT_Data",
        "Aqua":  r"NT_AUS\MODISAqua_LSurfT_Data",
        "VIIRS": r"NT_AUS\VIIRS_NPP_NT_LSurfT_Data",
    },
    "SE_CA": {
        "Terra": r"SE_CA\MODISTerra_SECA_LSurfT_Data",
        "Aqua":  r"SE_CA\MODISAqua_SECA_LSurfT_Data",
        "VIIRS": r"SE_CA\VIIRS_NPP_SECA_LSurfT_Data",
    }
}

# =============================================================================
#  REGION-SPECIFIC BOUNDARIES & TILE GEOMETRIES
# =============================================================================

BOUNDARIES = {
    "BKJ": {
        "lat_min": 3.05,  "lat_max": 4.29,
        "lon_min": 114.86, "lon_max": 115.50
    },
    "Yucatán": {
        "lat_min": 16.0,  "lat_max": 21.7,
        "lon_min": -91.0, "lon_max": -86.6
    },
    "Mekong": {
        "lat_min": 8.54167,  "lat_max": 11.4583,
        "lon_min": 104.042,  "lon_max": 106.958
    },
    "Pantanal": {
        "lat_min": -18.5, "lat_max": -16.5,
        "lon_min": -59.5, "lon_max": -56.0
    },
    "NT_AUS": {
        "lat_min": -17.0, "lat_max": -10.9,
        "lon_min": 129.0, "lon_max": 138.0
    },
    "SE_CA": {
        "lat_min": -22.5, "lat_max": -15.5,
        "lon_min": 17.0,  "lon_max": 28.0
    }
}

# Tile geometries (copied / adapted from your scripts)

GEOMETRIES = {

    # BKJ – only VIIRS – single tile
    "BKJ": {
        "VIIRS": {
            "h29v08": [
                (109.5885, 0.0005), (120.0192, -0.0112),
                (121.8612, 9.9998), (111.2665, 10.0097)
            ]
        }
    },

    # Yucatán – only VIIRS
    "Yucatán": {
        "VIIRS": {
            "h09v06": [(-95.7583, 19.8939), (-84.8251, 19.9359),
                       (-92.0525, 30.0438), (-103.923, 30.0)],
            "h09v07": [(-91.3988, 9.9459), (-80.9271, 9.9705),
                       (-84.8012, 20.0238), (-95.776, 20.0)]
        }
    },

    # Mekong (same tiles for MODIS & VIIRS)
    "Mekong": {
        "Terra": {
            "h28v08": [(99.6259, 0.0004), (110.0184, -0.0102),
                       (111.7068, 9.9998), (101.1513, 10.0088)],
            "h28v07": [(101.1705, 9.9726), (111.7183, 9.9416),
                       (117.0729, 19.9995), (106.0116, 20.0297)]
        },
        "Aqua": {  # assuming same geometry as Terra
            "h28v08": [(99.6259, 0.0004), (110.0184, -0.0102),
                       (111.7068, 9.9998), (101.1513, 10.0088)],
            "h28v07": [(101.1705, 9.9726), (111.7183, 9.9416),
                       (117.0729, 19.9995), (106.0116, 20.0297)]
        },
        "VIIRS": {  # same as MODIS
            "h28v08": [(99.6259, 0.0004), (110.0184, -0.0102),
                       (111.7068, 9.9998), (101.1513, 10.0088)],
            "h28v07": [(101.1705, 9.9726), (111.7183, 9.9416),
                       (117.0729, 19.9995), (106.0116, 20.0297)]
        }
    },

    # Pantanal – different boundaries for LST&E vs ET (but we only use LST&E here)
    "Pantanal": {
        "Terra": {
            "LST_E": [(-63.8551, -19.9958), (-53.2133, -19.9958),
                      (-50.7769, -10.0042), (-60.9314, -10.0042)]
        },
        "Aqua": {
            "LST_E": [(-63.8551, -19.9958), (-53.2133, -19.9958),
                      (-50.7769, -10.0042), (-60.9314, -10.0042)]
        },
        "VIIRS": {
            "h30v11": [(-63.8507, -20), (-52.9886, -20.0151),
                       (-50.5717, -9.9674), (-60.9332, -9.9517)]
        }
    },

    # NT_AUS
    "NT_AUS": {
        "Terra": {
            "h30v10": [(127.6969, -19.9958), (138.3386, -19.9958),
                       (132.0046, -10.0042), (121.8501, -10.0042)],
            "h31v10": [(138.3387, -19.9958), (148.9804, -19.9958),
                       (142.1591, -10.0042), (132.0046, -10.0042)]
        },
        "Aqua": {  # same as Terra
            "h30v10": [(127.6969, -19.9958), (138.3386, -19.9958),
                       (132.0046, -10.0042), (121.8501, -10.0042)],
            "h31v10": [(138.3387, -19.9958), (148.9804, -19.9958),
                       (142.1591, -10.0042), (132.0046, -10.0042)]
        },
        "VIIRS": {
            "h30v10": [(127.22, -20.0356), (138.3431, -20.0),
                       (132.0209, -9.9375), (121.4097, -9.9745)],
            "h31v10": [(137.825, -20.0386), (148.9849, -20.0),
                       (142.1754, -9.9353), (131.5302, -9.9755)]
        }
    },

    # SE_CA
    "SE_CA": {
        "Terra": {
            "h19v10": [(10.6373, -19.9958), (21.2791, -19.9958),
                       (20.3048, -10.0042), (10.1503, -10.0042)],
            "h19v11": [(11.5422, -29.9958), (23.0892, -29.9958),
                       (21.2802, -20.0042), (10.6379, -20.0042)],
            "h20v10": [(21.2791, -19.9958), (31.9209, -19.9958),
                       (30.4593, -10.0042), (20.3048, -10.0042)],
            "h20v11": [(23.0892, -29.9958), (34.6362, -29.9958),
                       (31.9226, -20.0042), (21.2803, -20.0042)]
        },
        "Aqua": {  # same tiles/geometry
            "h19v10": [(10.6373, -19.9958), (21.2791, -19.9958),
                       (20.3048, -10.0042), (10.1503, -10.0042)],
            "h19v11": [(11.5422, -29.9958), (23.0892, -29.9958),
                       (21.2802, -20.0042), (10.6379, -20.0042)],
            "h20v10": [(21.2791, -19.9958), (31.9209, -19.9958),
                       (30.4593, -10.0042), (20.3048, -10.0042)],
            "h20v11": [(23.0892, -29.9958), (34.6362, -29.9958),
                       (31.9226, -20.0042), (21.2803, -20.0042)]
        },
        "VIIRS": {  # same as MODIS
            "h19v10": [(10.5988, -20.0045), (21.2910, -19.9998),
                       (20.3182, -9.9589), (10.1165, -9.9635)],
            "h19v11": [(11.4987, -30.008), (23.1013, -29.9997),
                       (21.2877, -19.916), (10.5996, -19.9237)],
            "h20v10": [(21.1986, -20.0072), (31.9321, -19.9998),
                       (30.4737, -9.9571), (20.2324, -9.9645)],
            "h20v11": [(23.0001, -30.0129), (34.6472, -29.9997),
                       (31.9280, -19.913), (21.1986, -19.9254)]
        }
    }
}

# =============================================================================
#  Utility functions
# =============================================================================

def extract_date_from_filename(filename):
    match = re.search(r"A(\d{4})(\d{3})", filename)
    if match:
        year = int(match.group(1))
        doy = int(match.group(2))
        return (datetime(year, 1, 1) + pd.to_timedelta(doy - 1, unit="D")).date()
    return None


def compute_lat_lon(boundary_points, n_rows, n_cols):
    bl, br, tr, tl = boundary_points[:4]  # take first 4 points
    t = np.linspace(0, 1, n_rows)[:, None]
    s = np.linspace(0, 1, n_cols)[None, :]

    left_lon = bl[0] + t * (tl[0] - bl[0])
    left_lat = bl[1] + t * (tl[1] - bl[1])
    right_lon = br[0] + t * (tr[0] - br[0])
    right_lat = br[1] + t * (tr[1] - br[1])

    lon_array = left_lon + s * (right_lon - left_lon)
    lat_array = left_lat + s * (right_lat - left_lat)
    return lat_array, lon_array


def filter_by_boundary(data, lat, lon, bounds):
    mask = (
        (lat >= bounds["lat_min"]) & (lat <= bounds["lat_max"]) &
        (lon >= bounds["lon_min"]) & (lon <= bounds["lon_max"])
    )
    return data[mask]


def load_modis_night_lst(file_path):
    """MODIS Terra/Aqua – LST_Night_1km"""
    try:
        with Dataset(file_path, "r") as hdf:
            data = hdf.variables["LST_Night_1km"][:]
        return data, data.shape
    except Exception as e:
        print(f"  Failed to read MODIS night LST from {os.path.basename(file_path)}: {e}")
        return None, (0, 0)


def load_viirs_night_lst(file_path):
    """VIIRS/NPP – LST_Night_1KM (Collection 2 path)"""
    try:
        with Dataset(file_path, "r") as hdf:
            g = hdf.groups["HDFEOS"].groups["GRIDS"].groups["VIIRS_Grid_8Day_1km_LST21"].groups["Data Fields"]
            data = g.variables["LST_Night_1KM"][:]
        return data, data.shape
    except Exception as e:
        print(f"  Failed to read VIIRS night LST from {os.path.basename(file_path)}: {e}")
        return None, (0, 0)


def process_region_night_lst(region, sat):
    """Main function per region + satellite"""
    if region not in REGION_DIRS or sat not in REGION_DIRS[region]:
        print(f"→ Skipping {region} – {sat} (no directory defined)")
        return pd.DataFrame()

    subdir = REGION_DIRS[region][sat]
    full_dir = Path(BASE_ROOT) / subdir

    if not full_dir.is_dir():
        print(f"→ Directory not found: {full_dir}")
        return pd.DataFrame()

    print(f"\n→ Processing {region} – {sat}   ({full_dir})")

    bounds = BOUNDARIES[region]
    tile_geoms = GEOMETRIES[region][sat]

    all_files = [f for f in os.listdir(full_dir) if f.lower().endswith((".hdf", ".h5"))]
    if not all_files:
        print("  No .hdf / .h5 files found.")
        return pd.DataFrame()

    files_by_date = {}
    for fname in all_files:
        date = extract_date_from_filename(fname)
        if date:
            files_by_date.setdefault(date, []).append(fname)

    results = []

    for date in sorted(files_by_date):
        valid_pixels = []

        for fname in files_by_date[date]:
            file_path = full_dir / fname

            # Select loader
            if sat == "VIIRS":
                data, shape = load_viirs_night_lst(file_path)
            else:
                data, shape = load_modis_night_lst(file_path)

            if data is None or data.size == 0:
                continue

            n_rows, n_cols = shape

            # Find matching tile geometry
            tile_key = next((k for k in tile_geoms if k in fname), None)
            if tile_key is None:
                # For Pantanal MODIS we sometimes have special key "LST_E"
                if "LST_E" in tile_geoms and "LST_E" in tile_geoms:
                    tile_key = "LST_E"
                else:
                    continue

            lat, lon = compute_lat_lon(tile_geoms[tile_key], n_rows, n_cols)

            subset = filter_by_boundary(data, lat, lon, bounds)
            valid = subset[subset > 0]

            if valid.size > 0:
                valid_pixels.append(valid)

        if valid_pixels:
            combined = np.concatenate(valid_pixels)
            avg_lst = np.mean(combined)
        else:
            avg_lst = np.nan

        results.append({"Date": date, "Night_LST": avg_lst})

    if results:
        df = pd.DataFrame(results)
        print(f"  → Found {len(df)} dates | mean LST = {df['Night_LST'].mean():.2f} K")
        return df.set_index("Date")
    else:
        print("  → No valid data found")
        return pd.DataFrame()


def main():
    writer = pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl")

    for region in ["BKJ", "Yucatán", "Mekong", "Pantanal", "NT_AUS", "SE_CA"]:
        print(f"\n{'='*70}\nRegion: {region}\n{'='*70}")

        region_dfs = []

        for sat in REGION_DIRS.get(region, {}):
            df_sat = process_region_night_lst(region, sat)
            if not df_sat.empty:
                df_sat.columns = [f"{sat}_Night_LST"]
                region_dfs.append(df_sat)

        if region_dfs:
            df_region = pd.concat(region_dfs, axis=1).sort_index()
            df_region.to_excel(writer, sheet_name=region)
            print(f"  Saved sheet '{region}'  ({len(df_region)} rows)")
        else:
            print("  No data available for this region.")

    writer.close()
    print(f"\nDone. Output written to:\n{OUTPUT_FILE}\n")


if __name__ == "__main__":
    main()