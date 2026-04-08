import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────

BASE_DIR = Path(r"C:\Users\31623\Downloads\Juul\WUR\WUR MSc thesis\Data_MSc_thesis")

# In-situ observations (reference / temporal alignment base)
INSITU_DIR = Path(r"D:\WUR\In-Situ_Data")
FILE_INSITU = INSITU_DIR / "In-Situ_Data.xlsx"

# Model outputs (VIC + mGV) — station-specific daily time series
MODEL_DIR = Path(r"D:\WUR\Thesis_model_runs\InSitu_NH_NR_DP_S10")
FILE_MODELS = MODEL_DIR / "InSitu_NH_NR_DP_S10.xlsx"

# Satellite SM (only for some NT stations)
SAT_SM_DIR = Path(r"D:\WUR\In-Situ_Data")
FILE_SAT_SM = SAT_SM_DIR / "Satellite_In-Situ_Data.xlsx"

# Mapping: in-situ sheet name → display name for plots
STATION_DISPLAY_NAMES = {
    "BR-Npw":              "BR-Npw",
    "MX-PMm":              "MX-PMm",
    "NT_FoggDam":          "NT Fogg Dam",
    "NT_DryRiver":         "NT Dry River",
    "NT_CosmOz_Daly":      "NT CosmOz Daly",
}

# Full variable names for titles
VAR_FULL_NAMES = {
    "ET": "Evapotranspiration",
    "SM": "Soil Moisture",
}

# Short variable names for legend labels
VAR_SHORT_NAMES = {
    "ET": "ET",
    "SM": "SM",
}

# Which stations have which variables in in-situ data
INSITU_VARS = {
    "BR-Npw":              [("ET", "ET_BR-Npw")],
    "MX-PMm":              [("ET", "ET_MX-PMm")],
    "NT_FoggDam":          [("ET", "ET_FoggDam"), ("SM", "SM_FoggDam")],
    "NT_DryRiver":         [("ET", "ET_DryRiver"), ("SM", "SM_DryRiver")],
    "NT_CosmOz_Daly":      [("SM", "SM_CosmOz_Daly")],
}

# Model columns per station (VIC and mGV outputs)
MODEL_COLS = {
    "BR-Npw":              {"ET": ["ET_VIC", "ET_mGV"]},
    "MX-PMm":              {"ET": ["ET_VIC", "ET_mGV"]},
    "NT_FoggDam":          {"ET": ["ET_VIC", "ET_mGV"], "SM": ["VIC_volumetric_sm", "mGV_volumetric_sm"]},
    "NT_DryRiver":         {"ET": ["ET_VIC", "ET_mGV"], "SM": ["VIC_volumetric_sm", "mGV_volumetric_sm"]},
    "NT_CosmOz_Daly":      {"SM": ["VIC_volumetric_sm", "mGV_volumetric_sm"]},
}

# Satellite SM columns (only for some NT stations)
SAT_SM_COLS = {
    "NT_FoggDam":     "SM_NT_FoggDam",
    "NT_DryRiver":    "SM_NT_DryRiver",
    "NT_CosmOz_Daly": "SM_NT_CosmOz_Daly",
}

# Output directory
OUTPUT_DIR = BASE_DIR / "Performance_Plots" / "In-situ"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ────────────────────────────────────────────────
# METRIC FUNCTIONS
# ────────────────────────────────────────────────

def nse(obs, sim):
    if len(obs) == 0:
        return np.nan
    mean_obs = np.mean(obs)
    num = np.sum((sim - obs) ** 2)
    den = np.sum((obs - mean_obs) ** 2)
    return 1 - num / den if den != 0 else np.nan


def kling_gupta(obs, sim):
    if len(obs) < 2:
        return np.nan
    mean_o, mean_s = np.mean(obs), np.mean(sim)
    std_o, std_s   = np.std(obs),  np.std(sim)
    if std_o == 0 or std_s == 0:
        return np.nan
    r = np.corrcoef(obs, sim)[0, 1]
    alpha = std_s / std_o
    beta  = mean_s / mean_o
    kge = 1 - np.sqrt((r - 1)**2 + (alpha - 1)**2 + (beta - 1)**2)
    return kge


# ────────────────────────────────────────────────
# PLOTTING FUNCTION (updated legend labels + satellite solid line)
# ────────────────────────────────────────────────

