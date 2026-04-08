import pandas as pd
import os

# -----------------------------
# File paths
# -----------------------------
directory = r"D:\WUR\In-Situ_Data\MX-PMm_Ameriflux_Yucatan\AMF_MX-PMm_BASE-BADM_2-5"
filename = "AMF_MX-PMm_BASE_HH_2-5.csv"
filepath = os.path.join(directory, filename)
output_file = os.path.join(directory, "daily_averages_TA_LE.csv")

# -----------------------------
# Step 1: Read CSV
# -----------------------------
# Skip the first two metadata lines
df = pd.read_csv(filepath, skiprows=2, dtype=str)
df.replace('-9999', pd.NA, inplace=True)

# -----------------------------
# Step 2: Check required columns
# -----------------------------
required_columns = ['TIMESTAMP_START', 'TA_1_1_1', 'LE']
for col in required_columns:
    if col not in df.columns:
        raise ValueError(f"Column '{col}' not found! Available columns (first 10): {df.columns[:10]}")

# -----------------------------
# Step 3: Convert types
# -----------------------------
df['TA_1_1_1'] = pd.to_numeric(df['TA_1_1_1'], errors='coerce')
df['LE'] = pd.to_numeric(df['LE'], errors='coerce')
df['TIMESTAMP_START'] = pd.to_datetime(df['TIMESTAMP_START'], format='%Y%m%d%H%M', errors='coerce')
df = df.dropna(subset=['TIMESTAMP_START'])

# -----------------------------
# Step 4: Add date column
# -----------------------------
df['date'] = df['TIMESTAMP_START'].dt.date

# -----------------------------
# Step 5: Keep days with at least 75% coverage
# -----------------------------
# Count valid (non-NaN) measurements per day
daily_counts = df.groupby('date')[['TA_1_1_1', 'LE']].apply(lambda x: x.notna().sum())

# Expected measurements per day (30-min data = 48)
expected_rows_per_day = 48

# Minimum required measurements for 75% coverage
min_required = int(expected_rows_per_day * 0.75)

# Keep days where both variables have at least 75% of expected measurements
valid_days = daily_counts[
    (daily_counts['TA_1_1_1'] >= min_required) &
    (daily_counts['LE'] >= min_required)
].index

daily_valid = df[df['date'].isin(valid_days)]

# -----------------------------
# Step 6: Compute daily averages
# -----------------------------
daily_avg = daily_valid.groupby('date', as_index=False).agg({
    'TA_1_1_1': 'mean',
    'LE': 'mean'
})

# -----------------------------
# Step 7: Save CSV
# -----------------------------
daily_avg.to_csv(output_file, index=False)
print(f"Daily averages saved to: {output_file}")