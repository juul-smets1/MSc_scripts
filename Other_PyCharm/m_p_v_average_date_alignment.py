# Merged precipitation Vietnam date alignment with averaging over existing dates (no data loss)
# + Missing date/month check (included in Excel output, no timestamps)

import pandas as pd
import os

# --- File path ---
file_path = r"C:\Users\31623\Downloads\Juul\WUR\WUR MSc thesis\Data_MSc_thesis\Unfiltered\merged_precipitation_vietnam.xlsx"

# --- Read Excel file ---
df = pd.read_excel(file_path)

# --- Define stations of interest ---
stations = ['CA MAU VM', 'PHAN THIET VM', 'PHU QUOC VM', 'TAN SON HOA VM']

# --- Filter dataframe for these stations ---
df_filtered = df[df['STATION_NA'].isin(stations)].copy()

# --- Ensure Date column is in datetime format ---
df_filtered['Date'] = pd.to_datetime(df_filtered['Date'])

# --- Pivot table so each station has its own column of TPCP values ---
pivot_df = df_filtered.pivot_table(
    index='Date',
    columns='STATION_NA',
    values='TPCP'
)

# --- Calculate average across *available* stations for each date (ignore missing) ---
pivot_df['TPCP_avg'] = pivot_df[stations].mean(axis=1, skipna=True)

# --- Reset index and format Date to YYYY-MM-DD (remove time) ---
pivot_df = pivot_df.reset_index()
pivot_df['Date'] = pivot_df['Date'].dt.strftime('%Y-%m-%d')

# --- Create final dataframe with Date and average TPCP ---
result_df = pivot_df[['Date', 'TPCP_avg']].copy()

# ==============================================================
# Check for missing dates between first and last date
# ==============================================================

# Convert Date column back to datetime for date range comparison
dates_dt = pd.to_datetime(result_df['Date'])

# Generate complete monthly date range between first and last date
full_range = pd.date_range(start=dates_dt.min(), end=dates_dt.max(), freq='MS')

# Find missing months (dates not in result_df)
existing_dates = pd.to_datetime(result_df['Date'].unique())
missing_dates = [d for d in full_range if d not in existing_dates]

# Print summary of missing dates
if missing_dates:
    print("\n⚠️ Missing monthly dates between first and last record:")
    for d in missing_dates:
        print("  -", d.strftime('%Y-%m-%d'))
else:
    print("\n✅ No missing months — all dates are continuous!")

# --- Create DataFrame for missing dates to include in Excel ---
if missing_dates:
    missing_df = pd.DataFrame({'Missing_Date': [d.strftime('%Y-%m-%d') for d in missing_dates]})
else:
    missing_df = pd.DataFrame({'Missing_Date': ['None']})

# --- Ensure all date columns have clean string format ---
result_df['Date'] = result_df['Date'].astype(str)
missing_df['Missing_Date'] = missing_df['Missing_Date'].astype(str)

# --- Save both datasets to Excel ---
output_path = os.path.join(os.path.dirname(file_path), "average_TPCP_all_dates_with_missing.xlsx")

with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
    result_df.to_excel(writer, index=False, sheet_name='Averaged_TPCP')
    missing_df.to_excel(writer, index=False, sheet_name='Missing_Dates')

print("\n✅ Done! File saved to:", output_path)
print("\nExample of saved data:")
print(result_df.head())

