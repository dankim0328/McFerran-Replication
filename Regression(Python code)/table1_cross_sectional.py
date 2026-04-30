"""
McFerran Replication: Table 1 — Cross-sectional Hierarchical OLS (v5)
==============================================================================
Set A (Main Text): IV = feeling_poor
Set B (Appendix):  IV = feeling_poor_h
"""

import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
import warnings

warnings.filterwarnings("ignore")

DATA_PATH = "klips_master_mcferran_v5.csv"

# =============================================================================
# 1. Data Loading & Filtering (Year 2024 only)
# =============================================================================
print("=" * 80)
print("Table 1: Cross-sectional Hierarchical OLS (Year 2024)")
print("=" * 80)

try:
    df = pd.read_csv(DATA_PATH)
except FileNotFoundError:
    fallback = "/Users/dankim/Downloads/SNU/대학원/논문/data/klips/1-27차 release  (Stata)/klips_master_mcferran_v5.csv"
    try:
        df = pd.read_csv(fallback)
    except FileNotFoundError:
        print(f"Error: Could not find {DATA_PATH} or {fallback}.")
        exit()

time_col = 'year' if 'year' in df.columns else 'wave'
if time_col == 'year':
    df24 = df[df[time_col] == 2024].copy()
else:
    df24 = df[df[time_col] == df[time_col].max()].copy()

print(f"\n2024 observations: {len(df24):,}")

# =============================================================================
# 2. Definitions
# =============================================================================
ivs = {
    "feeling_poor":   "SET A (Main Text): IV = feeling_poor",
    "feeling_poor_h": "SET B (Appendix):  IV = feeling_poor_h",
}

dvs = {
    "dv1_social_sat": "DV1: Social Satisfaction",
    "p_freq":         "DV2: Parents Meeting Freq",
    "i_freq":         "DV3: In-laws Meeting Freq",
    "c_freq":         "DV4: Children Meeting Freq",
}

def get_models(iv):
    """Stepwise model specs: M1→M4. No is_metro."""
    return {
        "M1": [iv, "std_log_income"],
        "M2": [iv, "std_log_income", "age", "gender"],
        "M3": [iv, "std_log_income", "age", "gender", "health"],
        "M4": [iv, "std_log_income", "age", "gender", "health", "life_sat"],
    }

def run_ols(data, dv, predictors, label=""):
    vars_needed = [dv] + predictors
    if not all(v in data.columns for v in vars_needed):
        missing = [v for v in vars_needed if v not in data.columns]
        print(f"  ⚠ [{label}] Missing: {missing}")
        return None
    df_reg = data[vars_needed].dropna()
    if len(df_reg) < 30:
        print(f"  ⚠ [{label}] Only {len(df_reg)} obs. Skipping.")
        return None
    formula = f"{dv} ~ " + " + ".join(predictors)
    return smf.ols(formula=formula, data=df_reg).fit(cov_type="HC3")

# =============================================================================
# 3. Run All Models
# =============================================================================
for iv, iv_label in ivs.items():
    print(f"\n{'#' * 80}")
    print(f"### {iv_label}")
    print(f"{'#' * 80}")

    models_spec = get_models(iv)

    for dv, dv_label in dvs.items():
        if dv not in df24.columns:
            print(f"\n  ⚠ DV '{dv}' not found. Skipping.")
            continue

        print(f"\n{'=' * 80}")
        print(f"  {dv_label}  |  IV = {iv}")
        print(f"{'=' * 80}")

        for mname, predictors in models_spec.items():
            res = run_ols(df24, dv, predictors, label=f"{iv}_{dv}_{mname}")
            if res:
                print(f"\n  [{mname}] N={int(res.nobs):,} | R²={res.rsquared:.4f}")
                print(f"  {'Variable':<20} {'Coef':>10} {'Robust SE':>12} {'p-value':>10}")
                print(f"  {'-'*55}")
                for var in res.params.index:
                    coef = res.params[var]
                    se   = res.bse[var]
                    p    = res.pvalues[var]
                    stars = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""
                    print(f"  {var:<20} {coef:>10.4f}{stars:3s} {se:>11.4f} {p:>10.4f}")
                print(f"  {'-'*55}")

print(f"\n{'=' * 80}")
print("Note: *** p<0.01, ** p<0.05, * p<0.1 | Robust SE (HC3)")
print(f"{'=' * 80}")
