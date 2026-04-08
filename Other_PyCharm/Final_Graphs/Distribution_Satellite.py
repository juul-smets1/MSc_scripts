import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────
BASE_DIR = Path(r"C:\Users\31623\Downloads\Juul\WUR\WUR MSc thesis\Data_MSc_thesis")
FILE_GLOBAL = BASE_DIR / "Global_NH_NR_DP_S10.xlsx"      # VIC + mGV
FILE_SAT = BASE_DIR / "Satellite_NH_NR_DP_S10.xlsx"     # satellite data

# Soil moisture file (separate)
SOIL_MOISTURE_DIR = Path(r"D:\WUR\ESA_CCI_Soil_Moisture")
FILE_SM = SOIL_MOISTURE_DIR / "soil_moisture_data.xlsx"

# Region mapping
REGION_MAPPING = {
    "Pantanal_1990_2019": "Pantanal",
    "SE_CA_1990_2019": "SE_CA",
    "BKJ_1990_2019": "BKJ",
    "Yucatán_1990_2019": "Yucatán",
    "NT_1990_2019": "NT",
    "Mekong_2000_2019": "Mekong",
}

# Display names for titles
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
    "Yucatán_1990_2019", "NT_1990_2019",   # Mekong has no SM
}

# Variable groups
VARIABLE_GROUPS = [
    ("PET", "PET_VIC", "PET_mGV", "Mean_PET", "Potential Evapotranspiration (mm/day)", "Potential Evapotranspiration"),
    ("ET",  "ET_VIC",  "ET_mGV",  "Mean_ET",  "Evapotranspiration (mm/day)", "Evapotranspiration"),
    ("Tsurf","Tsurf_VIC","Tsurf_mGV","Mean_LST","Surface Temperature (°C)", "Surface Temperature"),
    ("SM", "VIC_volumetric_sm", "mGV_volumetric_sm", "soil_moisture", "Volumetric Soil Moisture (m³/m³)", "Volumetric Soil Moisture"),
]

OUTPUT_DIR = BASE_DIR / "Distribution_Plots" / "Final"
OUTPUT_DIR.mkdir(exist_ok=True)


# ────────────────────────────────────────────────
# STATISTIC FUNCTIONS
# ────────────────────────────────────────────────
def compute_stats(data):
    if len(data) == 0 or np.all(np.isnan(data)):
        return np.nan, np.nan
    valid = data[~np.isnan(data)]
    if len(valid) < 2:
        return np.nan, np.nan
    return np.mean(valid), np.std(valid, ddof=0)


# ────────────────────────────────────────────────
# PLOTTING FUNCTION
# ────────────────────────────────────────────────
def plot_distribution(df, var_info, region_sheet):
    short_key, col_vic, col_mgv, col_obs, ylabel, full_var_name = var_info
    full_region_name = REGION_DISPLAY_NAMES.get(region_sheet, region_sheet)

    sub = df[[col_vic, col_mgv, col_obs]].dropna()
    if len(sub) < 10:
        print(f" {short_key} — too few valid points ({len(sub)}) → skipped")
        return

    vic = sub[col_vic].values
    mgv = sub[col_mgv].values
    sat = sub[col_obs].values

    mu_vic, sigma_vic = compute_stats(vic)
    mu_mgv, sigma_mgv = compute_stats(mgv)
    mu_sat, sigma_sat = compute_stats(sat)

    fig, ax = plt.subplots(figsize=(13, 12), dpi=130)

    colors = {
        "VIC-WUR": "#1f77b4",
        "VIC-Julia": "#ff7f0e",
        "Satellite": "#2ca02c",
    }

    # Plot with count instead of density
    sns.histplot(vic, stat="count", kde=True, bins=40,
                 color=colors["VIC-WUR"], alpha=0.35, line_kws={'lw': 2.0},
                 label="VIC-WUR", ax=ax)
    sns.histplot(mgv, stat="count", kde=True, bins=40,
                 color=colors["VIC-Julia"], alpha=0.35, line_kws={'lw': 2.0},
                 label="VIC-Julia", ax=ax)
    sns.histplot(sat, stat="count", kde=True, bins=40,
                 color=colors["Satellite"], alpha=0.35, line_kws={'lw': 2.0, 'ls': '--'},
                 label="Satellite", ax=ax)

    ax.set_title(f"{full_region_name} — {full_var_name} Distribution", fontsize=25, pad=18)
    ax.set_xlabel(ylabel, fontsize=20)
    ax.set_ylabel("Number of samples", fontsize=20)          # ← Changed
    ax.tick_params(axis='both', labelsize=15)
    ax.grid(True, ls=":", alpha=0.6)

    # Legend (stacked vertically on left)
    ax.legend(loc="upper center", bbox_to_anchor=(0.1, -0.1),
              ncol=1, fontsize=17, framealpha=0.92)

    # Stats box (right side)
    textstr = (f"VIC-WUR    μ = {mu_vic:8.4f}   σ = {sigma_vic:8.4f}\n"
               f"VIC-Julia  μ = {mu_mgv:8.4f}   σ = {sigma_mgv:8.4f}\n"
               f"Satellite  μ = {mu_sat:8.4f}   σ = {sigma_sat:8.4f}")

    props = dict(boxstyle="round,pad=0.65", facecolor="#f8f9fa", alpha=0.94, edgecolor="#444")
    ax.text(0.30, -0.18, textstr, transform=ax.transAxes,
            fontsize=15, verticalalignment="top", horizontalalignment="left",
            family="monospace", bbox=props)

    # Bottom margin
    fig.tight_layout(rect=[0, 0.32, 1, 1])

    # Save
    safe_region = REGION_SAFE_NAMES.get(region_sheet, region_sheet.replace(" ", "_").replace("í", "i"))
    fname = OUTPUT_DIR / f"{safe_region}_{short_key}_distribution.png"
    plt.savefig(fname, bbox_inches="tight", dpi=200)
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

    print("Generating distribution plots...\n")

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

        df = df_sim.join(df_obs, how="inner", lsuffix='_sim', rsuffix='_obs').sort_index()

        if df.empty:
            print(" No overlapping dates → skipped")
            continue

        # ─── Main variables (PET, ET, Tsurf) ────────────────
        for var_info in VARIABLE_GROUPS:
            group, col_vic, col_mgv, col_obs, _, _ = var_info
            if group == "SM":
                continue

            if not all(c in df_sim.columns for c in [col_vic, col_mgv]) or col_obs not in df_obs.columns:
                print(f" Skipping {group} — missing column(s)")
                continue

            plot_distribution(df, var_info, sheet_global)

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
            plot_distribution(df_sm, var_info_sm, sheet_global)

    print(f"\nAll done. Distribution plots saved in:\n {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()