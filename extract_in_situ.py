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

OUT_DIR = "/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/python_extract_in-situ"
os.makedirs(OUT_DIR, exist_ok=True)

STATIONS = {
    "BR-Npw": {"lat": -16.4980, "lon": -56.4120, "vars": ["ET"]},
    "MX-PMm": {"lat": 20.8462, "lon": -86.8992, "vars": ["ET"]},
    "NT_FoggDam": {"lat": -12.5452, "lon": 131.3072, "vars": ["ET", "SM"]},
    "NT_DryRiver": {"lat": -15.2588, "lon": 132.3706, "vars": ["ET", "SM"]},
    "NT_CosmOz_Daly": {"lat": -14.16, "lon": 131.39, "vars": ["SM"]},
}

VIC_FILL = 9.96921e36
MGV_OCEAN_VALUE = 0.0


# -------------------------
# MEMORY-SAFE EXTRACTION
# -------------------------

def extract_point(
    ds,
    varname,
    lat,
    lon,
    sel_top_layer=False,
    fill_value=None,
    ocean_value=None,
):

    if varname not in ds:
        return None

    da = ds[varname]

    # ---- Reduce vertical dimension first
    if sel_top_layer:
        for d in ("layer", "nlayer", "top_layer"):
            if d in da.dims:
                da = da.isel({d: 0})
                break

    # ---- Compute nearest grid indices (cheap operation)
    lat_idx = np.abs(ds["lat"] - lat).argmin().item()
    lon_idx = np.abs(ds["lon"] - lon).argmin().item()

    # ---- Reduce spatial dimensions BEFORE loading
    da = da.isel(lat=lat_idx, lon=lon_idx)

    # Now da is (time) only

    if fill_value is not None:
        da = da.where(da != fill_value)

    if ocean_value is not None:
        da = da.where(da != ocean_value)

    # ---- Load only 1D time series
    return da.load()


# -------------------------
# MAIN
# -------------------------

def main():

    print("Opening VIC dataset...")

    ds_vic = xr.open_dataset(
        VIC_FILE,
        engine="h5netcdf",
        chunks={"time": 365},   # safe chunking
        decode_cf=True,
    )

    time_index = pd.date_range(
        "1990-01-01",
        periods=ds_vic.sizes["time"],
        freq="D",
    )

    mgv_files = sorted(f for f in os.listdir(MGV_DIR) if f.endswith(".nc"))

    for station, meta in STATIONS.items():

        print(f"\nProcessing {station}")

        lat = meta["lat"]
        lon = meta["lon"]
        required = meta["vars"]

        df = pd.DataFrame({"date": time_index})

        # ---------------------
        # VIC extraction
        # ---------------------

        if "ET" in required:
            da = extract_point(
                ds_vic,
                "OUT_EVAP",
                lat,
                lon,
                fill_value=VIC_FILL,
            )
            df["ET_VIC"] = da.values

        if "SM" in required:
            da = extract_point(
                ds_vic,
                "OUT_SOIL_MOIST",
                lat,
                lon,
                sel_top_layer=True,
                fill_value=VIC_FILL,
            )
            df["SM_VIC"] = da.values

        # ---------------------
        # mGV extraction
        # ---------------------

        mgv_data = {v: [] for v in required}

        for fname in mgv_files:

            fpath = os.path.join(MGV_DIR, fname)

            with xr.open_dataset(
                fpath,
                engine="h5netcdf",
                chunks={"time": 365},
                decode_cf=True,
            ) as ds:

                if "ET" in required:
                    da = extract_point(
                        ds,
                        "total_et_output",
                        lat,
                        lon,
                        ocean_value=MGV_OCEAN_VALUE,
                    )
                    mgv_data["ET"].append(da.values)

                if "SM" in required:
                    da = extract_point(
                        ds,
                        "soil_moisture_output",
                        lat,
                        lon,
                        sel_top_layer=True,
                        ocean_value=MGV_OCEAN_VALUE,
                    )
                    mgv_data["SM"].append(da.values)

        if "ET" in required:
            df["ET_mGV"] = np.concatenate(mgv_data["ET"])

        if "SM" in required:
            df["SM_mGV"] = np.concatenate(mgv_data["SM"])

        out_csv = os.path.join(OUT_DIR, f"{station}_daily_1990_2019.csv")
        df.to_csv(out_csv, index=False)

        print(f"Written {out_csv}")

    ds_vic.close()
    print("\nAll stations processed successfully!")


if __name__ == "__main__":
    main()

