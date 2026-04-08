import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────
BASE_DIR = Path(r"C:\Users\31623\Downloads\Juul\WUR\WUR MSc thesis\Data_MSc_thesis")
FILE_GLOBAL = BASE_DIR / "Global_NH_NR_DP_S10.xlsx"  # VIC + mGV
FILE_SAT = BASE_DIR / "Satellite_NH_NR_DP_S10.xlsx"  # satellite data

# Soil moisture file (separate)
SOIL_MOISTURE_DIR = Path(r"D:\WUR\ESA_CCI_Soil_Moisture")
FILE_SM = SOIL_MOISTURE_DIR / "soil_moisture_data.xlsx"

# Region mapping: global sheet name → satellite sheet name
REGION_MAPPING = {
    "Pantanal_1990_2019": "Pantanal",
    "SE_CA_1990_2019": "SE_CA",
    "BKJ_1990_2019": "BKJ",
    "Yucatán_1990_2019": "Yucatán",
    "NT_1990_2019": "NT",
    "Mekong_2000_2019": "Mekong",
}

# Display names for plot titles
REGION_DISPLAY_NAMES = {
    "Pantanal_1990_2019": "Pantanal",
    "SE_CA_1990_2019": "South-Eastern/Central Africa",
    "BKJ_1990_2019": "Bornean Karst Jungle",
    "Yucatán_1990_2019": "Yucatán Peninsula",
    "NT_1990_2019": "Northern Territory",
    "Mekong_2000_2019": "Mekong",
}

# Safe names for filenames
REGION_SAFE_NAMES = {
    "Pantanal_1990_2019": "Pantanal",
    "SE_CA_1990_2019": "SE_CA",
    "BKJ_1990_2019": "BKJ",
    "Yucatán_1990_2019": "Yucatan_Peninsula",
    "NT_1990_2019": "Northern_Territory",
    "Mekong_2000_2019": "Mekong",
}

# Regions that have soil moisture data
REGIONS_WITH_SM = {
    "Pantanal_1990_2019", "SE_CA_1990_2019", "BKJ_1990_2019",
    "Yucatán_1990_2019", "NT_1990_2019",  # Mekong has no SM
}

# Variable groups: (group, vic_col, mgv_col, obs_col, ylabel, full_title_name)
VARIABLE_GROUPS = [
    ("PET", "PET_VIC", "PET_mGV", "Mean_PET",
     "Potential\nEvapotranspiration\n(mm/day)",  # <-- Fixed: split over multiple lines
     "Potential Evapotranspiration"),

    ("ET", "ET_VIC", "ET_mGV", "Mean_ET",
     "Evapotranspiration (mm/day)",
     "Evapotranspiration"),

    ("Tsurf", "Tsurf_VIC", "Tsurf_mGV", "Mean_LST",
     "Surface Temperature (°C)",
     "Surface Temperature"),

    # Soil moisture
    ("SM", "VIC_volumetric_sm", "mGV_volumetric_sm", "soil_moisture",
     "Volumetric Soil Moisture (m³/m³)",
     "Volumetric Soil Moisture"),
]

OUTPUT_DIR = BASE_DIR / "Performance_Plots" / "Final"
OUTPUT_DIR.mkdir(exist_ok=True)


# ────────────────────────────────────────────────
# PLOTTING FUNCTION
# ────────────────────────────────────────────────
def plot_triple_timeseries(df, var_info, region_sheet):
    group, col_vic, col_mgv, col_obs, ylabel, full_var_name = var_info
    full_region_name = REGION_DISPLAY_NAMES.get(region_sheet, region_sheet)

    fig, ax = plt.subplots(figsize=(12, 6), dpi=110)

    # Plot lines with updated legend labels (VIC-WUR and VIC-Julia)
    if group == "SM":
        ax.plot(df.index, df[col_vic], label="VIC-WUR", lw=1.1, color="#1f77b4")
        ax.plot(df.index, df[col_mgv], label="VIC-Julia", lw=1.1, color="#ff7f0e")
        ax.plot(df.index, df[col_obs], label="Satellite", lw=1.4, color="#2ca02c", alpha=0.9, linestyle="--")
    else:
        ax.plot(df.index, df[col_vic], label=f"VIC-WUR", lw=1.1, color="#1f77b4")
        ax.plot(df.index, df[col_mgv], label=f"VIC-Julia", lw=1.1, color="#ff7f0e")
        ax.plot(df.index, df[col_obs], label=f"Satellite", lw=1.4, color="#2ca02c", alpha=0.9, linestyle="--")

    ax.set_title(f"{full_region_name} — {full_var_name}", fontsize=25, pad=12)
    ax.set_ylabel(ylabel, fontsize=20)
    ax.set_xlabel("Date", fontsize=20)

    # Tick label font size
    ax.tick_params(axis='both', labelsize=15)

    ax.grid(True, ls=":", alpha=0.7)

    # Legend placed below the x-axis
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3, fontsize=17, framealpha=0.92)

    fig.tight_layout()

    # Save
    safe_region = REGION_SAFE_NAMES.get(region_sheet, region_sheet.replace(" ", "_").replace("í", "i"))
    fname = OUTPUT_DIR / f"{safe_region}_{group}_timeseries.png"
    plt.savefig(fname, bbox_inches="tight", dpi=180)
    plt.close(fig)
    print(f"Saved: {fname.name}")


