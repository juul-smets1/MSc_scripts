"""
make_8day_means.py

Reads:
  D:\WUR\Thesis_model_runs\VIC-WUR\VIC_output_spin-up_analysis.xlsx
  D:\WUR\Thesis_model_runs\mGV\mGV_output_spin-up_analysis.xlsx

Computes 8-day averages per calendar year (windows starting: 1-Jan, 9-Jan, 17-Jan, ...)
Window = start_date .. start_date+7 (truncated at 31-Dec for that year)

Writes:
  D:\WUR\Thesis_model_runs\VIC_mGV_spin-up_8-day_means.xlsx

Author: Generated for you
"""

import os
import pandas as pd
import numpy as np
from datetime import timedelta

# -----------------------
# Configuration / paths
# -----------------------
base_out = r"D:\WUR\Thesis_model_runs"
vic_file = os.path.join(base_out, "VIC-WUR", "VIC_output_spin-up_analysis.xlsx")
mgv_file = os.path.join(base_out, "mGV", "mGV_output_spin-up_analysis.xlsx")
output_file = os.path.join(base_out, "VIC_mGV_spin-up_8-day_means.xlsx")

# expected variable names (as you specified)
vic_vars = [
    "Tsurf_S0_VIC","ET_S0_VIC","PET_S0_VIC",
    "Tsurf_S1_VIC","ET_S1_VIC","PET_S1_VIC",
    "Tsurf_S5_VIC","ET_S5_VIC","PET_S5_VIC",
    "Tsurf_S10_VIC","ET_S10_VIC","PET_S10_VIC"
]

mgv_vars = [
    "Tsurf_S0_mGV","ET_S0_mGV","PET_S0_mGV",
    "Tsurf_S1_mGV","ET_S1_mGV","PET_S1_mGV",
    "Tsurf_S5_mGV","ET_S5_mGV","PET_S5_mGV",
    "Tsurf_S10_mGV","ET_S10_mGV","PET_S10_mGV"
]

# analysis period (this is the period that should exist in the input spreadsheets)
period_start = pd.Timestamp("2000-01-01")
period_end   = pd.Timestamp("2019-12-31")

# -----------------------
# Helper: build 8-day window starts for each year
# -----------------------
def build_8day_window_starts(year):
    """
    Return a list of (start_date, end_date) pairs for given calendar year.
    Each start is 1-Jan, 9-Jan, 17-Jan, ... up to <= 31-Dec.
    Each end = min(start + 7 days, 31-Dec-of-year).
    """
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
# Read input Excel files
# -----------------------
print("Reading input Excel files...")

if not os.path.isfile(vic_file):
    raise FileNotFoundError(f"VIC file not found: {vic_file}")
if not os.path.isfile(mgv_file):
    raise FileNotFoundError(f"mGV file not found: {mgv_file}")

# parse date column as datetime
vic_df = pd.read_excel(vic_file, parse_dates=["date"])
mgv_df = pd.read_excel(mgv_file, parse_dates=["date"])

# check that 'date' column exists
if "date" not in vic_df.columns or "date" not in mgv_df.columns:
    raise KeyError("Input Excel files must contain a 'date' column with daily dates.")

# set date as index for easier slicing
vic_df = vic_df.set_index("date").sort_index()
mgv_df = mgv_df.set_index("date").sort_index()

# verify variables exist; warn if missing
missing_vic = [v for v in vic_vars if v not in vic_df.columns]
missing_mgv = [v for v in mgv_vars if v not in mgv_df.columns]
if missing_vic:
    print("Warning: the following VIC variables are missing from the VIC file:", missing_vic)
if missing_mgv:
    print("Warning: the following mGV variables are missing from the mGV file:", missing_mgv)

# We'll only attempt averages for variables that actually exist
vic_present = [v for v in vic_vars if v in vic_df.columns]
mgv_present = [v for v in mgv_vars if v in mgv_df.columns]

# -----------------------
# Build windows across years 2000-2019
# -----------------------
all_windows = []  # list of (start, end)
for yr in range(period_start.year, period_end.year + 1):
    all_windows.extend(build_8day_window_starts(yr))

# Filter windows to those that overlap the overall period (2000-01-01 to 2019-12-31)
valid_windows = []
for s,e in all_windows:
    if e < period_start or s > period_end:
        continue
    # clip to overall period
    s2 = max(s, period_start)
    e2 = min(e, period_end)
    valid_windows.append((s2, e2))

# Build result DataFrame index: use start dates (as formatted string like "1-1-2000")
window_starts = [s for s,e in valid_windows]
date_strings = [f"{d.day}-{d.month}-{d.year}" for d in window_starts]

result_index = pd.Index(window_starts, name="date")
result_df = pd.DataFrame(index=result_index)

# -----------------------
# Compute 8-day averages for each variable
# -----------------------
print("Computing 8-day averages...")

def compute_means_for_df(source_df, var_list, prefix):
    """
    Compute means for each window in valid_windows for variables in var_list.
    Returns a DataFrame indexed by window_starts with columns named exactly as var_list (or prefix+var).
    """
    out = pd.DataFrame(index=result_index)
    for v in var_list:
        col_values = []
        for s,e in valid_windows:
            # inclusive selection: dates between s and e inclusive
            # source_df index is datetime index
            sel = source_df.loc[s:e, v] if v in source_df.columns else pd.Series(index=pd.date_range(s,e), dtype=float)
            # compute mean skipping NaNs
            if sel.size == 0:
                mean_val = np.nan
            else:
                mean_val = sel.mean(skipna=True)
            col_values.append(mean_val)
        out[v] = col_values
    # rename columns with prefix if provided (we already pass full var names; prefix not needed)
    return out

# VIC
vic_8d = compute_means_for_df(vic_df, vic_present, prefix="VIC")
# mGV
mgv_8d = compute_means_for_df(mgv_df, mgv_present, prefix="mGV")

# Merge them side-by-side. Keep column order: VIC vars first then mGV vars
merged = pd.concat([vic_8d, mgv_8d], axis=1)

# Reindex to ensure correct order (should already be correct)
merged = merged.reindex(result_index)

# Insert a human-friendly date string column (day-month-year no leading zeros) as first column
date_strs = [f"{d.day}-{d.month}-{d.year}" for d in merged.index]
merged_insert = merged.copy()
merged_insert.insert(0, "date", date_strs)

# -----------------------
# Write to Excel
# -----------------------
print(f"Writing 8-day means to: {output_file}")
with pd.ExcelWriter(output_file, engine="openpyxl", datetime_format="yyyy-mm-dd") as writer:
    merged_insert.to_excel(writer, sheet_name="8day_means", index=False)

print("Done. Output saved.")
