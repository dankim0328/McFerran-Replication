"""
McFerran Replication: Appendix — Panel FE, BE, & Income Quartile Split (v5)
==============================================================================
Robustness Check: IV = feeling_poor_h (Household-Level Subjective Poverty)

Replicating McFerran et al. (2025) Table 2 methodology:
  M6:  Fixed Effects (Full Sample)
  M7:  Between-Effects (Full Sample)
  M8:  FE – 1st Income Quartile (Bottom 25%)
  M9:  FE – 2nd Income Quartile (25-50%)
  M10: FE – 3rd Income Quartile (50-75%)
  M11: FE – 4th Income Quartile (Top 25%)
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from linearmodels.panel import PanelOLS, BetweenOLS
import warnings

warnings.filterwarnings("ignore")

DATA_PATH = "klips_master_mcferran_v5.csv"

# =============================================================================
# 1. Data Loading & Panel Indexing
# =============================================================================
print("=" * 80)
print("APPENDIX: Table 2 (IV = feeling_poor_h)")
print("Robustness Check — Household-Level Subjective Poverty")
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
id_col = 'pid' if 'pid' in df.columns else 'id'

print(f"Loaded: {df.shape[0]:,} obs, {df[id_col].nunique():,} individuals")

# =============================================================================
# 2. Income Quartile Assignment
# =============================================================================
income_col = 'monthly_income'
if income_col not in df.columns:
    for alt in ['income', 'hh_income', 'log_income']:
        if alt in df.columns:
            income_col = alt
            break

print(f"Using '{income_col}' for quartile assignment.")

person_avg_income = df.groupby(id_col)[income_col].mean()
quartile_labels = pd.qcut(person_avg_income, q=4, labels=[1, 2, 3, 4])
df['income_quartile'] = df[id_col].map(quartile_labels)

print(f"\nIncome Quartile Distribution (person-level):")
print(person_avg_income.groupby(quartile_labels).agg(['count', 'min', 'max', 'mean']).to_string())

df = df.set_index([id_col, time_col])

# =============================================================================
# 3. Variable Definitions
# =============================================================================
iv = "feeling_poor_h"

dvs = {
    "dv1_social_sat": "DV1: Social Satisfaction",
    "p_freq":         "DV2: Parents Meeting Freq",
    "i_freq":         "DV3: In-laws Meeting Freq",
    "c_freq":         "DV4: Children Meeting Freq",
}

fe_controls = ["std_log_income", "health", "life_sat"]
be_controls = ["std_log_income", "health", "life_sat", "age", "gender"]

def stars(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""

# =============================================================================
# 4. Model Runner Functions
# =============================================================================
def run_fe(data, dv, iv_name, ctrls, label=""):
    predictors = [iv_name] + ctrls
    needed = [dv] + predictors
    if not all(c in data.columns for c in needed):
        missing = [c for c in needed if c not in data.columns]
        print(f"  [{label}] Missing: {missing}")
        return None
    subset = data[needed].dropna()
    if len(subset) < 100:
        print(f"  [{label}] Only {len(subset)} obs. Skipping.")
        return None
    Y = subset[dv]
    X = sm.add_constant(subset[predictors])
    mod = PanelOLS(Y, X, entity_effects=True, time_effects=True, drop_absorbed=True)
    return mod.fit(cov_type='clustered', cluster_entity=True)


def run_be(data, dv, iv_name, ctrls, label=""):
    predictors = [iv_name] + ctrls
    needed = [dv] + predictors
    if not all(c in data.columns for c in needed):
        missing = [c for c in needed if c not in data.columns]
        print(f"  [{label}] Missing: {missing}")
        return None
    subset = data[needed].dropna()
    if len(subset) < 100:
        print(f"  [{label}] Only {len(subset)} obs. Skipping.")
        return None
    Y = subset[dv]
    X = sm.add_constant(subset[predictors])
    mod = BetweenOLS(Y, X)
    return mod.fit()


def print_model(res, label, model_name):
    if res is None:
        print(f"  [{model_name}] → Skipped\n")
        return
    n = int(res.nobs) if hasattr(res, 'nobs') else "N/A"
    r2 = res.rsquared_within if hasattr(res, 'rsquared_within') else (res.rsquared if hasattr(res, 'rsquared') else np.nan)
    r2_label = "R²(w)" if hasattr(res, 'rsquared_within') else "R²"

    print(f"\n  [{model_name}] {label} | N={n} | {r2_label}={r2:.4f}")
    print(f"  {'Variable':<20} {'Coef':>10} {'SE':>12} {'p-value':>10}")
    print(f"  {'-'*55}")
    for var in res.params.index:
        c = res.params[var]
        s = res.std_errors[var]
        p = res.pvalues[var]
        print(f"  {var:<20} {c:>10.4f}{stars(p):3s} {s:>11.4f} {p:>10.4f}")
    print(f"  {'-'*55}")

# =============================================================================
# 5. Run All 6 Models for Each DV
# =============================================================================
for dv, dv_label in dvs.items():
    if dv not in df.columns:
        print(f"\n  ⚠ DV '{dv}' not found. Skipping.")
        continue

    print(f"\n{'#' * 80}")
    print(f"### {dv_label}  (IV = {iv})")
    print(f"{'#' * 80}")

    # M6: Fixed Effects – Full Sample
    res6 = run_fe(df, dv, iv, fe_controls, label="M6-FE-Full")
    print_model(res6, "Fixed Effects – Full Sample", "M6")

    # M7: Between-Effects – Full Sample
    res7 = run_be(df, dv, iv, be_controls, label="M7-BE-Full")
    print_model(res7, "Between-Effects – Full Sample", "M7")

    # M8–M11: Fixed Effects by Income Quartile
    for q in [1, 2, 3, 4]:
        q_label = {1: "Bottom 25%", 2: "25-50%", 3: "50-75%", 4: "Top 25%"}[q]
        model_num = q + 7
        df_q = df[df['income_quartile'] == q]
        q_controls = ["health", "life_sat"]
        res_q = run_fe(df_q, dv, iv, q_controls, label=f"M{model_num}-Q{q}")
        print_model(res_q, f"FE – {q_label} (Q{q})", f"M{model_num}")

# =============================================================================
# 6. Summary Comparison Table
# =============================================================================
print(f"\n{'=' * 80}")
print(f"SUMMARY: {iv} coefficient across all models & DVs")
print(f"{'=' * 80}\n")

header = f"{'DV':<20}"
model_labels = ["M6(FE)", "M7(BE)", "M8(Q1)", "M9(Q2)", "M10(Q3)", "M11(Q4)"]
for ml in model_labels:
    header += f" {ml:>12}"
print(header)
print("-" * (20 + 13 * len(model_labels)))

for dv, dv_label in dvs.items():
    if dv not in df.columns:
        continue
    row = f"{dv:<20}"

    res6 = run_fe(df, dv, iv, fe_controls, label="summary")
    if res6 and iv in res6.params.index:
        c = res6.params[iv]; p = res6.pvalues[iv]
        row += f" {c:>8.4f}{stars(p):3s}"
    else:
        row += f" {'N/A':>12}"

    res7 = run_be(df, dv, iv, be_controls, label="summary")
    if res7 and iv in res7.params.index:
        c = res7.params[iv]; p = res7.pvalues[iv]
        row += f" {c:>8.4f}{stars(p):3s}"
    else:
        row += f" {'N/A':>12}"

    for q in [1, 2, 3, 4]:
        df_q = df[df['income_quartile'] == q]
        q_controls = ["health", "life_sat"]
        res_q = run_fe(df_q, dv, iv, q_controls, label="summary")
        if res_q and iv in res_q.params.index:
            c = res_q.params[iv]; p = res_q.pvalues[iv]
            row += f" {c:>8.4f}{stars(p):3s}"
        else:
            row += f" {'N/A':>12}"
    print(row)

print(f"\n{'=' * 80}")
print("Note: *** p<0.01, ** p<0.05, * p<0.1")
print("  M6=Fixed Effects (Full), M7=Between Effects (Full)")
print("  M8-M11=Fixed Effects by Income Quartile (Q1=Bottom 25%, Q4=Top 25%)")
print(f"{'=' * 80}")