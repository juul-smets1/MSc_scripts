# =============================================================================
# Script: Satellite_In-Situ_data__clean_fixed.py
# Purpose:
#   Extract POINT values of ET (MODIS & VIIRS) and Soil Moisture (ESA CCI)
#   **only** from directories relevant to each station's region
#
# Output columns per station (when ET is requested):
#   date | ET_Terra_{station} | ET_Aqua_{station} | ET_VIIRS_{station} | SM_{station} (if requested)
#
# Stations → required data → region → directories:
#   BR-Npw         → ET          → Pantanal
#   MX-PMm         → ET          → Yucatán
#   NT_FoggDam     → ET + SM     → NT_AUS
#   NT_DryRiver    → ET + SM     → NT_AUS
#   NT_CosmOz_Daly →     SM      → NT_AUS
#
# Output: D:\WUR\In-Situ_Data\Satellite_In-Situ_Data.xlsx
# =============================================================================

import numpy as np
import os
import re
import pandas as pd
from datetime import datetime
from pathlib import Path
from netCDF4 import Dataset
import h5py
import xarray as xr
from typing import List, Tuple, Optional, Dict

# ────────────────────────────────────────────────
# CONFIGURATION – strict region → directory mapping
# ────────────────────────────────────────────────

BASE_ROOT = r"D:\WUR\NASA_ESDS"
ESA_SM_ROOT = r"D:\WUR\ESA_CCI_Soil_Moisture"

OUTPUT_DIR  = r"D:\WUR\In-Situ_Data"
OUTPUT_FILE = Path(OUTPUT_DIR) / "Satellite_In-Situ_Data.xlsx"

STATION_CONFIG = {
    "BR-Npw": {
        "lat": -16.4980,
        "lon": -56.4120,
        "variables": ["ET"],
        "region": "Pantanal",
        "et_dirs": {
            "MODISTerra": r"Pantanal\MODISTerra_PantanalETData",
            "MODISAqua":  r"Pantanal\MODISAqua_PantanalETData",
            "VIIRS_NPP":  r"Pantanal\VIIRS_NPP_PantanalETData",
        }
    },
    "MX-PMm": {
        "lat": 20.8462,
        "lon": -86.8992,
        "variables": ["ET"],
        "region": "Yucatán",
        "et_dirs": {
            "VIIRS_NPP": r"Yucatan\VIIRS_NPP_YucatanETData",
        }
    },
    "NT_FoggDam": {
        "lat": -12.5452,
        "lon": 131.3072,
        "variables": ["ET", "SM"],
        "region": "NT_AUS",
        "et_dirs": {
            "MODISTerra": r"NT_AUS\MODISTerra_NT_ETData",
            "MODISAqua":  r"NT_AUS\MODISAqua_NT_ETData",
            "VIIRS_NPP":  r"NT_AUS\VIIRS_NPP_NT_ETData",
        }
    },
    "NT_DryRiver": {
        "lat": -15.2588,
        "lon": 132.3706,
        "variables": ["ET", "SM"],
        "region": "NT_AUS",
        "et_dirs": {
            "MODISTerra": r"NT_AUS\MODISTerra_NT_ETData",
            "MODISAqua":  r"NT_AUS\MODISAqua_NT_ETData",
            "VIIRS_NPP":  r"NT_AUS\VIIRS_NPP_NT_ETData",
        }
    },
    "NT_CosmOz_Daly": {
        "lat": -14.16,
        "lon": 131.39,
        "variables": ["SM"],
        "region": "NT_AUS",
        "et_dirs": {}
    }
}

# Geometry definitions (only ET related)
VIIRS_ET_GEOMETRIES = {
    "Pantanal": {
        "default": [(-63.8507, -20.0), (-52.9886, -20.0151),
                    (-50.5717, -9.9674), (-60.9332, -9.9517)]
    },
    "Yucatán": {
        "h09v06": [(-95.7583, 19.8939), (-84.8251, 19.9359),
                   (-92.0525, 30.0438), (-103.923, 30.0)],
        "h09v07": [(-91.3988, 9.9459), (-80.9271, 9.9705),
                   (-84.8012, 20.0238), (-95.776, 20.0)]
    },
    "NT_AUS": {
        "h30v10": [(127.22, -20.0356), (138.3431, -20.0),
                   (132.0209, -9.9375), (121.4097, -9.9745)],
        "h31v10": [(137.825, -20.0386), (148.9849, -20.0),
                   (142.1754, -9.9353), (131.5302, -9.9755)]
    }
}

