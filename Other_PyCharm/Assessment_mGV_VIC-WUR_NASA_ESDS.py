import pandas as pd
import numpy as np
from pathlib import Path

# ────────────────────────────────────────────────
#  CONFIGURATION
# ────────────────────────────────────────────────

BASE_DIR = Path(r"C:\Users\31623\Downloads\Juul\WUR\WUR MSc thesis\Data_MSc_thesis")

FILE_GLOBAL = BASE_DIR / "Global_NH_NR_DP_S10.xlsx"     # VIC model
FILE_SAT    = BASE_DIR / "Satellite_NH_NR_DP_S10.xlsx"  # observations

# Region mapping: global sheet name → satellite sheet name
REGION_MAPPING = {
    "Pantanal_1990_2019": "Pantanal",
    "SE_CA_1990_2019":    "SE_CA",
    "BKJ_1990_2019":      "BKJ",
    "Yucatán_1990_2019":  "Yucatán",
    "NT_1990_2019":       "NT"
}

VARIABLES = [
    ("PET",  "PET_VIC",   "Mean_PET"),
    ("ET",   "ET_VIC",    "Mean_ET"),
    ("Tsurf","Tsurf_VIC", "Mean_LST"),
    ("PET",  "PET_mGV",   "Mean_PET"),
    ("ET",   "ET_mGV",    "Mean_ET"),
    ("Tsurf","Tsurf_mGV", "Mean_LST"),
]

# ────────────────────────────────────────────────
#  METRIC FUNCTIONS
# ────────────────────────────────────────────────

def nse(obs: np.ndarray, sim: np.ndarray) -> float:
    if len(obs) == 0:
        return np.nan
    mean_obs = np.mean(obs)
    numerator = np.sum((sim - obs) ** 2)
    denominator = np.sum((obs - mean_obs) ** 2)
    if denominator == 0:
        return np.nan
    return 1 - numerator / denominator


def kling_gupta(obs: np.ndarray, sim: np.ndarray) -> tuple[float, float, float, float]:
    """Returns KGE, r (correlation), alpha (std ratio), beta (mean ratio)"""
    if len(obs) < 2:
        return np.nan, np.nan, np.nan, np.nan

    mean_obs = np.mean(obs)
    mean_sim = np.mean(sim)
    std_obs = np.std(obs)
    std_sim = np.std(sim)

    if std_obs == 0 or std_sim == 0:
        return np.nan, np.nan, np.nan, np.nan

    # Pearson correlation (sample version, ddof=0 like most hydrological packages)
    r = np.corrcoef(obs, sim)[0, 1]

    beta  = mean_sim / mean_obs
    alpha = std_sim / std_obs

    kge = 1 - np.sqrt(
        (r - 1)**2 +
        (alpha - 1)**2 +
        (beta - 1)**2
    )
    return kge, r, alpha, beta


def pbias(obs: np.ndarray, sim: np.ndarray) -> float:
    if len(obs) == 0:
        return np.nan
    return 100 * np.sum(sim - obs) / np.sum(obs)


def rmse(obs: np.ndarray, sim: np.ndarray) -> float:
    if len(obs) == 0:
        return np.nan
    return np.sqrt(np.mean((sim - obs) ** 2))


def classify_nse(n: float) -> str:
    if np.isnan(n): return "No data"
    if n > 0.75:  return "Very good"
    if n > 0.65:  return "Good"
    if n > 0.50:  return "Satisfactory"
    if n > 0.40:  return "Acceptable"
    return "Unsatisfactory"


def classify_kge(k: float) -> str:
    if np.isnan(k): return "No data"
    if k > 0.77: return "Very good"
    if k > 0.53: return "Good"
    if k > 0.30: return "Satisfactory"
    return "Unsatisfactory"


def classify_pbias(p: float) -> str:
    if np.isnan(p): return "No data"
    p = abs(p)
    if p < 10:  return "Very good"
    if p < 15:  return "Good"
    if p < 25:  return "Satisfactory"
    return "Unsatisfactory"