def plot_triple_timeseries(df, group, station_short, obs_col, vic_col=None, mgv_col=None, sat_col=None):
    full_station_name = STATION_DISPLAY_NAMES.get(station_short, station_short)
    ylabel = f"{VAR_FULL_NAMES[group]} ({'mm/day' if group == 'ET' else 'm³/m³'})"
    full_var_name = f"In-situ {VAR_FULL_NAMES[group]}"

    fig, ax = plt.subplots(figsize=(12, 6), dpi=110)

    # Always plot in-situ observation (reference line)
    ax.plot(df.index, df[obs_col], label=f"In-situ {VAR_SHORT_NAMES[group]}", lw=1.4, color="#2ca02c",
            alpha=0.9, linestyle="--")

    # Plot VIC if available
    if vic_col and vic_col in df.columns:
        ax.plot(df.index, df[vic_col], label=f"{VAR_SHORT_NAMES[group]} VIC", lw=1.1, color="#1f77b4")

    # Plot mGV if available
    if mgv_col and mgv_col in df.columns:
        ax.plot(df.index, df[mgv_col], label=f"{VAR_SHORT_NAMES[group]} mGV", lw=1.1, color="#ff7f0e")

    # Overlay satellite SM if provided (solid line, purple-ish for distinction)
    if sat_col and sat_col in df.columns and group == "SM":
        ax.plot(df.index, df[sat_col], label=f"Satellite {VAR_SHORT_NAMES[group]}", lw=1.4, color="#9467bd",
                alpha=0.9, linestyle="-")  # ← changed to solid line

    ax.set_title(f"{full_station_name} — {full_var_name}", fontsize=14, pad=12)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_xlabel("Date", fontsize=11)

    ax.grid(True, ls=":", alpha=0.7)
    ax.legend(loc="upper left", ncol=3, fontsize=10.5, framealpha=0.92)

    # Performance text box — only show VIC & mGV metrics when both exist
    if vic_col and mgv_col and vic_col in df.columns and mgv_col in df.columns:
        obs_vals = df[obs_col].dropna().to_numpy()
        vic_vals = df[vic_col].reindex(df[obs_col].index).dropna().to_numpy()
        mgv_vals = df[mgv_col].reindex(df[obs_col].index).dropna().to_numpy()

        # Ensure same length for metrics
        min_len = min(len(obs_vals), len(vic_vals), len(mgv_vals))
        obs_vals = obs_vals[:min_len]
        vic_vals = vic_vals[:min_len]
        mgv_vals = mgv_vals[:min_len]

        nse_vic = nse(obs_vals, vic_vals)
        kge_vic = kling_gupta(obs_vals, vic_vals)
        nse_mgv = nse(obs_vals, mgv_vals)
        kge_mgv = kling_gupta(obs_vals, mgv_vals)

        textstr = (
            f"VIC-WUR   NSE = {nse_vic:8.4f}\n"
            f"          KGE = {kge_vic:8.4f}\n"
            f"mGV       NSE = {nse_mgv:8.4f}\n"
            f"          KGE = {kge_mgv:8.4f}"
        )
        props = dict(boxstyle="round,pad=0.5", facecolor="#f8f9fa", alpha=0.92, edgecolor="#555")
        ax.text(0.98, 0.98, textstr, transform=ax.transAxes, fontsize=10.2,
                verticalalignment="top", horizontalalignment="right", bbox=props)

    fig.tight_layout()

    # Save
    safe_station = station_short.replace(" ", "_").replace("-", "_")
    fname = OUTPUT_DIR / f"{safe_station}_{group}_timeseries.png"
    plt.savefig(fname, bbox_inches="tight", dpi=180)
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

    print("Generating in-situ performance plots...\n")

    for station_short in STATION_DISPLAY_NAMES.keys():
        print(f"Processing station: {station_short}")

        # Load in-situ (reference / observation)
        if station_short not in xl_insitu.sheet_names:
            print(f"  In-situ sheet '{station_short}' not found → skipped")
            continue

        df_insitu = pd.read_excel(xl_insitu, sheet_name=station_short, index_col=None, parse_dates=['date'])
        df_insitu = df_insitu.set_index('date')

        # Load model outputs
        model_sheet = f"{station_short}_daily_1990_2019"
        if model_sheet not in xl_models.sheet_names:
            print(f"  Model sheet '{model_sheet}' not found → skipped")
            continue

        df_models = pd.read_excel(xl_models, sheet_name=model_sheet, index_col=None, parse_dates=['date'])
        df_models = df_models.set_index('date')

        # Join in-situ + models (temporal reference = in-situ)
        df_main = df_insitu.join(df_models, how="inner").sort_index()

        if df_main.empty:
            print("  No overlapping dates between in-situ and models → skipped")
            continue

        print(f"  In-situ + models matching points: {len(df_main):,d}")

        # ─── Main variables (ET and/or SM) ────────────────
        for group, insitu_col in INSITU_VARS.get(station_short, []):
            if insitu_col not in df_main.columns:
                print(f"  {group} — in-situ column '{insitu_col}' missing → skipped")
                continue

            # Get available model columns
            sim_cols = MODEL_COLS.get(station_short, {}).get(group, [])
            if not sim_cols:
                print(f"  {group} — no model columns found → skipped")
                continue

            vic_col = next((c for c in sim_cols if "VIC" in c), None)
            mgv_col = next((c for c in sim_cols if "mGV" in c), None)

            # Plot the full comparison (in-situ + VIC + mGV)
            plot_triple_timeseries(df_main, group, station_short, insitu_col,
                                   vic_col=vic_col, mgv_col=mgv_col)

        # ─── Satellite SM overlay (only where available) ────────────────
        if station_short in SAT_SM_COLS and xl_sat_sm is not None:
            sat_sheet = station_short
            sat_col = SAT_SM_COLS[station_short]

            if sat_sheet not in xl_sat_sm.sheet_names:
                print(f"  Satellite SM sheet '{sat_sheet}' not found → skipped")
            else:
                df_sat_sm = pd.read_excel(xl_sat_sm, sheet_name=sat_sheet, index_col=None, parse_dates=['date'])
                df_sat_sm = df_sat_sm.set_index('date')

                # Join satellite SM to the in-situ + models DataFrame
                df_all = df_main.join(df_sat_sm[[sat_col]], how="inner").sort_index()

                if df_all.empty:
                    print("  No overlapping dates for satellite SM → skipped")
                else:
                    # Get SM in-situ column
                    sm_insitu_col = [c for g, c in INSITU_VARS[station_short] if g == "SM"][0]

                    # VIC/mGV SM columns (if available)
                    vic_sm_col = MODEL_COLS.get(station_short, {}).get("SM", [None])[0]
                    mgv_sm_col = MODEL_COLS.get(station_short, {}).get("SM", [None, None])[1]

                    # Plot in-situ SM + VIC + mGV + satellite SM (solid line)
                    plot_triple_timeseries(df_all, "SM", station_short, sm_insitu_col,
                                           vic_col=vic_sm_col, mgv_col=mgv_sm_col,
                                           sat_col=sat_col)

    print(f"\nAll done. Plots saved in:\n  {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()