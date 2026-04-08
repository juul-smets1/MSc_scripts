import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────

BASE_DIR = Path(r"C:\Users\31623\Downloads\Juul\WUR\WUR MSc thesis\Data_MSc_thesis")

FILE_GLOBAL = BASE_DIR / "Global_NH_NR_DP_S10.xlsx"           # VIC + mGV simulations
FILE_SAT    = BASE_DIR / "Satellite_NH_NR_DP_S10.xlsx"        # satellite observations

# Soil moisture file (separate)
SOIL_MOISTURE_DIR = Path(r"D:\WUR\ESA_CCI_Soil_Moisture")
FILE_SM = SOIL_MOISTURE_DIR / "soil_moisture_data.xlsx"

# Region mapping: global sheet name → satellite sheet name
REGION_MAPPING = {
    "Pantanal_1990_2019": "Pantanal",
    "SE_CA_1990_2019":    "SE_CA",
    "BKJ_1990_2019":      "BKJ",
    "Yucatán_1990_2019":  "Yucatán",
    "NT_1990_2019":       "NT",
    "Mekong_2000_2019":   "Mekong",               # added Mekong
}

# Beautiful display names for regions
REGION_DISPLAY_NAMES = {
    "Pantanal_1990_2019":      "Pantanal",
    "SE_CA_1990_2019":         "South-Eastern / Central Africa",
    "BKJ_1990_2019":           "Bornean Karst Jungle",
    "Yucatán_1990_2019":       "Yucatán Peninsula",
    "NT_1990_2019":            "Northern Territory",
    "Mekong_2000_2019":        "Mekong",
}

# Regions that have soil moisture data
REGIONS_WITH_SM = {
    "Pantanal_1990_2019",
    "SE_CA_1990_2019",
    "BKJ_1990_2019",
    "Yucatán_1990_2019",
    "NT_1990_2019",
    # Mekong has no SM → intentionally not included
}

# Variable groups: (short name, vic col, mgv col, obs col, unit, full title name)
VARIABLE_GROUPS = [
    ("PET",   "PET_VIC",          "PET_mGV",          "Mean_PET",   "Potential Evapotranspiration (mm/day)",   "Potential Evapotranspiration"),
    ("ET",    "ET_VIC",           "ET_mGV",           "Mean_ET",    "Evapotranspiration (mm/day)",             "Evapotranspiration"),
    ("Tsurf", "Tsurf_VIC",        "Tsurf_mGV",        "Mean_LST",   "Surface Temperature (°C)",                "Surface Temperature"),
    # Soil moisture (added)
    ("SM",    "VIC_volumetric_sm", "mGV_volumetric_sm", "soil_moisture", "Volumetric Soil Moisture (m³/m³)",     "Volumetric Soil Moisture"),
]

OUTPUT_DIR = BASE_DIR / "Scatter_Obs_vs_Sim"
OUTPUT_DIR.mkdir(exist_ok=True)

# ────────────────────────────────────────────────
# PLOTTING FUNCTION
# ────────────────────────────────────────────────

def plot_scatter_obs_vs_sim(df, var_info, region_sheet):
    """
    Creates classic Observed vs Simulated scatter
    - x = Satellite (observed)
    - y = VIC and mGV (both on same plot)
    """
    short_name, col_vic, col_mgv, col_obs, full_ylabel, full_var_name = var_info
    full_region = REGION_DISPLAY_NAMES.get(region_sheet, region_sheet)

    # Prepare clean data
    data = df[[col_obs, col_vic, col_mgv]].dropna()
    if len(data) < 20:
        print(f" → Too few points for {short_name} ({len(data)})")
        return

    obs = data[col_obs].values
    vic = data[col_vic].values
    mgv = data[col_mgv].values

    fig, ax = plt.subplots(figsize=(9, 9), dpi=110)

    # ─── Scatter points ───────────────────────────────
    ax.scatter(obs, vic, s=25, alpha=0.5, color="#1f77b4", label="VIC", edgecolor="none")
    ax.scatter(obs, mgv, s=25, alpha=0.5, color="#ff7f0e", label="mGV", edgecolor="none")

    # ─── 1:1 reference line ───────────────────────────
    min_val = min(obs.min(), vic.min(), mgv.min()) * 0.95
    max_val = max(obs.max(), vic.max(), mgv.max()) * 1.05
    ax.plot([min_val, max_val], [min_val, max_val],
            color='black', lw=1.8, linestyle='--', alpha=0.7, label='1 : 1 line')

    # ─── Style & labels ───────────────────────────────
    ax.set_xlabel(f"Satellite (observed) – {full_ylabel}", fontsize=12)
    ax.set_ylabel(f"Simulated – {full_ylabel}", fontsize=12)

    # Updated title: region – full variable name
    ax.set_title(f"{full_region} – {full_var_name}", fontsize=14, fontweight='bold', pad=16)

    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='upper left', fontsize=10.5, framealpha=0.92)

    # Make plot more square & nice limits
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlim(min_val, max_val)
    ax.set_ylim(min_val, max_val)

    fig.tight_layout()

    # Save (filename still uses short name to keep it compact)
    safe_region = region_sheet.replace(" ", "_").replace("í", "i").replace("/", "_")
    fname = OUTPUT_DIR / f"{safe_region}_{short_name}_scatter_obs_vs_sim.png"
    plt.savefig(fname, bbox_inches='tight', dpi=180)
    plt.close(fig)

    print(f"Saved: {fname.name}")


