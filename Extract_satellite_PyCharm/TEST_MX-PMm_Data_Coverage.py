import pandas as pd
import os

# -----------------------------
# File paths
# -----------------------------
directory = r"D:\WUR\In-Situ_Data\MX-PMm_Ameriflux_Yucatan\AMF_MX-PMm_BASE-BADM_2-5"
filename = "AMF_MX-PMm_BASE_HH_2-5.csv"
filepath = os.path.join(directory, filename)

# -----------------------------
# Step 1: Read CSV
# -----------------------------
df = pd.read_csv(filepath, skiprows=2, dtype=str)
df.replace('-9999', pd.NA, inplace=True)

# -----------------------------
# Step 2: Convert types
# -----------------------------
df['TA_1_1_1'] = pd.to_numeric(df['TA_1_1_1'], errors='coerce')
df['LE'] = pd.to_numeric(df['LE'], errors='coerce')
df['TIMESTAMP_START'] = pd.to_datetime(df['TIMESTAMP_START'], format='%Y%m%d%H%M', errors='coerce')
df = df.dropna(subset=['TIMESTAMP_START'])

# -----------------------------
# Step 3: Add date column
# -----------------------------
df['date'] = df['TIMESTAMP_START'].dt.date

# -----------------------------
# Step 4: Count valid measurements per day
# -----------------------------
daily_counts = df.groupby('date')[['TA_1_1_1', 'LE']].apply(lambda x: x.notna().sum())

# -----------------------------
# Step 5: Show diagnostic info
# -----------------------------
expected_rows_per_day = 48  # for 30-min data

print("Daily counts of valid measurements:")
print(daily_counts)

# Determine which days are complete for each variable
complete_TA_days = daily_counts[daily_counts['TA_1_1_1'] == expected_rows_per_day].index
complete_LE_days = daily_counts[daily_counts['LE'] == expected_rows_per_day].index

print("\nDays with complete TA_1_1_1 data (all 48 measurements):")
print(list(complete_TA_days))

print("\nDays with complete LE data (all 48 measurements):")
print(list(complete_LE_days))

# Optional: Days that are complete for BOTH
complete_both_days = daily_counts[
    (daily_counts['TA_1_1_1'] == expected_rows_per_day) &
    (daily_counts['LE'] == expected_rows_per_day)
].index

print("\nDays with complete TA_1_1_1 AND LE data:")
print(list(complete_both_days))