MODIS_ET_GEOMETRIES = {
    "Pantanal": {
        "default": [(-63.8506663420922, -19.9999999982039),
                    (-52.9885896490026, -20.0151416658559),
                    (-50.5717093742954, -9.96742499665193),
                    (-60.9332459081005, -9.95174301126409)]
    },
    "NT_AUS": {
        "h30v10": [(138.343110407867, -19.9999999982039),
                   (132.020927894706, -9.93746671411948),
                   (121.409671246333, -9.97449019926359),
                   (127.219958378815, -20.0355981480789)],
        "h31v10": [(148.984888131549, -19.9999999982039),
                   (142.175397358673, -9.93527477182093),
                   (131.530219601717, -9.97545162476126),
                   (137.825020464527, -20.0385919212958)]
    }
}

# ────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────

def compute_lat_lon(corners, n_rows: int, n_cols: int):
    bl, br, tr, tl = corners[:4]
    t = np.linspace(0, 1, n_rows)[:, None]
    s = np.linspace(0, 1, n_cols)[None, :]
    left_lon  = bl[0] + t * (tl[0] - bl[0])
    left_lat  = bl[1] + t * (tl[1] - bl[1])
    right_lon = br[0] + t * (tr[0] - br[0])
    right_lat = br[1] + t * (tr[1] - br[1])
    lon_grid = left_lon + s * (right_lon - left_lon)
    lat_grid = left_lat + s * (right_lat - left_lat)
    return lat_grid, lon_grid


def bilinear_interpolate(data, lat_grid, lon_grid, target_lat, target_lon):
    i = np.searchsorted(lat_grid[:,0], target_lat) - 1
    j = np.searchsorted(lon_grid[0,:], target_lon) - 1
    if i < 0 or j < 0 or i+1 >= lat_grid.shape[0] or j+1 >= lon_grid.shape[1]:
        return np.nan

    lat0, lat1 = lat_grid[i,j], lat_grid[i+1,j]
    lon0, lon1 = lon_grid[i,j], lon_grid[i,j+1]

    if lat1 == lat0 or lon1 == lon0:
        return float(data[i,j])

    denom = (lat1-lat0)*(lon1-lon0)
    if denom == 0:
        return np.nan

    w00 = (lat1-target_lat)*(lon1-target_lon) / denom
    w10 = (target_lat-lat0)*(lon1-target_lon) / denom
    w01 = (lat1-target_lat)*(target_lon-lon0) / denom
    w11 = (target_lon-lon0)*(target_lat-lat0) / denom

    val = (w00*data[i,j] + w10*data[i+1,j] +
           w01*data[i,j+1] + w11*data[i+1,j+1])
    return val if np.isfinite(val) else np.nan


def extract_date_from_filename(fn: str) -> Optional[datetime.date]:
    m = re.search(r"A(\d{4})(\d{3})", fn)
    if m:
        y, d = int(m.group(1)), int(m.group(2))
        return (datetime(y, 1, 1) + pd.Timedelta(d-1, unit="D")).date()
    return None


# ────────────────────────────────────────────────
# ET value extraction
# ────────────────────────────────────────────────

def get_et_value(file_path: Path, lat_t: float, lon_t: float, region: str, sensor: str) -> float:
    try:
        if sensor == "VIIRS_NPP":
            with h5py.File(file_path, "r") as h5:
                path = "/HDFEOS/GRIDS/VIIRS_Grid_ETLE/Data Fields/ET_500m"
                if path not in h5:
                    return np.nan
                data = h5[path][:]
        else:
            with Dataset(file_path, "r") as ds:
                if "ET_500m" not in ds.variables:
                    return np.nan
                data = ds.variables["ET_500m"][:]

        if data.ndim != 2:
            return np.nan

        rows, cols = data.shape

        geom_dict = VIIRS_ET_GEOMETRIES if sensor == "VIIRS_NPP" else MODIS_ET_GEOMETRIES
        corners = None
        fname_lower = file_path.name.lower()
        expected_tiles = list(geom_dict.get(region, {}).keys())

        for key, pts in geom_dict.get(region, {}).items():
            if key.lower() in fname_lower or key == "default":
                corners = pts
                break

        if corners is None:
            print(f"  WARNING: No geometry match for {file_path.name}")
            print(f"           Expected one of: {expected_tiles} (case-insensitive)")
            return np.nan

        lat_g, lon_g = compute_lat_lon(corners, rows, cols)
        val = bilinear_interpolate(data, lat_g, lon_g, lat_t, lon_t)

        return float(val) if np.isfinite(val) and 0 <= val <= 10000 else np.nan

    except Exception as e:
        print(f"  Read error {file_path.name}: {e}")
        return np.nan


# ────────────────────────────────────────────────
# Main collection – per station
# ────────────────────────────────────────────────

