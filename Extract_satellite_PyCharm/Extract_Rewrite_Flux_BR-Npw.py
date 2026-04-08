import pandas as pd
import os

# -----------------------------
# File paths
# -----------------------------
directory = r"D:\WUR\In-Situ_Data\BR-NPW_Ameriflux_Pantanal\AMF_BR-Npw_FLUXNET_FULLSET_2013-2017_5-7"
filename = "AMF_BR-Npw_FLUXNET_FULLSET_HH_2013-2017_5-7_extract.csv"
filepath = os.path.join(directory, filename)
output_file = os.path.join(directory, "daily_averages_TA_LE.csv")

# -----------------------------
# Step 1: Read CSV
# -----------------------------
df = pd.read_csv(filepath, dtype=str)

# -----------------------------
# Step 2: Check for required columns
# -----------------------------
required_columns = ['TIMESTAMP_START', 'TA_F_MDS', 'LE_F_MDS']
for col in required_columns:
    if col not in df.columns:
        raise ValueError(f"Column '{col}' not found! Available columns (first 10): {df.columns[:10]}")

# -----------------------------
# Step 3: Convert types
# -----------------------------
df.replace('-9999', pd.NA, inplace=True)
df['TA_F_MDS'] = pd.to_numeric(df['TA_F_MDS'], errors='coerce')
df['LE_F_MDS'] = pd.to_numeric(df['LE_F_MDS'], errors='coerce')
df['TIMESTAMP_START'] = pd.to_datetime(df['TIMESTAMP_START'], format='%Y%m%d%H%M', errors='coerce')
df = df.dropna(subset=['TIMESTAMP_START'])

# -----------------------------
# Step 4: Add date column
# -----------------------------
df['date'] = df['TIMESTAMP_START'].dt.date

# -----------------------------
# Step 5: Keep only complete days (no missing data for the day)
# -----------------------------
daily_complete = df.groupby('date').filter(lambda x: x[['TA_F_MDS', 'LE_F_MDS']].notna().all().all())

# -----------------------------
# Step 6: Compute daily averages
# -----------------------------
daily_avg = daily_complete.groupby('date', as_index=False).agg({
    'TA_F_MDS': 'mean',
    'LE_F_MDS': 'mean'
})

# -----------------------------
# Step 7: Save to CSV
# -----------------------------
daily_avg.to_csv(output_file, index=False)
print(f"Daily averages saved to: {output_file}")

