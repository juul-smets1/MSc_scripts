import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────
BASE_DIR = Path(r"C:\Users\31623\Downloads\Juul\WUR\WUR MSc thesis\Data_MSc_thesis")

# In-situ observations (reference)
INSITU_DIR = Path(r"D:\WUR\In-Situ_Data")
FILE_INSITU = INSITU_DIR / "In-Situ_Data.xlsx"

# Model outputs
MODEL_DIR = Path(r"D:\WUR\Thesis_model_runs\InSitu_NH_NR_DP_S10")
FILE_MODELS = MODEL_DIR / "InSitu_NH_NR_DP_S10.xlsx"

# Satellite SM
SAT_SM_DIR = Path(r"D:\WUR\In-Situ_Data")
FILE_SAT_SM = SAT_SM_DIR / "Satellite_In-Situ_Data.xlsx"

# Station display names
STATION_DISPLAY_NAMES = {
    "BR-Npw": "BR-Npw",
    "MX-PMm": "MX-PMm",
    "NT_FoggDam": "NT Fogg Dam",
    "NT_DryRiver": "NT Dry River",
    "NT_CosmOz_Daly": "NT CosmOz Daly",
}

# Safe names for filenames
STATION_SAFE_NAMES = {
    "BR-Npw": "BR_Npw",
    "MX-PMm": "MX_PMm",
    "NT_FoggDam": "NT_FoggDam",
    "NT_DryRiver": "NT_DryRiver",
    "NT_CosmOz_Daly": "NT_CosmOz_Daly",
}

# Which stations have which variables
INSITU_VARS = {
    "BR-Npw": [("ET", "ET_BR-Npw")],
    "MX-PMm": [("ET", "ET_MX-PMm")],
    "NT_FoggDam": [("ET", "ET_FoggDam"), ("SM", "SM_FoggDam")],
    "NT_DryRiver": [("ET", "ET_DryRiver"), ("SM", "SM_DryRiver")],
    "NT_CosmOz_Daly": [("SM", "SM_CosmOz_Daly")],
}

# Model columns
MODEL_COLS = {
    "BR-Npw": {"ET": ["ET_VIC", "ET_mGV"]},
    "MX-PMm": {"ET": ["ET_VIC", "ET_mGV"]},
    "NT_FoggDam": {"ET": ["ET_VIC", "ET_mGV"], "SM": ["VIC_volumetric_sm", "mGV_volumetric_sm"]},
    "NT_DryRiver": {"ET": ["ET_VIC", "ET_mGV"], "SM": ["VIC_volumetric_sm", "mGV_volumetric_sm"]},
    "NT_CosmOz_Daly": {"SM": ["VIC_volumetric_sm", "mGV_volumetric_sm"]},
}

# Satellite SM columns
SAT_SM_COLS = {
    "NT_FoggDam": "SM_NT_FoggDam",
    "NT_DryRiver": "SM_NT_DryRiver",
    "NT_CosmOz_Daly": "SM_NT_CosmOz_Daly",
}

# Variable groups
VARIABLE_GROUPS = [
    ("ET", "ET_VIC", "ET_mGV", "ET_in-situ", "Evapotranspiration (mm/day)", "Evapotranspiration"),
    ("SM", "VIC_volumetric_sm", "mGV_volumetric_sm", "SM_in-situ", "Volumetric Soil Moisture (m³/m³)", "Soil Moisture"),
]

