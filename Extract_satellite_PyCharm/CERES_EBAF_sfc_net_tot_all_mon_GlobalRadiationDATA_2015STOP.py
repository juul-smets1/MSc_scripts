import xarray as xr
import pandas as pd
import os

# === INPUTS ===
file_path = r"D:\WUR\NASA_ESDS\CERES_EBAF_Edition4.1_GlobalDATA\CERES_EBAF_Edition4.1_200003-202203.nc"
var_name = "sfc_net_tot_all_mon"
vic_boundary = {
    "lat_min": 8.54167,
    "lat_max": 11.4583,
    "lon_min": 104.042,
    "lon_max": 106.958
}

# === OPEN THE DATASET ===
ds = xr.open_dataset(file_path)
print("✅ Dataset loaded successfully!")
print("Available coordinates:", list(ds.coords))

# === IDENTIFY LAT/LON COORDINATE NAMES ===
if "lat" in ds.coords and "lon" in ds.coords:
    lat_name = "lat"
    lon_name = "lon"
elif "degrees_north" in ds.coords and "degrees_east" in ds.coords:
    lat_name = "degrees_north"
    lon_name = "degrees_east"
else:
    raise KeyError("❌ Could not find latitude/longitude coordinate names in dataset.")

# === SELECT VARIABLE ===
data = ds[var_name]

# === HANDLE LATITUDE ORIENTATION ===
latitudes = ds[lat_name].values
if latitudes[0] > latitudes[-1]:
    # Dataset has descending latitude, reverse the slice order
    lat_slice = slice(vic_boundary["lat_max"], vic_boundary["lat_min"])
else:
    lat_slice = slice(vic_boundary["lat_min"], vic_boundary["lat_max"])

# === SUBSET SPATIALLY ===
data_subset = data.sel(
    {lat_name: lat_slice,
     lon_name: slice(vic_boundary["lon_min"], vic_boundary["lon_max"])}
)

# === SUBSET TEMPORALLY ===
data_subset = data_subset.sel(time=slice("2000-03-15", "2014-12-15"))

# === COMPUTE SPATIAL MEAN ===
data_mean = data_subset.mean(dim=[lat_name, lon_name], skipna=True)

# === CONVERT TO DATAFRAME (TIME SERIES) ===
df = data_mean.to_dataframe().reset_index()[["time", var_name]]

# Combine year and month
df["YearMonth"] = df["time"].dt.strftime("%Y-%m")
df = df[["YearMonth", var_name]]

# === SAVE MAIN OUTPUT TO EXCEL ===
output_dir = os.path.dirname(file_path)
output_path = os.path.join(output_dir, "MekongDelta_GlobalRadiation_2000_2014.xlsx")
df.to_excel(output_path, index=False)

print(f"✅ Main export complete! File saved at:\n{output_path}")

# === SAVE GRID CELL LOCATIONS ===
# Extract the unique lat/lon pairs used in averaging
lats = data_subset[lat_name].values
lons = data_subset[lon_name].values

grid_df = pd.DataFrame([(lat, lon) for lat in lats for lon in lons],
                       columns=["Latitude", "Longitude"])

grid_output_path = os.path.join(output_dir, "MekongDelta_GlobalRadiation_2000_2014_GridCells.xlsx")
grid_df.to_excel(grid_output_path, index=False)

print(f"✅ Grid cell info saved at:\n{grid_output_path}")
print(f"Grid cells used: {len(lats)} latitudes × {len(lons)} longitudes = {len(lats)*len(lons)} total cells")