def classify_rmse(r: float, obs: np.ndarray) -> str:
    if np.isnan(r) or len(obs) == 0:
        return "No data"
    std_obs = np.std(obs)
    if r < 0.5 * std_obs:
        return "Satisfactory (RMSE < 0.5 × std_obs)"
    return f"Unsatisfactory (RMSE ≥ 0.5 × std_obs = {0.5*std_obs:.3g})"


# ────────────────────────────────────────────────
#  MAIN LOGIC
# ────────────────────────────────────────────────

def main():
    if not FILE_GLOBAL.is_file():
        print(f"File not found: {FILE_GLOBAL}")
        return
    if not FILE_SAT.is_file():
        print(f"File not found: {FILE_SAT}")
        return

    xl_global = pd.ExcelFile(FILE_GLOBAL)
    xl_sat    = pd.ExcelFile(FILE_SAT)

    print("=" * 80)
    print(" MODEL PERFORMANCE ASSESSMENT".center(80))
    print(" NSE – KGE – PBIAS – RMSE".center(80))
    print("=" * 80)

    for sheet_global, sheet_sat in REGION_MAPPING.items():
        if sheet_global not in xl_global.sheet_names:
            print(f"→ Sheet '{sheet_global}' not found in global file – skipping")
            continue
        if sheet_sat not in xl_sat.sheet_names:
            print(f"→ Sheet '{sheet_sat}' not found in satellite file – skipping")
            continue

        print(f"\nRegion: {sheet_global}  (obs = {sheet_sat})")
        print("-" * 80)

        df_sim = pd.read_excel(xl_global, sheet_name=sheet_global, index_col=0, parse_dates=True)
        df_obs = pd.read_excel(xl_sat,    sheet_name=sheet_sat,    index_col=0, parse_dates=True)

        # Make sure index is datetime
        if not pd.api.types.is_datetime64_any_dtype(df_sim.index):
            print("  Warning: simulation index not recognized as datetime")
        if not pd.api.types.is_datetime64_any_dtype(df_obs.index):
            print("  Warning: observation index not recognized as datetime")

        # Inner join on date → only days present in BOTH files
        df = df_sim.join(df_obs, how="inner")

        if df.empty:
            print("  No overlapping dates → skipping region")
            continue

        print(f"  Number of matching time steps: {len(df):,d}\n")

        for group, sim_col, obs_col in VARIABLES:
            if sim_col not in df_sim.columns or obs_col not in df_obs.columns:
                print(f"  {group:6} | {sim_col:12} or {obs_col:12} missing → skipped")
                continue

            # Use only rows where both values are not NaN
            sub = df[[sim_col, obs_col]].dropna()
            if len(sub) < 3:
                print(f"  {group:6} | {sim_col:12} vs {obs_col:12} → too few valid points ({len(sub)})")
                continue

            obs = sub[obs_col].to_numpy()
            sim = sub[sim_col].to_numpy()

            n   = nse(obs, sim)
            k, r, a, b = kling_gupta(obs, sim)
            p   = pbias(obs, sim)
            rm  = rmse(obs, sim)

            print(f"  {group:6} | {sim_col:12} vs {obs_col:12}")
            print(f"          NSE   = {n:8.4f}  → {classify_nse(n)}")
            print(f"          KGE   = {k:8.4f}  → {classify_kge(k)}")
            print(f"            ├─ r     = {r:6.4f}")
            print(f"            ├─ α     = {a:6.4f}")
            print(f"            └─ β     = {b:6.4f}")
            print(f"          PBIAS = {p:8.4f} %  → {classify_pbias(p)}")
            print(f"          RMSE  = {rm:8.4f}  → {classify_rmse(rm, obs)}")
            print()

    print("=" * 80)
    print("Done.\n")


if __name__ == "__main__":
    main()