import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────
BASE_DIR = Path(r"C:\Users\31623\Downloads\Juul\WUR\WUR MSc thesis\Data_MSc_thesis")

# In-situ observations (reference / x-axis)
INSITU_DIR = Path(r"D:\WUR\In-Situ_Data")
FILE_INSITU = INSITU_DIR / "In-Situ_Data.xlsx"

# Model outputs (VIC + mGV) — station-specific daily time series (y-axis)
MODEL_DIR = Path(r"D:\WUR\Thesis_model_runs\InSitu_NH_NR_DP_S10")
FILE_MODELS = MODEL_DIR / "InSitu_NH_NR_DP_S10.xlsx"

# Satellite SM (only for some NT stations, additional y-axis)
SAT_SM_DIR = Path(r"D:\WUR\In-Situ_Data")
FILE_SAT_SM = SAT_SM_DIR / "Satellite_In-Situ_Data.xlsx"

# Mapping: in-situ sheet name → display name for plots
STATION_DISPLAY_NAMES = {
    "BR-Npw": "BR-Npw",
    "MX-PMm": "MX-PMm",
    "NT_FoggDam": "NT Fogg Dam",
    "NT_DryRiver": "NT Dry River",
    "NT_CosmOz_Daly": "NT CosmOz Daly",
}

# Safe names for filenames
STATION_SAFE_NAMES = {
    "BR-Npw": "BR-Npw",
    "MX-PMm": "MX-PMm",
    "NT_FoggDam": "NT_FoggDam",
    "NT_DryRiver": "NT_DryRiver",
    "NT_CosmOz_Daly": "NT_CosmOz_Daly",
}

# Which stations have which variables in in-situ data
INSITU_VARS = {
    "BR-Npw": [("ET", "ET_BR-Npw")],
    "MX-PMm": [("ET", "ET_MX-PMm")],
    "NT_FoggDam": [("ET", "ET_FoggDam"), ("SM", "SM_FoggDam")],
    "NT_DryRiver": [("ET", "ET_DryRiver"), ("SM", "SM_DryRiver")],
    "NT_CosmOz_Daly": [("SM", "SM_CosmOz_Daly")],
}

# Model columns per station (VIC and mGV outputs)
MODEL_COLS = {
    "BR-Npw": {"ET": ["ET_VIC", "ET_mGV"]},
    "MX-PMm": {"ET": ["ET_VIC", "ET_mGV"]},
    "NT_FoggDam": {"ET": ["ET_VIC", "ET_mGV"], "SM": ["VIC_volumetric_sm", "mGV_volumetric_sm"]},
    "NT_DryRiver": {"ET": ["ET_VIC", "ET_mGV"], "SM": ["VIC_volumetric_sm", "mGV_volumetric_sm"]},
    "NT_CosmOz_Daly": {"SM": ["VIC_volumetric_sm", "mGV_volumetric_sm"]},
}

# Satellite SM columns (only for some NT stations)
SAT_SM_COLS = {
    "NT_FoggDam": "SM_NT_FoggDam",
    "NT_DryRiver": "SM_NT_DryRiver",
    "NT_CosmOz_Daly": "SM_NT_CosmOz_Daly",
}

# Output directory
OUTPUT_DIR = BASE_DIR / "Scatter_Obs_vs_Sim" / "In-situ" / "Final"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ────────────────────────────────────────────────
# PLOTTING FUNCTION – Observed (in-situ) vs Simulated (VIC / mGV / satellite)
# ────────────────────────────────────────────────
def plot_scatter_obs_vs_sim(df, group, station_short, obs_col, vic_col=None, mgv_col=None, sat_col=None):
    """Creates Observed (in-situ) vs Simulated scatter plot"""
    full_station = STATION_DISPLAY_NAMES.get(station_short, station_short)
    full_var_name = "Evapotranspiration" if group == "ET" else "Soil Moisture"
    full_ylabel = "Evapotranspiration (mm/day)" if group == "ET" else "Volumetric Soil Moisture (m³/m³)"

    # Collect available simulated datasets
    sim_datasets = {}
    if vic_col and vic_col in df.columns:
        sim_datasets["VIC-WUR"] = (vic_col, "#1f77b4")
    if mgv_col and mgv_col in df.columns:
        sim_datasets["VIC-Julia"] = (mgv_col, "#ff7f0e")
    if sat_col and sat_col in df.columns and group == "SM":
        sim_datasets["Satellite"] = (sat_col, "#9467bd")

    if not sim_datasets:
        print(f" {group} — no simulated data available for scatter → skipped")
        return

    fig, ax = plt.subplots(figsize=(9, 9), dpi=110)

    # ─── Scatter points for each simulated dataset ───
    for name, (sim_col, color) in sim_datasets.items():
        sub = df[[obs_col, sim_col]].dropna()
        if len(sub) < 20:
            print(f" {group} — too few points for {name} ({len(sub)})")
            continue
        obs = sub[obs_col].values
        sim = sub[sim_col].values
        ax.scatter(obs, sim, s=25, alpha=0.5, color=color, label=name, edgecolor="none")

    # ─── 1:1 reference line ───────────────────────────
    all_vals = df[obs_col].dropna().values
    for sim_col, _ in sim_datasets.values():
        all_vals = np.concatenate([all_vals, df[sim_col].dropna().values])
    min_val = np.nanmin(all_vals) * 0.95 if len(all_vals) > 0 else 0
    max_val = np.nanmax(all_vals) * 1.05 if len(all_vals) > 0 else 1
    ax.plot([min_val, max_val], [min_val, max_val], color='black', lw=1.8, linestyle='--', alpha=0.7,
            label='1 : 1 line')

    # ─── Style & labels (with requested font sizes) ───────────────────────────────
    ax.set_xlabel(f"In-situ (observed) – {full_ylabel}", fontsize=20)
    ax.set_ylabel(f"Simulated – {full_ylabel}", fontsize=20)

    # Title: size 25, NOT bold
    ax.set_title(f"{full_station} – {full_var_name}", fontsize=25, pad=16)

    ax.grid(True, linestyle=':', alpha=0.6)

    # Legend with requested font size
    ax.legend(loc='upper left', fontsize=17, framealpha=0.92)

    # Tick marks font size
    ax.tick_params(axis='both', labelsize=15)

    # Square aspect & limits
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlim(min_val, max_val)
    ax.set_ylim(min_val, max_val)

    fig.tight_layout()

    # Save
    safe_station = STATION_SAFE_NAMES.get(station_short, station_short.replace(" ", "_").replace("-", "_"))
    fname = OUTPUT_DIR / f"{safe_station}_{group}_scatter_obs_vs_sim.png"
    plt.savefig(fname, bbox_inches='tight', dpi=180)
    plt.close(fig)
    print(f"Saved: {fname.name}")


