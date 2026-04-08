#!/usr/bin/env python3
import os
import numpy as np
import pandas as pd
import xarray as xr

# -------------------------
# CONFIGURATION
# -------------------------
VIC_FILE = "/lustre/nobackup/WUR/ESG/smets008/mGV/validations/global/output/global_1990_2019_NH_NR_DP_S10.1990-01-01.nc"
MGV_DIR = "/lustre/nobackup/WUR/ESG/smets008/zarr_mGV/output_data/global/file_by_year"
OUT_DIR = "python_extract_valid"

os.makedirs(OUT_DIR, exist_ok=True)

AREAS = {
    "Pantanal_Brazil_Bolivia": (-59.5, -56.0, -18.5, -16.5),
    "SouthEastern_Central_Africa": (17.0, 28.0, -22.5, -15.5),
    "Bornean_Karst_Jungle_Malaysia": (114.86, 115.5, 3.05, 4.29),
    "Yucatan_Peninsula": (-91.0, -86.6, 16.0, 21.7),
    "Northern_Territory_Australia": (129.0, 138.0, -17.0, -10.9),
}

VIC_VARS = {
    "OUT_PET": "PET_VIC",
    "OUT_EVAP": "ET_VIC",
    "OUT_SURF_TEMP": "Tsurf_VIC",
    "OUT_SOIL_MOIST": "SoilMoist_top_VIC",
}

MGV_VARS = {
    "potential_evaporation_summed_output": "PET_mGV",
    "total_et_output": "ET_mGV",
    "tsurf_output": "Tsurf_mGV",
    "soil_moisture_output": "SoilMoist_top_mGV",
}

VIC_FILL = 9.96921e36
MGV_OCEAN_VALUE = 0.0


def extract_area_mean(
    ds,
    varname,
    lonmin,
    lonmax,
    latmin,
    latmax,
    sel_top_layer=False,
    fill_value=None,
    ocean_value=None,
):
    if varname not in ds:
        return None

    da = ds[varname]

    # vertical selection
    if sel_top_layer:
        for d in ("layer", "nlayer", "top_layer"):
            if d in da.dims:
                da = da.isel({d: 0})
                break

    if fill_value is not None:
        da = da.where(da != fill_value)

    if ocean_value is not None:
        da = da.where(da != ocean_value)

    da = da.sel(
        lon=slice(lonmin, lonmax),
        lat=slice(latmin, latmax),
    )

    # IMPORTANT: no .load()
    return da.mean(dim=("lat", "lon"), skipna=True)


def main():
    print("Opening VIC dataset...")
    ds_vic = xr.open_dataset(
        VIC_FILE,
        engine="h5netcdf",
        chunks={"time": 365},  # safe chunking
    )

    time_index = pd.date_range(
        "1990-01-01",
        periods=ds_vic.sizes["time"],
        freq="D",
    )

    mgv_files = sorted(f for f in os.listdir(MGV_DIR) if f.endswith(".nc"))

    for area, (lonmin, lonmax, latmin, latmax) in AREAS.items():
        print(f"\nProcessing {area}")

        df = pd.DataFrame({"date": time_index})

        # ---- VIC variables
        for var, col in VIC_VARS.items():
            da = extract_area_mean(
                ds_vic,
                var,
                lonmin,
                lonmax,
                latmin,
                latmax,
                sel_top_layer=(var == "OUT_SOIL_MOIST"),
                fill_value=VIC_FILL,
            )
            df[col] = da.values if da is not None else np.nan

        # ---- mGV variables
        mgv_data = {col: [] for col in MGV_VARS.values()}

        for fname in mgv_files:
            fpath = os.path.join(MGV_DIR, fname)
            with xr.open_dataset(fpath, engine="h5netcdf") as ds:
                for var, col in MGV_VARS.items():
                    da = extract_area_mean(
                        ds,
                        var,
                        lonmin,
                        lonmax,
                        latmin,
                        latmax,
                        sel_top_layer=(var == "soil_moisture_output"),
                        ocean_value=MGV_OCEAN_VALUE,
                    )
                    mgv_data[col].append(da.values if da is not None else np.nan)

        for col, vals in mgv_data.items():
            df[col] = np.concatenate(vals)

        out_csv = os.path.join(OUT_DIR, f"{area}_daily_1990_2019.csv")
        df.to_csv(out_csv, index=False)
        print(f"Written {out_csv}")

    ds_vic.close()
    print("\nAll areas processed successfully!")


if __name__ == "__main__":
    main()