# ────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────

def main():
    if not FILE_GLOBAL.is_file() or not FILE_SAT.is_file():
        print("One or both main files not found.")
        return

    xl_g = pd.ExcelFile(FILE_GLOBAL)
    xl_s = pd.ExcelFile(FILE_SAT)

    # Soil moisture file is optional
    xl_sm = None
    if FILE_SM.is_file():
        xl_sm = pd.ExcelFile(FILE_SM)
    else:
        print("Soil moisture file not found → SM scatter plots will be skipped")

    print("Creating Observed vs Simulated scatter plots...\n")

    for sheet_g, sheet_s in REGION_MAPPING.items():
        if sheet_g not in xl_g.sheet_names:
            print(f"Missing global sheet: {sheet_g}")
            continue

        if sheet_s not in xl_s.sheet_names:
            print(f"Missing satellite sheet: {sheet_s}")
            continue

        print(f"Processing → {sheet_g}")

        df_sim = pd.read_excel(xl_g, sheet_name=sheet_g, index_col=0, parse_dates=True)
        df_obs = pd.read_excel(xl_s, sheet_name=sheet_s, index_col=0, parse_dates=True)

        df_sim.index = pd.to_datetime(df_sim.index)
        df_obs.index = pd.to_datetime(df_obs.index)

        # Join with suffixes to prevent column overlap error (e.g. Unnamed: 4)
        df = df_sim.join(df_obs, how="inner", lsuffix='_sim', rsuffix='_obs').sort_index()

        if df.empty:
            print(" → No common dates")
            continue

        # ─── Main variables (PET, ET, Tsurf) ────────────────
        for var_info in VARIABLE_GROUPS:
            short_name, c_vic, c_mgv, c_obs, _, _ = var_info

            # Skip SM here
            if short_name == "SM":
                continue

            if not all(c in df_sim.columns for c in [c_vic, c_mgv]) or \
               not c_obs in df_obs.columns:
                print(f" → Missing columns for {short_name}")
                continue

            plot_scatter_obs_vs_sim(df, var_info, sheet_g)

        # ─── Soil moisture (separate file) ────────────────
        if sheet_g in REGIONS_WITH_SM and xl_sm is not None:
            # Soil moisture sheet name = base name (Pantanal, SE_CA, ...)
            sheet_sm = sheet_g.rsplit("_", 2)[0]

            if sheet_sm not in xl_sm.sheet_names:
                print(f" → Soil moisture sheet '{sheet_sm}' not found")
                continue

            df_sm_obs = pd.read_excel(xl_sm, sheet_name=sheet_sm, index_col=0, parse_dates=True)
            df_sm_obs.index = pd.to_datetime(df_sm_obs.index)

            # Join with suffixes here too
            df_sm = df_sim.join(df_sm_obs, how="inner", lsuffix='_sim', rsuffix='_obs').sort_index()

            if df_sm.empty:
                print(" → No common dates for soil moisture")
                continue

            print(f" → Soil moisture — matching points: {len(df_sm):,d}")

            # Soil moisture is the last entry in VARIABLE_GROUPS
            var_info_sm = VARIABLE_GROUPS[-1]
            short_sm, c_vic_sm, c_mgv_sm, c_obs_sm, _, full_sm = var_info_sm

            if not all(c in df_sim.columns for c in [c_vic_sm, c_mgv_sm]) or \
               not c_obs_sm in df_sm_obs.columns:
                print(f" → Missing columns for {short_sm}")
                continue

            plot_scatter_obs_vs_sim(df_sm, var_info_sm, sheet_g)

    print(f"\nFinished!\nAll scatter plots saved in:\n{OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()