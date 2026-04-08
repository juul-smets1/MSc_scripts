# Script for merging the total precipitation data during the dry and wet season in Vietnam.

import pandas as pd
import os

# Paths
base_dir = r"C:\Users\31623\Downloads\Juul\WUR\WUR MSc thesis\Data_MSc_thesis\Unfiltered"
wet_file = os.path.join(base_dir, "raindataseason.xlsx_wetseason.csv")
dry_file = os.path.join(base_dir, "raindataseason.xlsx_dryseason.csv")

# The canonical column names we want (exact matching after stripping & uppercasing)
desired_cols = ["STATION_NA", "ELEVATION", "LATITUDE", "LONGITUDE", "DATE", "TPCP"]

def read_and_select(path):
    # read without forcing dtypes (we'll normalize after), handle semicolon and latin1
    df = pd.read_csv(path, encoding="latin1", sep=";", on_bad_lines="skip", dtype=str)
    # normalize column names: strip and uppercase for reliable matching
    df.columns = [c.strip().upper() for c in df.columns]
    # keep only columns that match our desired list (if present)
    keep = [c for c in df.columns if c in desired_cols]
    df = df[keep].copy()
    # rename columns back to canonical lowercase names for ease
    rename_map = { "STATION_NA":"STATION_NA",
                   "ELEVATION":"ELEVATION",
                   "LATITUDE":"LATITUDE",
                   "LONGITUDE":"LONGITUDE",
                   "DATE":"Date",
                   "TPCP":"TPCP" }
    # Only map columns that exist
    cols_to_rename = {k:v for k,v in rename_map.items() if k in df.columns}
    df = df.rename(columns=cols_to_rename)
    return df

# Load
wet_df = read_and_select(wet_file)
dry_df = read_and_select(dry_file)

# Combine
merged_df = pd.concat([wet_df, dry_df], ignore_index=True)

# Make sure STATION_NA exists and filter stations ending with 'VM'
if "STATION_NA" in merged_df.columns:
    merged_df = merged_df[merged_df["STATION_NA"].str.strip().str.endswith("VM", na=False)]
else:
    raise KeyError("STATION_NA column not found after reading files. Check headers.")

# === Critical fix: parse Date correctly ===
# Some files may have Date stored as string like '19510501' or as floats/ints in string form.
# Convert to string, strip whitespace, then parse with format %Y%m%d
if "Date" in merged_df.columns:
    merged_df["Date"] = merged_df["Date"].astype(str).str.strip()
    # replace empty strings or non-numeric placeholders with NaN
    merged_df.loc[merged_df["Date"].str.fullmatch(r"\s*"), "Date"] = pd.NA
    # parse format YYYYMMDD
    merged_df["Date"] = pd.to_datetime(merged_df["Date"], format="%Y%m%d", errors="coerce")
else:
    raise KeyError("Date column not found after reading files. Check headers.")

# Optional: report rows where Date could not be parsed (helpful diagnostic)
bad_dates = merged_df[merged_df["Date"].isna()]
if not bad_dates.empty:
    print(f"Warning: {len(bad_dates)} rows have unparseable Date values and will have NaT in Date column.")
    # Uncomment next line to see examples:
    # print(bad_dates.head()[["STATION_NA", "Date"]])

# Convert numeric columns if needed (TPCP, ELEVATION, LAT/LON)
if "TPCP" in merged_df.columns:
    merged_df["TPCP"] = pd.to_numeric(merged_df["TPCP"].astype(str).str.replace(",", "."), errors="coerce")
if "ELEVATION" in merged_df.columns:
    merged_df["ELEVATION"] = pd.to_numeric(merged_df["ELEVATION"].astype(str).str.replace(",", "."), errors="coerce")
if "LATITUDE" in merged_df.columns:
    merged_df["LATITUDE"] = pd.to_numeric(merged_df["LATITUDE"].astype(str).str.replace(",", "."), errors="coerce")
if "LONGITUDE" in merged_df.columns:
    merged_df["LONGITUDE"] = pd.to_numeric(merged_df["LONGITUDE"].astype(str).str.replace(",", "."), errors="coerce")

# Sort by station then date
merged_df = merged_df.sort_values(by=["STATION_NA", "Date"])

# Save outputs
output_excel = os.path.join(base_dir, "merged_precipitation_vietnam.xlsx")
output_csv = os.path.join(base_dir, "merged_precipitation_vietnam.csv")

merged_df.to_excel(output_excel, index=False)
merged_df.to_csv(output_csv, index=False, encoding="utf-8")

print("Merging complete!")
print(f"Saved Excel file: {output_excel}")
print(f"Saved CSV file:   {output_csv}")

