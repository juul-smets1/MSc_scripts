import pandas as pd
import os

# -----------------------------
# Paths
# -----------------------------
directory = r"D:\WUR\In-Situ_Data\NT_AUS"
input_file = os.path.join(directory, "CosmOz_Daly_level4.csv")
output_file = os.path.join(directory, "CosmOz_Daly_Daily_SoilMoisture.csv")

# -----------------------------
# Step 1: Read CSV with correct separator
# -----------------------------
df = pd.read_csv(input_file, sep=';', dtype=str)

# Strip column names to remove extra spaces
df.columns = df.columns.str.strip()

# Check columns
print("Columns found in CSV:", df.columns.tolist())

# -----------------------------
# Step 2: Identify time and soil columns
# -----------------------------
time_col = None
soil_col = None

for col in df.columns:
    if "UTC" in col.upper() and "TIMESTAMP" in col.upper():
        time_col = col
    if "SOIL" in col.upper() and "MOISTURE" in col.upper():
        soil_col = col

if time_col is None or soil_col is None:
    raise ValueError("Could not find the timestamp or soil moisture columns in the CSV.")

# -----------------------------
# Step 3: Convert timestamp to datetime
# -----------------------------
df['timestamp'] = pd.to_datetime(df[time_col], dayfirst=True, errors='coerce')

# Drop rows with invalid timestamps
df = df.dropna(subset=['timestamp'])

# -----------------------------
# Step 4: Add date column
# -----------------------------
df['date'] = df['timestamp'].dt.date

# -----------------------------
# Step 5: Convert soil moisture to numeric
# -----------------------------
df['soil_moisture'] = pd.to_numeric(df[soil_col], errors='coerce')

# -----------------------------
# Step 6: Keep only fully complete days
# -----------------------------
expected_rows_per_day = 24  # hourly data assumption

daily_counts = df.groupby('date')['soil_moisture'].count()
complete_days = daily_counts[daily_counts == expected_rows_per_day].index
df_complete = df[df['date'].isin(complete_days)]

# -----------------------------
# Step 7: Compute daily averages
# -----------------------------
daily_avg = df_complete.groupby('date', as_index=False)['soil_moisture'].mean()

# -----------------------------
# Step 8: Save CSV
# -----------------------------
daily_avg.to_csv(output_file, index=False)

print("✅ Daily averages computed and saved")
print(f"📁 Output CSV: {output_file}")