def collect_station_data(station: str, cfg: dict) -> pd.DataFrame:
    lat, lon = cfg["lat"], cfg["lon"]
    vars_needed = cfg["variables"]
    region = cfg["region"]
    et_dir_patterns = cfg.get("et_dirs", {})

    print(f"\n{'═'*75}\n{station} ({lat:.4f}, {lon:.4f}) – {region}")
    print(f"  Needed: {', '.join(vars_needed)}\n")

    # Collect ET per sensor
    et_data: dict[str, list[tuple[datetime.date, float]]] = {
        "Terra": [], "Aqua": [], "VIIRS": []
    }
    sm_data: list[tuple[datetime.date, float]] = []

    # ─── ET per sensor ──────────────────────────────────
    if "ET" in vars_needed and et_dir_patterns:
        sensor_map = {
            "MODISTerra": "Terra",
            "MODISAqua":  "Aqua",
            "VIIRS_NPP":  "VIIRS"
        }

        for sensor_key, rel_path in et_dir_patterns.items():
            full_dir = Path(BASE_ROOT) / rel_path
            if not full_dir.is_dir():
                print(f"  Directory missing: {full_dir}")
                continue

            pattern = "*.h5" if sensor_key == "VIIRS_NPP" else "*.hdf"
            files = sorted(full_dir.glob(pattern))
            print(f"  {sensor_key}: {len(files)} files in {rel_path}")

            target_col = sensor_map[sensor_key]

            for fp in files:
                date = extract_date_from_filename(fp.name)
                if not date:
                    continue
                val = get_et_value(fp, lat, lon, region, sensor_key)
                if np.isfinite(val):
                    et_data[target_col].append((date, val))

    # ─── SM (ESA CCI) ───────────────────────────────────
    if "SM" in vars_needed:
        nc_files = sorted(Path(ESA_SM_ROOT).rglob("*.nc"))
        print(f"  ESA CCI SM: {len(nc_files)} files")

        for fp in nc_files:
            m = re.search(r'(\d{8})', fp.name)
            if not m:
                continue
            try:
                date = datetime.strptime(m.group(1), "%Y%m%d").date()
            except:
                continue

            try:
                with xr.open_dataset(fp) as ds:
                    if 'sm' not in ds:
                        continue
                    val = ds['sm'].sel(lat=lat, lon=lon, method="nearest").item()
                    if np.isfinite(val):
                        sm_data.append((date, float(val)))
            except Exception as e:
                print(f"  SM read error {fp.name}: {e}")

    # ─── Build daily table ──────────────────────────────
    all_dates = sorted(set(
        d for sub in et_data.values() for d,_ in sub
    ).union(d for d,_ in sm_data))

    rows = []
    for d in all_dates:
        row = {"date": d}

        # ET columns
        for src in ["Terra", "Aqua", "VIIRS"]:
            vals = [v for dd, v in et_data[src] if dd == d]
            row[f"ET_{src}_{station}"] = vals[0] if vals else np.nan  # first value (or NaN)

        # SM column
        if "SM" in vars_needed:
            sm_vals = [v for dd, v in sm_data if dd == d]
            row[f"SM_{station}"] = sm_vals[0] if sm_vals else np.nan

        rows.append(row)

    # Create DataFrame
    if rows:
        df = pd.DataFrame(rows)
        df = df.sort_values("date").reset_index(drop=True)
    else:
        # Create empty DataFrame with correct columns to avoid KeyError
        columns = ["date"]
        if "ET" in vars_needed:
            columns += [f"ET_{src}_{station}" for src in ["Terra", "Aqua", "VIIRS"]]
        if "SM" in vars_needed:
            columns += [f"SM_{station}"]
        df = pd.DataFrame(columns=columns)

    # Summary
    et_counts = {src: df.get(f"ET_{src}_{station}", pd.Series()).notna().sum()
                 for src in ["Terra", "Aqua", "VIIRS"]}
    sm_count = df.get(f"SM_{station}", pd.Series()).notna().sum()

    print(f"  Result: {len(df)} days")
    print(f"    ET Terra: {et_counts['Terra']} valid")
    print(f"    ET Aqua:  {et_counts['Aqua']} valid")
    print(f"    ET VIIRS: {et_counts['VIIRS']} valid")
    if "SM" in vars_needed:
        print(f"    SM:       {sm_count} valid")
    print()

    return df


# ────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────

def main():
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl", date_format="YYYY-MM-DD") as writer:
        for station, cfg in STATION_CONFIG.items():
            df = collect_station_data(station, cfg)
            if df.empty:
                print(f"  → No data extracted for {station}")
                continue

            sheet = station[:31]
            df.to_excel(writer, sheet_name=sheet, index=False)
            print(f"  Sheet '{sheet}' written ({len(df)} rows)")

    print(f"\nFinished. File saved:\n{OUTPUT_FILE}\n")


if __name__ == "__main__":
    main()