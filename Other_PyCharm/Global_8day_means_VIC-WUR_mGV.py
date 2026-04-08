import os
import pandas as pd
import numpy as np
from datetime import timedelta

# -----------------------
# Configuration / paths
# -----------------------

base_dir = r"C:\Users\31623\Downloads\Juul\WUR\WUR MSc thesis\Data_MSc_thesis\python_extract_valid"

input_files = [
    "Bornean_Karst_Jungle_Malaysia_daily_1990_2019.csv",
    "Northern_Territory_Australia_daily_1990_2019.csv",
    "Pantanal_Brazil_Bolivia_daily_1990_2019.csv",
    "SouthEastern_Central_Africa_daily_1990_2019.csv",
    "Yucatan_Peninsula_daily_1990_2019.csv"
]

output_file = os.path.join(base_dir, "8day_Global_NH_NR_DP_S10.xlsx")

# Variables to process
variables = [
    "PET_VIC", "ET_VIC", "Tsurf_VIC",
    "PET_mGV", "ET_mGV", "Tsurf_mGV"
]

# Analysis period
period_start = pd.Timestamp("1990-01-01")
period_end   = pd.Timestamp("2019-12-31")

# -----------------------
# Helper: build 8-day window starts for each year
# -----------------------

def build_8day_window_starts(year):
    jan1 = pd.Timestamp(year=year, month=1, day=1)
    dec31 = pd.Timestamp(year=year, month=12, day=31)
    starts = []
    cur = jan1
    while cur <= dec31:
        end = cur + timedelta(days=7)
        if end > dec31:
            end = dec31
        starts.append((cur, end))
        cur = cur + timedelta(days=8)
    return starts

# -----------------------
# Build all 8-day windows
# -----------------------

all_windows = []
for yr in range(period_start.year, period_end.year + 1):
    all_windows.extend(build_8day_window_starts(yr))

valid_windows = []
for s, e in all_windows:
    if e < period_start or s > period_end:
        continue
    s2 = max(s, period_start)
    e2 = min(e, period_end)
    valid_windows.append((s2, e2))

window_starts = [s for s, e in valid_windows]
result_index = pd.Index(window_starts, name="date")

# -----------------------
# Function to compute 8-day means
# -----------------------

def compute_8day_means(df, var_list):
    out = pd.DataFrame(index=result_index)
    for v in var_list:
        if v not in df.columns:
            print(f"Warning: {v} not found in file.")
            out[v] = np.nan
            continue

        col_values = []
        for s, e in valid_windows:
            sel = df.loc[s:e, v]
            if sel.size == 0:
                mean_val = np.nan
            else:
                mean_val = sel.mean(skipna=True)
            col_values.append(mean_val)
        out[v] = col_values
    return out

# -----------------------
# Process all regions
# -----------------------

all_regions_output = []

print("Starting 8-day aggregation for all regions...\n")

for file in input_files:
    file_path = os.path.join(base_dir, file)
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        continue

    print(f"Processing: {file}")

    # Region name (remove extension)
    region_name = file.replace(".csv", "")

    # Read CSV (semicolon-separated)
    df = pd.read_csv(file_path, sep=';')

    # Clean column names: remove spaces and lowercase
    df.columns = df.columns.str.strip()
    df.columns = df.columns.str.lower()

    if "date" not in df.columns:
        print(f"Error: 'date' column not found in {file_path}. Columns: {df.columns.tolist()}")
        continue

    # Parse date column
    df["date"] = pd.to_datetime(df["date"], dayfirst=True)

    # Set index
    df = df.set_index("date").sort_index()

    # Restrict to analysis period
    df = df.loc[period_start:period_end]

    # Compute 8-day means
    lower_vars = [v.lower() for v in variables]
    region_8d = compute_8day_means(df, lower_vars)

    # Rename columns back to original case
    region_8d.columns = variables

    # Add region column
    region_8d.insert(0, "Region", region_name)

    # Add formatted date column
    date_strs = [f"{d.day}-{d.month}-{d.year}" for d in region_8d.index]
    region_8d.insert(1, "date", date_strs)

    all_regions_output.append(region_8d.reset_index(drop=True))

# -----------------------
# Combine all regions
# -----------------------

if not all_regions_output:
    raise ValueError("No data was processed. Check that the CSV files exist and are properly formatted.")

final_output = pd.concat(all_regions_output, ignore_index=True)

# -----------------------
# Write to Excel
# -----------------------

print(f"\nWriting output to: {output_file}")

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    final_output.to_excel(writer, sheet_name="8day_means", index=False)

print("Done. 8-day aggregation complete.")
