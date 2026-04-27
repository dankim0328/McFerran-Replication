"""
McFerran Replication: Table 1 — Cross-sectional Hierarchical OLS (KLIPS 2024)
==============================================================================
Stepwise regression adding controls to test stability of feeling_poor effect.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
import warnings

warnings.filterwarnings("ignore")

DATA_PATH = "/Users/dankim/Downloads/SNU/대학원/논문/data/klips/1-27차 release  (Stata)/klips_master_mcferran_v4.csv"

# =============================================================================
# 1. Data Loading & Filtering (Year 2024 only)
# =============================================================================
print("=" * 70)
print("Table 1: Cross-sectional Hierarchical OLS (Year 2024)")
print("=" * 70)

df = pd.read_csv(DATA_PATH)
df24 = df[df["year"] == 2024].copy()
print(f"\n2024 observations: {len(df24):,}")
print(f"Unique individuals: {df24['pid'].nunique():,}")

# Variable availability
key_vars = ["feeling_poor", "std_log_income", "age", "gender",
            "feeling_poor_h", "health", "life_sat",
            "dv1_social_sat", "dv3_family_freq"]
print(f"\n{'─' * 50}")
for v in key_vars:
    if v in df24.columns:
        print(f"  {v:20s} → {df24[v].notna().sum():>6,} obs")
    else:
        print(f"  {v:20s} → ⚠ NOT FOUND")

# =============================================================================
# 2. Model Specifications (Hierarchical / Stepwise)
# =============================================================================
models_spec = {
    "M1": ["feeling_poor", "std_log_income"],
    "M2": ["feeling_poor", "std_log_income", "age", "gender"],
    "M3": ["feeling_poor", "std_log_income", "age", "gender", "feeling_poor_h"],
    "M4": ["feeling_poor", "std_log_income", "age", "gender", "feeling_poor_h", "health"],
    "M5": ["feeling_poor", "std_log_income", "age", "gender", "feeling_poor_h", "health", "life_sat"],
}

dvs = {
    "dv1_social_sat":  "DV1: Social Satisfaction",
    "dv3_family_freq": "DV3: Family Meeting Freq",
}


def run_ols(data, dv, predictors, label=""):
    """OLS with HC3 robust standard errors."""
    vars_needed = [dv] + predictors
    vars_avail = [v for v in vars_needed if v in data.columns]
    if len(vars_avail) < len(vars_needed):
        missing = set(vars_needed) - set(vars_avail)
        print(f"  ⚠ [{label}] Missing: {missing}")
        return None

    df_reg = data[vars_needed].dropna()
    if len(df_reg) < 30:
        print(f"  ⚠ [{label}] Only {len(df_reg)} obs. Skipping.")
        return None

    X = sm.add_constant(df_reg[predictors])
    y = df_reg[dv]
    result = sm.OLS(y, X).fit(cov_type="HC3")
    return result


# =============================================================================
# 3. Run All Models
# =============================================================================
all_results = {}

for dv, dv_label in dvs.items():
    print(f"\n{'=' * 70}")
    print(f"  {dv_label}")
    print(f"{'=' * 70}")

    for mname, predictors in models_spec.items():
        m = run_ols(df24, dv, predictors, label=f"{dv}_{mname}")
        all_results[(dv, mname)] = m

        if m:
            fp_b = m.params.get("feeling_poor", np.nan)
            fp_se = m.bse.get("feeling_poor", np.nan)
            fp_p = m.pvalues.get("feeling_poor", np.nan)
            stars = "***" if fp_p < 0.01 else "**" if fp_p < 0.05 else "*" if fp_p < 0.1 else ""
            print(f"  {mname}: N={int(m.nobs):,}  R²={m.rsquared:.4f}  "
                  f"feeling_poor β={fp_b:.4f}{stars} (SE={fp_se:.4f}, p={fp_p:.4f})")

# =============================================================================
# 4. Summary Table (Paper-ready format)
# =============================================================================
for dv, dv_label in dvs.items():
    print(f"\n{'=' * 70}")
    print(f"TABLE 1: {dv_label}")
    print(f"{'=' * 70}")

    # Collect all predictor names
    all_preds = ["const"] + models_spec["M5"]
    model_names = list(models_spec.keys())

    # Header
    header = f"{'Variable':20s}"
    for mn in model_names:
        header += f"  {'(' + mn + ')':>14s}"
    print(header)
    print("─" * (20 + 16 * len(model_names)))

    # Rows
    for pred in all_preds:
        row_coef = f"{pred:20s}"
        row_se = f"{'':20s}"
        for mn in model_names:
            m = all_results.get((dv, mn))
            if m and pred in m.params.index:
                b = m.params[pred]
                se = m.bse[pred]
                p = m.pvalues[pred]
                stars = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""
                row_coef += f"  {b:>10.4f}{stars:3s}"
                row_se += f"  {'(' + f'{se:.4f}' + ')':>13s}"
            else:
                row_coef += f"  {'':>13s}"
                row_se += f"  {'':>13s}"
        print(row_coef)
        print(row_se)

    # Footer: N and R²
    print("─" * (20 + 16 * len(model_names)))
    row_n = f"{'N':20s}"
    row_r2 = f"{'R²':20s}"
    for mn in model_names:
        m = all_results.get((dv, mn))
        if m:
            row_n += f"  {int(m.nobs):>13,}"
            row_r2 += f"  {m.rsquared:>13.4f}"
        else:
            row_n += f"  {'':>13s}"
            row_r2 += f"  {'':>13s}"
    print(row_n)
    print(row_r2)

# =============================================================================
# 5. Interpretation
# =============================================================================
print(f"\n{'=' * 70}")
print("INTERPRETATION: Stability of 'feeling_poor' coefficient")
print(f"{'=' * 70}")

for dv, dv_label in dvs.items():
    print(f"\n▶ {dv_label}")
    coefs = []
    for mn in models_spec:
        m = all_results.get((dv, mn))
        if m and "feeling_poor" in m.params.index:
            b = m.params["feeling_poor"]
            p = m.pvalues["feeling_poor"]
            coefs.append((mn, b, p))

    if coefs:
        first_b = coefs[0][1]
        last_b = coefs[-1][1]
        all_sig = all(p < 0.05 for _, _, p in coefs)
        change_pct = abs((last_b - first_b) / first_b * 100) if first_b != 0 else 0

        print(f"  M1 β = {first_b:.4f} → M5 β = {last_b:.4f}  (change: {change_pct:.1f}%)")
        if all_sig and change_pct < 30:
            print(f"  → ✅ Robust: feeling_poor remains significant and stable across all models")
        elif all_sig:
            print(f"  → ⚠️ Significant but coefficient changes substantially ({change_pct:.1f}%)")
        else:
            nonsig = [mn for mn, _, p in coefs if p >= 0.05]
            print(f"  → ❌ Not robust: loses significance in {nonsig}")

print(f"\n{'=' * 70}")
print("Note: *** p<0.01, ** p<0.05, * p<0.1 | Robust SE (HC3)")
print(f"{'=' * 70}")
