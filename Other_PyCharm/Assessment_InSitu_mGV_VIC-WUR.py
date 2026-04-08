import pandas as pd
import numpy as np
from pathlib import Path

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────

BASE_DIR = Path(r"C:\Users\31623\Downloads\Juul\WUR\WUR MSc thesis\Data_MSc_thesis")

# In-situ (reference / observed) data
INSITU_DIR = Path(r"D:\WUR\In-Situ_Data")
FILE_INSITU = INSITU_DIR / "In-Situ_Data.xlsx"

# Model outputs (VIC + mGV) — daily time series at stations
MODEL_DIR = Path(r"D:\WUR\Thesis_model_runs\InSitu_NH_NR_DP_S10")
FILE_MODELS = MODEL_DIR / "InSitu_NH_NR_DP_S10.xlsx"

# Satellite SM (only for some NT stations)
SAT_SM_DIR = Path(r"D:\WUR\In-Situ_Data")
FILE_SAT_SM = SAT_SM_DIR / "Satellite_In-Situ_Data.xlsx"

# Mapping: in-situ sheet name → display name
STATION_MAPPING = {
    "BR-Npw":              "BR-Npw",
    "MX-PMm":              "MX-PMm",
    "NT_FoggDam":          "NT Fogg Dam",
    "NT_DryRiver":         "NT Dry River",
    "NT_CosmOz_Daly":      "NT CosmOz Daly",
}

# Which stations have which variables in in-situ data
# Format: station → list of (group, in-situ col)
INSITU_VARS = {
    "BR-Npw":              [("ET", "ET_BR-Npw")],
    "MX-PMm":              [("ET", "ET_MX-PMm")],
    "NT_FoggDam":          [("ET", "ET_FoggDam"), ("SM", "SM_FoggDam")],
    "NT_DryRiver":         [("ET", "ET_DryRiver"), ("SM", "SM_DryRiver")],
    "NT_CosmOz_Daly":      [("SM", "SM_CosmOz_Daly")],
}

# Model columns per station (corrected — no SM_VIC / SM_mGV)
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

# ────────────────────────────────────────────────
# METRIC FUNCTIONS (unchanged)
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


def kling_gupta(obs: np.ndarray, sim: np.ndarray) -> tuple:
    if len(obs) < 2:
        return np.nan, np.nan, np.nan, np.nan
    mean_obs = np.mean(obs)
    mean_sim = np.mean(sim)
    std_obs = np.std(obs)
    std_sim = np.std(sim)
    if std_obs == 0 or std_sim == 0:
        return np.nan, np.nan, np.nan, np.nan
    r = np.corrcoef(obs, sim)[0, 1]
    beta = mean_sim / mean_obs if mean_obs != 0 else np.nan
    alpha = std_sim / std_obs if std_obs != 0 else np.nan
    kge = 1 - np.sqrt((r - 1)**2 + (alpha - 1)**2 + (beta - 1)**2)
    return kge, r, alpha, beta


def pbias(obs: np.ndarray, sim: np.ndarray) -> float:
    if len(obs) == 0 or np.sum(obs) == 0:
        return np.nan
    return 100 * np.sum(sim - obs) / np.sum(obs)


def rmse(obs: np.ndarray, sim: np.ndarray) -> float:
    if len(obs) == 0:
        return np.nan
    return np.sqrt(np.mean((sim - obs) ** 2))


