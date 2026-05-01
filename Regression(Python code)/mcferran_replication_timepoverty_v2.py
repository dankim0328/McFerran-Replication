"""
McFerran Replication & EXTENSION (v3 - Social Satisfaction Focused)
==============================================================================
Focusing exclusively on 'dv1_social_sat' due to low R^2 in behavioral frequency DVs.
Includes 'total_work_hr' to control for Time Poverty, with missing values
(unemployed/retired) properly filled with 0 to prevent sample selection bias.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
from linearmodels.panel import PanelOLS, BetweenOLS
import warnings

warnings.filterwarnings("ignore")

DATA_PATH = "klips_master_mcferran_v6_timepoverty.csv"
FALLBACK_PATH = "/Users/dankim/Downloads/SNU/대학원/논문/data/klips/1-27차 release  (Stata)/klips_master_mcferran_v6_timepoverty.csv"

def stars(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""

def print_model(res, label, model_name):
    """Print full coefficient table for a model result."""
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
        s = res.std_errors[var] if hasattr(res, 'std_errors') else res.bse[var]
        p = res.pvalues[var]
        print(f"  {var:<20} {c:>10.4f}{stars(p):3s} {s:>11.4f} {p:>10.4f}")
    print(f"  {'-'*55}")

# =============================================================================
# 0. Data Loading & Bias Fix
# =============================================================================
print("=" * 80)
print("Loading KLIPS V6 Data & Fixing Time Poverty N/A...")
print("=" * 80)

try:
    df = pd.read_csv(DATA_PATH)
except FileNotFoundError:
    try:
        df = pd.read_csv(FALLBACK_PATH)
    except FileNotFoundError:
        print(f"Error: Could not find data.")
        exit()

# 🚨 [Core Fix] Fill missing working hours for the unemployed/retired with 0 to prevent sample attrition (Selection Bias)
if 'total_work_hr' in df.columns:
    df['total_work_hr'] = df['total_work_hr'].fillna(0)

time_col = 'year' if 'year' in df.columns else 'wave'
id_col = 'pid' if 'pid' in df.columns else 'id'

# DV is strictly fixed to 1 variable: Social Satisfaction
dv = "dv1_social_sat"

# =============================================================================
# PART 1: Table 1 — Cross-sectional Hierarchical OLS (Year 2024)
# =============================================================================
print("\n\n" + "=" * 80)
print("PART 1: Cross-sectional Hierarchical OLS (Year 2024) - Social Satisfaction")
print("=" * 80)

df24 = df[df[time_col] == 2024].copy()

ivs = {
    "feeling_poor":   "Main Text IV (Individual)",
    "feeling_poor_h": "Appendix IV (Household)"
}

def get_ols_models(iv):
    """M1~M4: Baseline / M5: Time Poverty Extension"""
    return {
        "M1": [iv, "std_log_income"],
        "M2": [iv, "std_log_income", "age", "gender"],
        "M3": [iv, "std_log_income", "age", "gender", "health"],
        "M4": [iv, "std_log_income", "age", "gender", "health", "life_sat"],
        "M5": [iv, "std_log_income", "age", "gender", "health", "life_sat", "total_work_hr"],
    }

def run_ols(data, dep_var, predictors, label=""):
    vars_needed = [dep_var] + predictors
    if not all(v in data.columns for v in vars_needed): return None
    df_reg = data[vars_needed].dropna()
    if len(df_reg) < 30: return None
    formula = f"{dep_var} ~ " + " + ".join(predictors)
    return smf.ols(formula=formula, data=df_reg).fit(cov_type="HC3")

for iv, iv_label in ivs.items():
    print(f"\n{'#' * 80}")
    print(f"### IV = {iv} ({iv_label})")
    print(f"{'#' * 80}")
    models_spec = get_ols_models(iv)
    
    for mname, predictors in models_spec.items():
        res = run_ols(df24, dv, predictors, label=f"{iv}_{dv}_{mname}")
        if res:
            print(f"\n  [{mname}] N={int(res.nobs):,} | R²={res.rsquared:.4f}")
            print(f"  {'Variable':<20} {'Coef':>10} {'Robust SE':>12} {'p-value':>10}")
            for var in res.params.index:
                coef = res.params[var]; se = res.bse[var]; p = res.pvalues[var]
                print(f"  {var:<20} {coef:>10.4f}{stars(p):3s} {se:>11.4f} {p:>10.4f}")

# =============================================================================
# PART 2: Table 2 — Panel FE, BE, & Income Quartile Split
# =============================================================================
print("\n\n" + "=" * 80)
print("PART 2: Panel FE / BE / Quartile Analysis (27 Waves) - Social Satisfaction")
print("=" * 80)

df_panel = df.copy()
income_col = 'monthly_income'
person_avg_income = df_panel.groupby(id_col)[income_col].mean()
quartile_labels = pd.qcut(person_avg_income, q=4, labels=[1, 2, 3, 4])
df_panel['income_quartile'] = df_panel[id_col].map(quartile_labels)
df_panel = df_panel.set_index([id_col, time_col])

# Controls with Time Poverty included
fe_controls = ["std_log_income", "health", "life_sat", "total_work_hr"]
be_controls = ["std_log_income", "health", "life_sat", "age", "gender", "total_work_hr"]
q_controls  = ["health", "life_sat", "total_work_hr"] # std_log_income excluded in quartiles

def run_fe(data, dep_var, iv_name, ctrls):
    predictors = [iv_name] + ctrls
    needed = [dep_var] + predictors
    if not all(c in data.columns for c in needed): return None
    subset = data[needed].dropna()
    if len(subset) < 100: return None
    Y = subset[dep_var]
    X = sm.add_constant(subset[predictors])
    mod = PanelOLS(Y, X, entity_effects=True, time_effects=True, drop_absorbed=True)
    return mod.fit(cov_type='clustered', cluster_entity=True)

def run_be(data, dep_var, iv_name, ctrls):
    predictors = [iv_name] + ctrls
    needed = [dep_var] + predictors
    if not all(c in data.columns for c in needed): return None
    subset = data[needed].dropna()
    if len(subset) < 100: return None
    Y = subset[dep_var]
    X = sm.add_constant(subset[predictors])
    mod = BetweenOLS(Y, X)
    return mod.fit()

for iv, iv_label in ivs.items():
    print(f"\n{'#' * 80}")
    print(f"### IV = {iv} ({iv_label})")
    print(f"{'#' * 80}")

    # M6: FE
    res6 = run_fe(df_panel, dv, iv, fe_controls)
    print_model(res6, "Fixed Effects – Full Sample", "M6")

    # M7: BE
    res7 = run_be(df_panel, dv, iv, be_controls)
    print_model(res7, "Between-Effects – Full Sample", "M7")

    # M8–M11: Quartiles
    for q in [1, 2, 3, 4]:
        q_label = {1: "Bottom 25%", 2: "25-50%", 3: "50-75%", 4: "Top 25%"}[q]
        model_num = q + 7  
        df_q = df_panel[df_panel['income_quartile'] == q]
        res_q = run_fe(df_q, dv, iv, q_controls)
        print_model(res_q, f"FE – {q_label} (Q{q})", f"M{model_num}")

# =============================================================================
# SUMMARY TABLE
# =============================================================================
print(f"\n{'=' * 80}")
print("SUMMARY: Coefficient of Subjective Poverty on SOCIAL SATISFACTION")
print(f"{'=' * 80}\n")

header = f"{'IV Type':<18}"
model_labels = ["M6(FE)", "M7(BE)", "M8(Q1)", "M9(Q2)", "M10(Q3)", "M11(Q4)"]
for ml in model_labels: header += f" {ml:>12}"
print(header)
print("-" * (18 + 13 * len(model_labels)))

for iv in ivs.keys():
    row = f"{iv:<18}"
    
    res6 = run_fe(df_panel, dv, iv, fe_controls)
    row += f" {res6.params[iv]:>8.4f}{stars(res6.pvalues[iv]):3s}" if res6 else f" {'N/A':>12}"

    res7 = run_be(df_panel, dv, iv, be_controls)
    row += f" {res7.params[iv]:>8.4f}{stars(res7.pvalues[iv]):3s}" if res7 else f" {'N/A':>12}"

    for q in [1, 2, 3, 4]:
        df_q = df_panel[df_panel['income_quartile'] == q]
        res_q = run_fe(df_q, dv, iv, q_controls)
        row += f" {res_q.params[iv]:>8.4f}{stars(res_q.pvalues[iv]):3s}" if res_q else f" {'N/A':>12}"

    print(row)