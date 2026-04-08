import os
import xarray as xr
import pandas as pd
import numpy as np

# -------------------------
# SETTINGS
# -------------------------
base_dir = r"D:\WUR\Thesis_model_runs\mGV"

file_map = {
    "S0": ("NH_NR_DP_S0_mekong_2000_2019.nc", "2000-01-01"),
    "S1": ("NH_NR_DP_S1_mekong_2000_2019.nc", "1999-01-01"),
    "S5": ("NH_NR_DP_S5_mekong_2000_2019.nc", "1995-01-01"),
    "S10": ("NH_NR_DP_S10_mekong_2000_2019.nc", "1990-01-01"),
}

var_names = {
    "tsurf": "tsurf_output",
    "et": "total_et_output",
    "pet": "potential_evaporation_summed_output",
}

output_excel = os.path.join(base_dir, "mGV_output_spin-up_analysis.xlsx")

# Target period
start_date = pd.Timestamp("2000-01-01")
end_date   = pd.Timestamp("2019-12-31")
full_dates = pd.date_range(start_date, end_date, freq="D")


# -------------------------
# MAIN FUNCTION
# -------------------------
def process_all():
    df = pd.DataFrame(index=full_dates)

    for spin, (fname, spin_start) in file_map.items():
        fpath = os.path.join(base_dir, fname)
        print(f"\nOpening {fpath} ...")

        ds = xr.open_dataset(fpath, decode_times=False)
        n_steps = ds.dims["time"]
        print(f"Number of timesteps: {n_steps}")

        # Reconstruct time axis from spin-up start date
        spin_start_date = pd.Timestamp(spin_start)
        time_index = pd.date_range(spin_start_date, periods=n_steps, freq="D")

        # Slice only 2000–2019 period
        sel_mask = (time_index >= start_date) & (time_index <= end_date)
        time_index_sel = time_index[sel_mask]
        sel_idx = np.where(sel_mask)[0]  # integer indices to slice the data

        # Process each variable
        for short, vname in var_names.items():
            if vname not in ds:
                print(f"Warning: {vname} not found in {fname}")
                continue

            da = ds[vname]

            # mask invalid values
            if short == "tsurf":
                da = da.where(da != 0)
            else:
                da = da.where(~np.isnan(da))

            # compute area mean over all non-time dims
            dims = [d for d in da.dims if d != "time"]
            da_mean = da.isel(time=sel_idx).mean(dim=dims, skipna=True)

            # convert to pandas Series with proper time index
            series = pd.Series(da_mean.values, index=time_index_sel)

            # assign column name
            if short == "tsurf":
                col = f"Tsurf_{spin}_mGV"
            elif short == "et":
                col = f"ET_{spin}_mGV"
            else:
                col = f"PET_{spin}_mGV"

            df[col] = series

        ds.close()

    # write Excel
    df_out = df.reset_index().rename(columns={"index": "date"})
    print(f"\nWriting Excel → {output_excel}")
    df_out.to_excel(output_excel, index=False)
    print("Finished successfully.")
    return df_out


# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    result_df = process_all()
    print(result_df.head())