# ────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────
def main():
    if not FILE_GLOBAL.is_file() or not FILE_SAT.is_file():
        print("One or both main Excel files not found.")
        return

    xl_global = pd.ExcelFile(FILE_GLOBAL)
    xl_sat = pd.ExcelFile(FILE_SAT)

    # Soil moisture file is optional
    xl_sm = None
    if FILE_SM.is_file():
        xl_sm = pd.ExcelFile(FILE_SM)
    else:
        print(f"Soil moisture file not found → SM plots will be skipped")

    print("Generating performance plots...\n")

    for sheet_global, sheet_sat in REGION_MAPPING.items():
        if sheet_global not in xl_global.sheet_names:
            print(f"Skipping {sheet_global} — global sheet missing")
            continue
        if sheet_sat not in xl_sat.sheet_names:
            print(f"Skipping {sheet_global} — satellite sheet '{sheet_sat}' missing")
            continue

        print(f"Processing region: {sheet_global}")

        df_sim = pd.read_excel(xl_global, sheet_name=sheet_global, index_col=0, parse_dates=True)
        df_obs = pd.read_excel(xl_sat, sheet_name=sheet_sat, index_col=0, parse_dates=True)

        df_sim.index = pd.to_datetime(df_sim.index)
        df_obs.index = pd.to_datetime(df_obs.index)

        # Join with suffixes to prevent column overlap
        df = df_sim.join(df_obs, how="inner", lsuffix='_sim', rsuffix='_obs').sort_index()

        if df.empty:
            print(" No overlapping dates → skipped")
            continue

        # ─── Main variables (PET, ET, Tsurf) ────────────────
        for var_info in VARIABLE_GROUPS:
            group, col_vic, col_mgv, col_obs, _, _ = var_info
            if group == "SM":
                continue  # SM handled separately

            # Check columns
            if not all(c in df_sim.columns for c in [col_vic, col_mgv]) or \
                    not all(c in df_obs.columns for c in [col_obs]):
                print(f" Skipping {group} — missing column(s)")
                continue

            sub = df[[col_vic, col_mgv, col_obs]].dropna()
            if len(sub) < 10:
                print(f" {group} — too few valid points ({len(sub)})")
                continue

            plot_triple_timeseries(sub, var_info, sheet_global)

        # ─── Soil moisture (separate file) ────────────────
        if sheet_global in REGIONS_WITH_SM and xl_sm is not None:
            sheet_sm = sheet_global.rsplit("_", 2)[0]
            if sheet_sm not in xl_sm.sheet_names:
                print(f" Soil moisture sheet '{sheet_sm}' not found → skipped SM")
                continue

            df_sm_obs = pd.read_excel(xl_sm, sheet_name=sheet_sm, index_col=0, parse_dates=True)
            df_sm_obs.index = pd.to_datetime(df_sm_obs.index)

            df_sm = df_sim.join(df_sm_obs, how="inner", lsuffix='_sim', rsuffix='_obs').sort_index()

            if df_sm.empty:
                print(" No overlapping dates for soil moisture → skipped")
                continue

            print(f" Soil moisture — matching points: {len(df_sm):,d}")

            var_info_sm = VARIABLE_GROUPS[-1]
            col_vic_sm, col_mgv_sm, col_obs_sm = var_info_sm[1], var_info_sm[2], var_info_sm[3]

            if not all(c in df_sim.columns for c in [col_vic_sm, col_mgv_sm]) or \
                    col_obs_sm not in df_sm_obs.columns:
                print(f" Skipping SM — missing column(s)")
                continue

            sub_sm = df_sm[[col_vic_sm, col_mgv_sm, col_obs_sm]].dropna()
            if len(sub_sm) < 10:
                print(f" SM — too few valid points ({len(sub_sm)})")
                continue

            plot_triple_timeseries(sub_sm, var_info_sm, sheet_global)

    print(f"\nAll done. Plots saved in:\n {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()