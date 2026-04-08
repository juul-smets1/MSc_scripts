import os
import xarray as xr
import pandas as pd
import numpy as np

# -------------------------------
# CONFIGURATION
# -------------------------------

base_dir = r"D:\WUR\Thesis_model_runs\VIC-WUR"

# Each entry: (filename, spin-up start date)
file_map = {
    "S0": ("mekong_2000_2019_NH_NR_DP_S0.2000-01-01.nc", "2000-01-01"),
    "S1": ("mekong_1999_2019_NH_NR_DP_S1.1999-01-01.nc", "1999-01-01"),
    "S5": ("mekong_1995_2019_NH_NR_DP_S5.1995-01-01.nc", "1995-01-01"),
    "S10": ("mekong_1990_2019_NH_NR_DP_S10.1990-01-01.nc", "1990-01-01"),
}

variables = {
    "OUT_SURF_TEMP": "Tsurf",
    "OUT_EVAP": "ET",
    "OUT_PET": "PET"
}

start_period = pd.Timestamp("2000-01-01")
end_period = pd.Timestamp("2019-12-31")
output_excel = os.path.join(base_dir, "VIC_output_spin-up_analysis.xlsx")


# -------------------------------
# FUNCTION TO PROCESS ONE FILE
# -------------------------------

def process_file(fname, spin_start_date):
    fpath = os.path.join(base_dir, fname)
    print(f"Opening {fpath} ...")

    ds = xr.open_dataset(fpath, engine="netcdf4", decode_times=False)

    # Number of timesteps in file
    n_steps = ds.dims["time"]
    print(f"Number of timesteps: {n_steps}")

    # Reconstruct daily dates using spin-up start date
    spin_start = pd.Timestamp(spin_start_date)
    dates = pd.date_range(spin_start, periods=n_steps, freq="D")

    df = pd.DataFrame(index=dates)

    # Process each variable
    for var_name, col_prefix in variables.items():
        if var_name not in ds:
            print(f"Variable {var_name} not found in {fname}, skipping.")
            df[col_prefix] = np.nan
            continue

        da = ds[var_name]

        # Convert to DataFrame: daily spatial average
        if var_name == "OUT_SURF_TEMP":
            # Exclude zeros
            avg_series = da.where(da != 0).mean(dim=("lat", "lon"))
        else:
            # Exclude NaNs
            avg_series = da.mean(dim=("lat", "lon"), skipna=True)

        # Convert to pandas Series
        s = pd.Series(avg_series.values, index=dates, name=f"{col_prefix}_{fname}")
        df[col_prefix] = s

    ds.close()

    # Slice to 2000-2019 period
    df = df.loc[start_period:end_period]

    # Rename columns to include spin-up
    df = df.rename(columns=lambda c: f"{c}_{fname.split('S')[-1].split('.')[0]}_VIC")

    return df


# -------------------------------
# PROCESS ALL FILES AND MERGE
# -------------------------------

all_dfs = []

for spin, (fname, spin_start) in file_map.items():
    df = process_file(fname, spin_start)
    all_dfs.append(df)

# Merge all spin-ups side by side
result_df = pd.concat(all_dfs, axis=1)

# Add date column
result_df.insert(0, "date", result_df.index)

# Write to Excel
print(f"Writing Excel file → {output_excel}")
result_df.to_excel(output_excel, index=False)
print("Finished extraction!")
