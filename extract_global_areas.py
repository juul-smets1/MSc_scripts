#!/usr/bin/env python3
import os
import numpy as np
import pandas as pd
import xarray as xr

def main():
    from dask.distributed import Client, LocalCluster

    # -------------------------
    # CONFIGURATION
    # -------------------------
    VIC_FILE = "/lustre/nobackup/WUR/ESG/smets008/mGV/validations/global/output/global_1990_2019_NH_NR_DP_S10.1990-01-01.nc"
    MGV_DIR = "/lustre/nobackup/WUR/ESG/smets008/zarr_mGV/output_data/global/file_by_year"
    OUT_DIR = "python_extract"

    os.makedirs(OUT_DIR, exist_ok=True)

    AREAS = {
        "Pantanal_Brazil_Bolivia": [-59.5, -56.0, -18.5, -16.5],
        "SouthEastern_Central_Africa": [17.0, 28.0, -22.5, -15.5],
        "Bornean_Karst_Jungle_Malaysia": [114.86, 115.5, 3.05, 4.29],
        "Yucatan_Peninsula": [-91.0, -86.6, 16.0, 21.7],
        "Northern_Territory_Australia": [129.0, 138.0, -17.0, -10.9]
    }

    VIC_VARS = {
        "OUT_PET": "PET_VIC",
        "OUT_EVAP": "ET_VIC",
        "OUT_SURF_TEMP": "Tsurf_VIC",
        "OUT_SOIL_MOIST": "SoilMoist_top_VIC"
    }

    MGV_VARS = {
        "potential_evaporation_summed_output": "PET_mGV",
        "total_et_output": "ET_mGV",
        "tsurf_output": "Tsurf_mGV",
        "soil_moisture_output": "SoilMoist_top_mGV"
    }

    # -------------------------
    # DASK SETUP
    # -------------------------
    n_cpus = int(os.environ.get("SLURM_CPUS_PER_TASK", 1))
    n_workers = min(16, n_cpus)
    threads_per_worker = max(1, n_cpus // n_workers)

    cluster = LocalCluster(
        n_workers=n_workers,
        threads_per_worker=threads_per_worker,
        processes=True
    )
    client = Client(cluster)
    print(client)

    # -------------------------
    # HELPER FUNCTION
    # -------------------------
    def extract_area_mean(ds, varname, lonmin, lonmax, latmin, latmax, sel_top_layer=False):
        if varname not in ds:
            return None

        da = ds[varname]

        vert_dims = [d for d in ("layer", "nlayer") if d in da.dims]
        if sel_top_layer and vert_dims:
            da = da.isel({vert_dims[0]: 0})

        da = da.sel(
            lon=slice(lonmin, lonmax),
            lat=slice(latmin, latmax)
        )

        return da.mean(dim=("lat", "lon"), skipna=True).load()

    # -------------------------
    # LOAD VIC DATA (ONCE)
    # -------------------------
    ds_vic = xr.open_dataset(VIC_FILE, engine="h5netcdf")

    time_index = pd.date_range(
        "1990-01-01",
        periods=ds_vic.sizes["time"],
        freq="D"
    )

    # -------------------------
    # LOOP OVER AREAS
    # -------------------------
    for area, (lonmin, lonmax, latmin, latmax) in AREAS.items():
        print(f"Processing {area}")

        df = pd.DataFrame({"date": time_index})

        # ---- VIC variables
        for var, col in VIC_VARS.items():
            sel_top = var == "OUT_SOIL_MOIST"
            da = extract_area_mean(
                ds_vic, var,
                lonmin, lonmax, latmin, latmax,
                sel_top_layer=sel_top
            )
            df[col] = da.values if da is not None else np.nan

        # ---- mGV variables (FILE BY FILE)
        mgv_series = {col: [] for col in MGV_VARS.values()}

        mgv_files = sorted(f for f in os.listdir(MGV_DIR) if f.endswith(".nc"))

        for fname in mgv_files:
            fpath = os.path.join(MGV_DIR, fname)

            try:
                ds = xr.open_dataset(fpath, engine="h5netcdf")

                for var, col in MGV_VARS.items():
                    sel_top = var == "soil_moisture_output"
                    da = extract_area_mean(
                        ds, var,
                        lonmin, lonmax, latmin, latmax,
                        sel_top_layer=sel_top
                    )
                    if da is not None:
                        mgv_series[col].append(da.values)
                    else:
                        mgv_series[col].append(np.nan)

                ds.close()

            except Exception as e:
                print(f"Skipping {fname}: {e}")
                for col in MGV_VARS.values():
                    mgv_series[col].append(np.nan)

        for col, values in mgv_series.items():
            df[col] = np.concatenate(values)

        out_csv = os.path.join(OUT_DIR, f"{area}_daily_1990_2019.csv")
        df.to_csv(out_csv, index=False)
        print(f"Written {out_csv}")

    ds_vic.close()
    client.close()
    print("All areas processed successfully!")


if __name__ == "__main__":
    main()

