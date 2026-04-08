import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# ────────────────────────────────────────────────
#  CONFIGURATION
# ────────────────────────────────────────────────

BASE_DIR = Path(r"C:\Users\31623\Downloads\Juul\WUR\WUR MSc thesis\Data_MSc_thesis")

FILE_GLOBAL = BASE_DIR / "Global_NH_NR_DP_S10.xlsx"     # VIC + mGV
FILE_SAT    = BASE_DIR / "Satellite_NH_NR_DP_S10.xlsx"  # observations

# Real sheet names in Excel files (same as used in the working time-series script)
REGION_MAPPING = {
    "Pantanal_1990_2019": "Pantanal",
    "SE_CA_1990_2019":    "SE_CA",
    "BKJ_1990_2019":      "BKJ",
    "Yucatán_1990_2019":  "Yucatán",
    "NT_1990_2019":       "NT"
}

# Display names for titles
REGION_DISPLAY_NAMES = {
    "Pantanal_1990_2019":      "Pantanal",
    "SE_CA_1990_2019":         "South-Eastern/Central Africa",
    "BKJ_1990_2019":           "Bornean Karst Jungle",
    "Yucatán_1990_2019":       "Yucatán Peninsula",
    "NT_1990_2019":            "Northern Territory"
}

# For filename safety
REGION_SAFE_NAMES = {
    "Pantanal_1990_2019":      "Pantanal",
    "SE_CA_1990_2019":         "SE_CA",
    "BKJ_1990_2019":           "BKJ",
    "Yucatán_1990_2019":       "Yucatan_Peninsula",
    "NT_1990_2019":            "Northern_Territory"
}

# Variable groups: (short key, vic col, mgv col, obs col, unit, full title name)
VARIABLE_GROUPS = [
    ("PET",   "PET_VIC",   "PET_mGV",   "Mean_PET",  "Potential Evapotranspiration (mm/day)", "Potential Evapotranspiration"),
    ("ET",    "ET_VIC",    "ET_mGV",    "Mean_ET",   "Evapotranspiration (mm/day)",          "Evapotranspiration"),
    ("Tsurf", "Tsurf_VIC", "Tsurf_mGV", "Mean_LST",  "Surface Temperature (°C)",            "Surface Temperature"),
]

OUTPUT_DIR = BASE_DIR / "Distribution_Plots"
OUTPUT_DIR.mkdir(exist_ok=True)

# ────────────────────────────────────────────────
#  STATISTIC FUNCTIONS
# ────────────────────────────────────────────────

def compute_stats(data):
    """Return mean and std, handling empty/invalid cases"""
    if len(data) == 0 or np.all(np.isnan(data)):
        return np.nan, np.nan
    valid = data[~np.isnan(data)]
    if len(valid) < 2:
        return np.nan, np.nan
    return np.mean(valid), np.std(valid, ddof=0)  # population std

# ────────────────────────────────────────────────
#  PLOTTING FUNCTION – Distribution (histogram + KDE)
# ────────────────────────────────────────────────

def plot_distribution(df, var_info, region_sheet):
    short_key, col_vic, col_mgv, col_obs, ylabel, full_var_name = var_info
    full_region_name = REGION_DISPLAY_NAMES.get(region_sheet, region_sheet)

    sub = df[[col_vic, col_mgv, col_obs]].dropna()
    if len(sub) < 10:
        print(f"  {short_key} — too few valid points ({len(sub)}) → skipped")
        return

    vic = sub[col_vic].values
    mgv = sub[col_mgv].values
    sat = sub[col_obs].values

    mu_vic, sigma_vic = compute_stats(vic)
    mu_mgv, sigma_mgv = compute_stats(mgv)
    mu_sat, sigma_sat = compute_stats(sat)

    fig, ax = plt.subplots(figsize=(10, 6), dpi=110)

    # Histogram + KDE for each dataset
    sns.histplot(vic, stat="density", kde=True, bins=40, color="#1f77b4", alpha=0.25,
                 line_kws={'lw': 1.8}, label="VIC-WUR", ax=ax)
    sns.histplot(mgv, stat="density", kde=True, bins=40, color="#ff7f0e", alpha=0.25,
                 line_kws={'lw': 1.8}, label="mGV", ax=ax)
    sns.histplot(sat, stat="density", kde=True, bins=40, color="#2ca02c", alpha=0.35,
                 line_kws={'lw': 2.2, 'ls': '--'}, label="Satellite", ax=ax)

    ax.set_title(f"{full_region_name} — {full_var_name} Distribution", fontsize=14, pad=12)
    ax.set_xlabel(ylabel, fontsize=11)
    ax.set_ylabel("Density", fontsize=11)

    ax.grid(True, ls=":", alpha=0.6)
    ax.legend(loc="upper right", fontsize=10.5, framealpha=0.92)

    # Stats text box
    textstr = (
        f"VIC-WUR     μ = {mu_vic:8.4f}    σ = {sigma_vic:8.4f}\n"
        f"mGV         μ = {mu_mgv:8.4f}    σ = {sigma_mgv:8.4f}\n"
        f"Satellite   μ = {mu_sat:8.4f}    σ = {sigma_sat:8.4f}"
    )

    props = dict(boxstyle="round,pad=0.55", facecolor="#f8f9fa", alpha=0.94, edgecolor="#444")
    ax.text(0.03, 0.97, textstr, transform=ax.transAxes, fontsize=10.4,
            verticalalignment="top", horizontalalignment="left", family="monospace", bbox=props)

    fig.tight_layout()

    # Save
    safe_region = REGION_SAFE_NAMES.get(region_sheet, region_sheet.replace(" ", "_").replace("í", "i"))
    fname = OUTPUT_DIR / f"{safe_region}_{short_key}_distribution.png"
    plt.savefig(fname, bbox_inches="tight", dpi=180)
    plt.close(fig)

    print(f"Saved: {fname.name}")

# ────────────────────────────────────────────────
#  MAIN – corrected loop
# ────────────────────────────────────────────────

def main():
    if not FILE_GLOBAL.is_file() or not FILE_SAT.is_file():
        print("One or both Excel files not found.")
        return

    xl_global = pd.ExcelFile(FILE_GLOBAL)
    xl_sat    = pd.ExcelFile(FILE_SAT)

    print("Generating distribution plots...\n")

    # Use the same mapping as the working time-series script
    for sheet_global, sheet_sat in REGION_MAPPING.items():
        if sheet_global not in xl_global.sheet_names:
            print(f"Skipping {sheet_global} — not found in global file")
            continue
        if sheet_sat not in xl_sat.sheet_names:
            print(f"Skipping {sheet_global} — satellite sheet '{sheet_sat}' missing")
            continue

        print(f"Processing region: {sheet_global}")

        df_sim = pd.read_excel(xl_global, sheet_name=sheet_global, index_col=0, parse_dates=True)
        df_obs = pd.read_excel(xl_sat,    sheet_name=sheet_sat,    index_col=0, parse_dates=True)

        df_sim.index = pd.to_datetime(df_sim.index)
        df_obs.index = pd.to_datetime(df_obs.index)

        df = df_sim.join(df_obs, how="inner").sort_index()

        if df.empty:
            print("  No overlapping dates → skipped")
            continue

        for var_info in VARIABLE_GROUPS:
            _, col_vic, col_mgv, col_obs, _, _ = var_info

            if not all(c in df.columns for c in [col_vic, col_mgv, col_obs]):
                print(f"  Skipping {var_info[0]} — missing column(s)")
                continue

            plot_distribution(df, var_info, sheet_global)

    print(f"\nAll done. Distribution plots saved in:\n  {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()