# ────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────
def main():
    if not FILE_INSITU.is_file():
        print(f"In-situ file not found: {FILE_INSITU}")
        return
    if not FILE_MODELS.is_file():
        print(f"Model file not found: {FILE_MODELS}")
        return

    xl_insitu = pd.ExcelFile(FILE_INSITU)
    xl_models = pd.ExcelFile(FILE_MODELS)
    xl_sat_sm = pd.ExcelFile(FILE_SAT_SM) if FILE_SAT_SM.is_file() else None

    print("Creating Observed (in-situ) vs Simulated scatter plots...\n")

    for station_short in STATION_DISPLAY_NAMES.keys():
        print(f"Processing station: {station_short}")

        # Load in-situ (reference / x-axis)
        if station_short not in xl_insitu.sheet_names:
            print(f" In-situ sheet '{station_short}' not found → skipped")
            continue
        df_insitu = pd.read_excel(xl_insitu, sheet_name=station_short, index_col=None, parse_dates=['date'])
        df_insitu = df_insitu.set_index('date')

        # Load model outputs
        model_sheet = f"{station_short}_daily_1990_2019"
        if model_sheet not in xl_models.sheet_names:
            print(f" Model sheet '{model_sheet}' not found → skipped")
            continue
        df_models = pd.read_excel(xl_models, sheet_name=model_sheet, index_col=None, parse_dates=['date'])
        df_models = df_models.set_index('date')

        # Join in-situ + models
        df_main = df_insitu.join(df_models, how="inner").sort_index()
        if df_main.empty:
            print(" No overlapping dates between in-situ and models → skipped")
            continue
        print(f" In-situ + models matching points: {len(df_main):,d}")

        # Add satellite SM if available
        sat_col = None
        if station_short in SAT_SM_COLS and xl_sat_sm is not None:
            sat_sheet = station_short
            sat_col = SAT_SM_COLS[station_short]
            if sat_sheet in xl_sat_sm.sheet_names:
                df_sat_sm = pd.read_excel(xl_sat_sm, sheet_name=sat_sheet, index_col=None, parse_dates=['date'])
                df_sat_sm = df_sat_sm.set_index('date')
                df_main = df_main.join(df_sat_sm[[sat_col]], how="left").sort_index()
                print(f" Satellite SM joined — {sat_col} added to df_main")

        # ─── Main variables (ET and/or SM) ────────────────
        for group, insitu_col in INSITU_VARS.get(station_short, []):
            if insitu_col not in df_main.columns:
                print(f" {group} — in-situ column '{insitu_col}' missing → skipped")
                continue

            sim_cols = MODEL_COLS.get(station_short, {}).get(group, [])
            vic_col = next((c for c in sim_cols if "VIC" in c), None)
            mgv_col = next((c for c in sim_cols if "mGV" in c), None)

            current_sat_col = sat_col if group == "SM" else None

            if vic_col or mgv_col or current_sat_col:
                plot_scatter_obs_vs_sim(df_main, group, station_short, insitu_col,
                                        vic_col=vic_col, mgv_col=mgv_col, sat_col=current_sat_col)
            else:
                print(f" {group} — no simulated data available → skipped")

    print(f"\nFinished!\nAll scatter plots saved in:\n{OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()