OUTPUT_DIR = BASE_DIR / "Distribution_Plots" / "In-situ" / "Final"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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
def plot_distribution(df, group, station_short, obs_col, vic_col=None, mgv_col=None, sat_col=None):
    full_station_name = STATION_DISPLAY_NAMES.get(station_short, station_short)
    full_var_name = next((t for g, _, _, _, _, t in VARIABLE_GROUPS if g == group), group)
    ylabel = next((u for g, _, _, _, u, _ in VARIABLE_GROUPS if g == group), "")

    # Collect datasets
    datasets = {}
    if obs_col in df.columns:
        datasets["In-situ"] = df[obs_col].dropna().values
    if vic_col and vic_col in df.columns:
        datasets["VIC-WUR"] = df[vic_col].dropna().values
    if mgv_col and mgv_col in df.columns:
        datasets["VIC-Julia"] = df[mgv_col].dropna().values
    if sat_col and sat_col in df.columns:
        datasets["Satellite"] = df[sat_col].dropna().values

    if not datasets:
        print(f" {group} — no data available → skipped")
        return

    # Compute stats
    stats = {}
    for name, vals in datasets.items():
        mu, sigma = compute_stats(vals)
        stats[name] = (mu, sigma)

    fig, ax = plt.subplots(figsize=(13, 12), dpi=130)

    colors = {
        "In-situ": "#2ca02c",
        "VIC-WUR": "#1f77b4",
        "VIC-Julia": "#ff7f0e",
        "Satellite": "#9467bd",
    }

    for name, vals in datasets.items():
        sns.histplot(vals, stat="count", kde=True, bins=40,          # ← CHANGED TO "count"
                     color=colors.get(name, "#777777"), alpha=0.35,
                     line_kws={'lw': 2.0}, label=name, ax=ax)

    ax.set_title(f"{full_station_name} — In-situ {full_var_name} Distribution", fontsize=25, pad=18)
    ax.set_xlabel(ylabel, fontsize=20)
    ax.set_ylabel("Number of samples", fontsize=20)                 # ← CHANGED LABEL
    ax.tick_params(axis='both', labelsize=15)
    ax.grid(True, ls=":", alpha=0.6)

    # Legend box (color indicators) - stacked vertically, left side
    ax.legend(loc="upper center", bbox_to_anchor=(0.1, -0.1), ncol=1, fontsize=17, framealpha=0.92)

    # Stats box (μ and σ) - right side
    text_lines = []
    for name, (mu, sigma) in stats.items():
        if not np.isnan(mu):
            text_lines.append(f"{name:12} μ = {mu:8.4f}   σ = {sigma:8.4f}")

    textstr = "\n".join(text_lines)
    if textstr:
        props = dict(boxstyle="round,pad=0.65", facecolor="#f8f9fa", alpha=0.94, edgecolor="#444")
        ax.text(0.30, -0.18, textstr, transform=ax.transAxes,
                fontsize=15, verticalalignment="top", horizontalalignment="left",
                family="monospace", bbox=props)

    # Extra bottom space
    fig.tight_layout(rect=[0, 0.32, 1, 1])

    # Save
    safe_station = STATION_SAFE_NAMES.get(station_short, station_short.replace(" ", "_").replace("-", "_"))
    fname = OUTPUT_DIR / f"{safe_station}_{group}_distribution.png"
    plt.savefig(fname, bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"Saved: {fname.name}")


# ────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────
def main():
    if not FILE_INSITU.is_file() or not FILE_MODELS.is_file():
        print("Required files not found.")
        return

    xl_insitu = pd.ExcelFile(FILE_INSITU)
    xl_models = pd.ExcelFile(FILE_MODELS)
    xl_sat_sm = pd.ExcelFile(FILE_SAT_SM) if FILE_SAT_SM.is_file() else None

    print("Generating distribution plots vs in-situ observations...\n")

    for station_short in STATION_DISPLAY_NAMES.keys():
        print(f"Processing station: {station_short}")

        if station_short not in xl_insitu.sheet_names:
            print(f" In-situ sheet '{station_short}' not found → skipped")
            continue
        df_insitu = pd.read_excel(xl_insitu, sheet_name=station_short, index_col=None, parse_dates=['date'])
        df_insitu = df_insitu.set_index('date')

        model_sheet = f"{station_short}_daily_1990_2019"
        if model_sheet not in xl_models.sheet_names:
            print(f" Model sheet '{model_sheet}' not found → skipped")
            continue
        df_models = pd.read_excel(xl_models, sheet_name=model_sheet, index_col=None, parse_dates=['date'])
        df_models = df_models.set_index('date')

        df_main = df_insitu.join(df_models, how="inner").sort_index()
        if df_main.empty:
            print(" No overlapping dates → skipped")
            continue
        print(f" In-situ + models matching points: {len(df_main):,d}")

        for group, insitu_col in INSITU_VARS.get(station_short, []):
            if insitu_col not in df_main.columns:
                print(f" {group} — in-situ column missing → skipped")
                continue

            sim_cols = MODEL_COLS.get(station_short, {}).get(group, [])
            vic_col = next((c for c in sim_cols if "VIC" in c), None)
            mgv_col = next((c for c in sim_cols if "mGV" in c), None)

            sat_col = SAT_SM_COLS.get(station_short) if group == "SM" else None
            if sat_col and xl_sat_sm is not None:
                sat_sheet = station_short
                if sat_sheet in xl_sat_sm.sheet_names:
                    df_sat = pd.read_excel(xl_sat_sm, sheet_name=sat_sheet, index_col=None, parse_dates=['date'])
                    df_sat = df_sat.set_index('date')
                    df_main = df_main.join(df_sat[[sat_col]], how="left")

            plot_distribution(df_main, group, station_short, insitu_col,
                              vic_col=vic_col, mgv_col=mgv_col, sat_col=sat_col)

    print(f"\nAll done. Distribution plots saved in:\n {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()