import os
import pandas as pd
import numpy as np
import datetime
from netCDF4 import Dataset, num2date

# -------------------------------------------------
# Paths
# -------------------------------------------------
directory = r"D:\WUR\In-Situ_Data\NT_AUS"

files = {
    "DryRiver": {
        "file": "DryRiver_OzFlux_L6.nc",
        "soil_var": "Sws",
        "soil_valid_range": (0.0, 0.9)
    },
    "FoggDam": {
        "file": "FoggDam_OzFlux_L6.nc",
        "soil_var": "Sws_10",
        "soil_valid_range": (0.1, 1.2)
    }
}

output_csv = os.path.join(
    directory,
    "Daily_ET_SoilMoisture_DryRiver_FoggDam_wide.csv"
)

# -------------------------------------------------
# Helper
# -------------------------------------------------
def reduce_to_time_series(var):
    """
    Reduce NetCDF variable to 1D time series
    (assumes time is first dimension)
    """
    data = var[:].astype(float)

    fill = getattr(var, "_FillValue", None)
    if fill is not None:
        data[data == fill] = np.nan

    if data.ndim > 1:
        data = np.nanmean(data, axis=tuple(range(1, data.ndim)))

    return data

# -------------------------------------------------
# Extraction function
# -------------------------------------------------
def extract_daily_means(nc_path, site_name, soil_var, soil_range):
    records = []

    with Dataset(nc_path, mode="r") as nc:

        # -------------------------
        # TIME
        # -------------------------
        time_var = nc.variables["time"]
        time_vals = num2date(
            time_var[:],
            units=time_var.units,
            calendar=getattr(time_var, "calendar", "standard"),
            only_use_cftime_datetimes=True
        )

        dates = np.array([
            datetime.date(t.year, t.month, t.day)
            for t in time_vals
        ])

        # -------------------------
        # ET
        # -------------------------
        et = reduce_to_time_series(nc.variables["ET"])

        et_df = pd.DataFrame({
            "date": dates,
            "value": et
        }).dropna()

        et_daily = et_df.groupby("date")["value"].mean() * 86400  # Unit conversion

        for d, v in et_daily.items():
            records.append({
                "site_variable": f"{site_name}_ET",
                "date": d,
                "value": v
            })

        # -------------------------
        # Soil moisture
        # -------------------------
        sm = reduce_to_time_series(nc.variables[soil_var])
        sm[(sm < soil_range[0]) | (sm > soil_range[1])] = np.nan

        sm_df = pd.DataFrame({
            "date": dates,
            "value": sm
        }).dropna()

        sm_daily = sm_df.groupby("date")["value"].mean()

        for d, v in sm_daily.items():
            records.append({
                "site_variable": f"{site_name}_{soil_var}",
                "date": d,
                "value": v
            })

    return records

# -------------------------------------------------
# Run
# -------------------------------------------------
all_records = []

for site, info in files.items():
    nc_file = os.path.join(directory, info["file"])
    all_records.extend(
        extract_daily_means(
            nc_file,
            site,
            info["soil_var"],
            info["soil_valid_range"]
        )
    )

# -------------------------------------------------
# Convert to wide format
# -------------------------------------------------
df = pd.DataFrame(all_records)
df_wide = df.pivot(index="date", columns="site_variable", values="value")
df_wide.sort_index(inplace=True)
df_wide.reset_index(inplace=True)

# -------------------------------------------------
# Save CSV
# -------------------------------------------------
df_wide.to_csv(output_csv, index=False)

print("✅ Extraction successful (wide format)")
print(f"📁 Output: {output_csv}")