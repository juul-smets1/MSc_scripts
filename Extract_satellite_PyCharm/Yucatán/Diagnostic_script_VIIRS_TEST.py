import os
import re
from datetime import datetime, timedelta

# Root directories
lst_dir = r"D:\WUR\NASA_ESDS\Yucatán\VIIRS_NPP_Yucatán_LSurfT_Data"
et_dir = r"D:\WUR\NASA_ESDS\Yucatán\VIIRS_NPP_YucatánETData"

# Expected granules for Yucatán
granules = ["h09v06", "h09v07"]

# Function to extract date from filename
def extract_date(filename):
    match = re.search(r"A(\d{4})(\d{3})", filename)
    if match:
        year = int(match.group(1))
        doy = int(match.group(2))
        return (datetime(year, 1, 1) + timedelta(days=doy - 1)).date()
    return None

# Collect all files in directories
lst_files = os.listdir(lst_dir)
et_files = os.listdir(et_dir)

# Diagnostic dictionary
diagnostics = {}

# Check LST files
for f in lst_files:
    date = extract_date(f)
    tile_found = any(g in f for g in granules)
    diagnostics.setdefault(date, {"LST": {}, "ET": {}, "PET": {}})
    diagnostics[date]["LST"][f] = os.path.exists(os.path.join(lst_dir, f)) and tile_found

# Check ET/PET files
for f in et_files:
    date = extract_date(f)
    tile_found = any(g in f for g in granules)
    diagnostics.setdefault(date, {"LST": {}, "ET": {}, "PET": {}})
    diagnostics[date]["ET"][f] = os.path.exists(os.path.join(et_dir, f)) and tile_found
    diagnostics[date]["PET"][f] = os.path.exists(os.path.join(et_dir, f)) and tile_found

# Print diagnostics
for date, info in sorted(diagnostics.items()):
    print(f"Date: {date}")
    for product in ["LST", "ET", "PET"]:
        files = info[product]
        if not files:
            print(f"  {product}: NO FILES FOUND")
        else:
            for fname, exists in files.items():
                status = "OK" if exists else "MISSING or wrong tile"
                print(f"  {product}: {fname} -> {status}")
    print("-" * 60)