def classify_nse(n: float) -> str:
    if np.isnan(n): return "No data"
    if n > 0.75: return "Very good"
    if n > 0.65: return "Good"
    if n > 0.50: return "Satisfactory"
    if n > 0.40: return "Acceptable"
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
# MAIN LOGIC
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

    print("=" * 80)
    print(" MODEL PERFORMANCE ASSESSMENT vs IN-SITU OBSERVATIONS".center(80))
    print(" NSE – KGE – PBIAS – RMSE".center(80))
    print("=" * 80)

    for station_short, display_name in STATION_MAPPING.items():
        print(f"\nStation: {display_name} ({station_short})")
        print("-" * 80)

        # Load in-situ (reference)
        if station_short not in xl_insitu.sheet_names:
            print(f"  In-situ sheet '{station_short}' not found → skipping station")
            continue

        df_insitu = pd.read_excel(xl_insitu, sheet_name=station_short, index_col=None, parse_dates=['date'])
        df_insitu = df_insitu.set_index('date')

        # Load model outputs
        model_sheet = f"{station_short}_daily_1990_2019"
        if model_sheet not in xl_models.sheet_names:
            print(f"  Model sheet '{model_sheet}' not found → skipping station")
            continue

        df_models = pd.read_excel(xl_models, sheet_name=model_sheet, index_col=None, parse_dates=['date'])
        df_models = df_models.set_index('date')

        # Join in-situ + models on date
        df = df_insitu.join(df_models, how="inner").sort_index()

        if df.empty:
            print("  No overlapping dates between in-situ and models → skipping")
            continue

        print(f"  Matching time steps (in-situ + models): {len(df):,d}\n")

        # ─── Process ET and SM variables ────────────────
        for group, insitu_col in INSITU_VARS.get(station_short, []):
            if insitu_col not in df.columns:
                print(f"  {group:6} | In-situ column '{insitu_col}' missing → skipped")
                continue

            # Get available simulation columns for this group (corrected — no SM_VIC/SM_mGV)
            sim_cols = MODEL_COLS.get(station_short, {}).get(group, [])
            if not sim_cols:
                print(f"  {group:6} | No simulation columns found → skipped")
                continue

            obs = df[insitu_col].dropna().to_numpy()
            if len(obs) < 3:
                print(f"  {group:6} | Too few valid in-situ points ({len(obs)}) → skipped")
                continue

            print(f" {group:6} | In-situ '{insitu_col}' vs simulations")
            print("-" * 60)

            for sim_col in sim_cols:
                if sim_col not in df.columns:
                    print(f"    {sim_col:20} missing → skipped")
                    continue

                sub = df[[insitu_col, sim_col]].dropna()
                if len(sub) < 3:
                    print(f"    {sim_col:20} — too few paired points ({len(sub)})")
                    continue

                obs_sub = sub[insitu_col].to_numpy()
                sim_sub = sub[sim_col].to_numpy()

                n = nse(obs_sub, sim_sub)
                k, r, a, b = kling_gupta(obs_sub, sim_sub)
                p = pbias(obs_sub, sim_sub)
                rm = rmse(obs_sub, sim_sub)

                print(f"    {sim_col:20}")
                print(f"      NSE   = {n:8.4f} → {classify_nse(n)}")
                print(f"      KGE   = {k:8.4f} → {classify_kge(k)}")
                print(f"        ├─ r   = {r:6.4f}")
                print(f"        ├─ α   = {a:6.4f}")
                print(f"        └─ β   = {b:6.4f}")
                print(f"      PBIAS = {p:8.4f} % → {classify_pbias(p)}")
                print(f"      RMSE  = {rm:8.4f} → {classify_rmse(rm, obs_sub)}")
                print()

            print()

        # ─── Satellite SM (only for some NT stations) ────────────────
        if station_short in SAT_SM_COLS and xl_sat_sm is not None:
            sat_sheet = station_short
            sat_col = SAT_SM_COLS[station_short]

            if sat_sheet not in xl_sat_sm.sheet_names:
                print(f"  Satellite SM sheet '{sat_sheet}' not found")
            else:
                df_sat_sm = pd.read_excel(xl_sat_sm, sheet_name=sat_sheet, index_col=None, parse_dates=['date'])
                df_sat_sm = df_sat_sm.set_index('date')

                # Join in-situ + satellite SM
                df_sat_join = df_insitu.join(df_sat_sm, how="inner").sort_index()

                if df_sat_join.empty:
                    print("  No overlapping dates for satellite SM → skipped")
                else:
                    print(f"  Satellite SM — matching points: {len(df_sat_join):,d}\n")

                    group = "SM"
                    obs_col = [c for g, c in INSITU_VARS[station_short] if g == "SM"][0]  # SM_FoggDam etc.
                    sim_col = sat_col

                    sub = df_sat_join[[obs_col, sim_col]].dropna()
                    if len(sub) < 3:
                        print(f"  Satellite SM — too few paired points ({len(sub)})")
                    else:
                        obs_sub = sub[obs_col].to_numpy()
                        sim_sub = sub[sim_col].to_numpy()

                        n = nse(obs_sub, sim_sub)
                        k, r, a, b = kling_gupta(obs_sub, sim_sub)
                        p = pbias(obs_sub, sim_sub)
                        rm = rmse(obs_sub, sim_sub)

                        print(f" {group:6} | Satellite '{sim_col}' vs in-situ '{obs_col}'")
                        print(f"   NSE   = {n:8.4f} → {classify_nse(n)}")
                        print(f"   KGE   = {k:8.4f} → {classify_kge(k)}")
                        print(f"     ├─ r   = {r:6.4f}")
                        print(f"     ├─ α   = {a:6.4f}")
                        print(f"     └─ β   = {b:6.4f}")
                        print(f"   PBIAS = {p:8.4f} % → {classify_pbias(p)}")
                        print(f"   RMSE  = {rm:8.4f} → {classify_rmse(rm, obs_sub)}")
                        print()

        print("=" * 80)

    print("Done.\n")


if __name__ == "__main__":
    main()