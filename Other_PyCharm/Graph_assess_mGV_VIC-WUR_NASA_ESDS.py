import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ────────────────────────────────────────────────
#  CONFIGURATION
# ────────────────────────────────────────────────

BASE_DIR = Path(r"C:\Users\31623\Downloads\Juul\WUR\WUR MSc thesis\Data_MSc_thesis")

FILE_GLOBAL = BASE_DIR / "Global_NH_NR_DP_S10.xlsx"     # VIC + mGV
FILE_SAT    = BASE_DIR / "Satellite_NH_NR_DP_S10.xlsx"  # observations

# Region mapping: global sheet name → satellite sheet name → full display name
REGION_DISPLAY_NAMES = {
    "Pantanal_1990_2019":      "Pantanal",
    "SE_CA_1990_2019":         "South-Eastern/Central Africa",
    "BKJ_1990_2019":           "Bornean Karst Jungle",
    "Yucatán_1990_2019":       "Yucatán Peninsula",
    "NT_1990_2019":            "Northern Territory"
}

# For filename safety (no spaces, no special chars)
REGION_SAFE_NAMES = {
    "Pantanal_1990_2019":      "Pantanal",
    "SE_CA_1990_2019":         "SE_CA",
    "BKJ_1990_2019":           "BKJ",
    "Yucatán_1990_2019":       "Yucatan_Peninsula",
    "NT_1990_2019":            "Northern_Territory"
}

# Variable groups: (short key, vic column, mgv column, obs column, unit, full title name)
VARIABLE_GROUPS = [
    ("PET", "PET_VIC",  "PET_mGV",  "Mean_PET",  "Potential Evapotranspiration (mm/day)", "Potential Evapotranspiration"),
    ("ET",  "ET_VIC",   "ET_mGV",   "Mean_ET",   "Evapotranspiration (mm/day)",          "Evapotranspiration"),
    ("Tsurf","Tsurf_VIC","Tsurf_mGV","Mean_LST",  "Surface Temperature (°C)",            "Surface Temperature"),
]

OUTPUT_DIR = BASE_DIR / "Performance_Plots"
OUTPUT_DIR.mkdir(exist_ok=True)

# ────────────────────────────────────────────────
#  METRIC FUNCTIONS (unchanged)
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


def pbias(obs, sim):
    if len(obs) == 0 or np.sum(obs) == 0:
        return np.nan
    return 100 * np.sum(sim - obs) / np.sum(obs)


def rmse(obs, sim):
    if len(obs) == 0:
        return np.nan
    return np.sqrt(np.mean((sim - obs) ** 2))


# ────────────────────────────────────────────────
#  PLOTTING FUNCTION (only title changed)
# ────────────────────────────────────────────────

def plot_triple_timeseries(df, var_info, region_sheet, nse_vic, kge_vic, nse_mgv, kge_mgv):
    _, col_vic, col_mgv, col_obs, ylabel, full_var_name = var_info
    full_region_name = REGION_DISPLAY_NAMES.get(region_sheet, region_sheet)

    fig, ax = plt.subplots(figsize=(12, 6), dpi=110)

    # Plot lines (legend labels unchanged!)
    ax.plot(df.index, df[col_vic], label="PET VIC",    lw=1.1, color="#1f77b4")
    ax.plot(df.index, df[col_mgv], label="PET mGV",    lw=1.1, color="#ff7f0e")
    ax.plot(df.index, df[col_obs], label="Satellite PET", lw=1.4, color="#2ca02c",
            alpha=0.9, linestyle="--")

    ax.set_title(f"{full_region_name} — {full_var_name}", fontsize=14, pad=12)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_xlabel("Date", fontsize=11)

    ax.grid(True, ls=":", alpha=0.7)
    ax.legend(loc="upper left", ncol=3, fontsize=10.5, framealpha=0.92)

    # Performance text box (unchanged)
    textstr = (
        f"VIC-WUR   NSE  = {nse_vic:8.4f}\n"
        f"          KGE  = {kge_vic:8.4f}\n"
        f"mGV       NSE  = {nse_mgv:8.4f}\n"
        f"          KGE  = {kge_mgv:8.4f}"
    )

    props = dict(boxstyle="round,pad=0.5", facecolor="#f8f9fa", alpha=0.92, edgecolor="#555")
    ax.text(0.98, 0.98, textstr, transform=ax.transAxes, fontsize=10.2,
            verticalalignment="top", horizontalalignment="right", bbox=props)

    fig.tight_layout()

    # Save using safe filename
    safe_region = REGION_SAFE_NAMES.get(region_sheet, region_sheet.replace(" ", "_").replace("í", "i"))
    fname = OUTPUT_DIR / f"{safe_region}_{var_info[0]}_timeseries.png"
    plt.savefig(fname, bbox_inches="tight", dpi=180)
    plt.close(fig)

    print(f"Saved: {fname.name}")


# ────────────────────────────────────────────────
#  MAIN (only title-related changes via arguments)
# ────────────────────────────────────────────────

def main():
    if not FILE_GLOBAL.is_file() or not FILE_SAT.is_file():
        print("One or both Excel files not found.")
        return

    xl_global = pd.ExcelFile(FILE_GLOBAL)
    xl_sat    = pd.ExcelFile(FILE_SAT)

    print("Generating performance plots...\n")

    for sheet_global, sheet_sat in REGION_MAPPING.items():
        if sheet_global not in xl_global.sheet_names or sheet_sat not in xl_sat.sheet_names:
            print(f"Skipping {sheet_global} — sheet missing")
            continue

        print(f"Processing region: {sheet_global}")

        df_sim = pd.read_excel(xl_global, sheet_name=sheet_global, index_col=0, parse_dates=True)
        df_obs = pd.read_excel(xl_sat,    sheet_name=sheet_sat,    index_col=0, parse_dates=True)

        # Ensure datetime index
        df_sim.index = pd.to_datetime(df_sim.index)
        df_obs.index = pd.to_datetime(df_obs.index)

        # Join on date (inner)
        df = df_sim.join(df_obs, how="inner").sort_index()

        if df.empty:
            print("  No overlapping dates → skipped")
            continue

        for var_info in VARIABLE_GROUPS:
            _, col_vic, col_mgv, col_obs, _, _ = var_info

            if not all(c in df.columns for c in [col_vic, col_mgv, col_obs]):
                print(f"  Skipping {var_info[0]} — missing column(s)")
                continue

            sub = df[[col_vic, col_mgv, col_obs]].dropna()
            if len(sub) < 10:
                print(f"  {var_info[0]} — too few valid points ({len(sub)})")
                continue

            obs = sub[col_obs].to_numpy()
            vic = sub[col_vic].to_numpy()
            mgv = sub[col_mgv].to_numpy()

            nse_vic = nse(obs, vic)
            kge_vic = kling_gupta(obs, vic)
            nse_mgv = nse(obs, mgv)
            kge_mgv = kling_gupta(obs, mgv)

            # Plot with full names
            plot_triple_timeseries(sub, var_info, sheet_global, nse_vic, kge_vic, nse_mgv, kge_mgv)

    print(f"\nAll done. Plots saved in:\n  {OUTPUT_DIR}\n")


# We still need REGION_MAPPING for sheet names
REGION_MAPPING = {
    "Pantanal_1990_2019": "Pantanal",
    "SE_CA_1990_2019":    "SE_CA",
    "BKJ_1990_2019":      "BKJ",
    "Yucatán_1990_2019":  "Yucatán",
    "NT_1990_2019":       "NT"
}


if __name__ == "__main__":
    main()