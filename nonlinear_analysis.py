"""
Non-linear Analysis: Quadratic Panel TWFE (v5)
==============================================================================
Set A (Main Text): IV = feeling_poor
Set B (Appendix):  IV = feeling_poor_h
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from linearmodels.panel import PanelOLS
import warnings

warnings.filterwarnings("ignore")

DATA_PATH = "klips_master_mcferran_v5.csv"

# =============================================================================
# 1. Setup
# =============================================================================
print("=" * 80)
print("Analysis 3: Non-Linear Quadratic TWFE (Full 27 Waves)")
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
df = df.set_index([id_col, time_col])

print(f"Loaded: {df.shape[0]:,} obs")

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

controls = ["std_log_income", "health", "life_sat"]

def stars(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""

def run_fe(data, dv, predictors, label=""):
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

# =============================================================================
# 3. Quadratic Model (U-Shape Test)
# =============================================================================
for iv, iv_label in ivs.items():
    print(f"\n{'#' * 80}")
    print(f"### {iv_label}")
    print(f"{'#' * 80}")

    sq_term = f"{iv}_sq"
    if iv in df.columns:
        df[sq_term] = df[iv] ** 2

    quad_pred = [iv, sq_term] + controls

    for dv, dv_label in dvs.items():
        if dv not in df.columns:
            print(f"\n  ⚠ DV '{dv}' not found. Skipping.")
            continue

        print(f"\n{'=' * 80}")
        print(f"  {dv_label}  |  IV = {iv}")
        print(f"{'=' * 80}")

        m = run_fe(df, dv, quad_pred, label=dv)
        if m:
            print(f"\n  [Quadratic TWFE] N={m.nobs} | R²(w)={m.rsquared_within:.4f}")
            print(f"  {'Variable':<30} {'Coef':>10} {'SE':>12} {'p-value':>10}")
            print(f"  {'-'*65}")
            for var in m.params.index:
                c = m.params[var]
                s = m.std_errors[var]
                p = m.pvalues[var]
                print(f"  {var:<30} {c:>10.4f}{stars(p):3s} {s:>11.4f} {p:>10.4f}")
            print(f"  {'-'*65}")

            # U-shape interpretation
            b1 = m.params.get(iv, np.nan)
            b2 = m.params.get(sq_term, np.nan)
            p2 = m.pvalues.get(sq_term, np.nan)
            if p2 < 0.05 and b2 != 0:
                vertex = -b1 / (2 * b2)
                shape = "U-shaped" if b2 > 0 else "Inverted-U"
                print(f"  → ✅ Significant quadratic term ({shape}), vertex ≈ {vertex:.2f}")
            else:
                print(f"  → ❌ No significant quadratic term")

print(f"\n{'=' * 80}")
print("Note: *** p<0.01, ** p<0.05, * p<0.1 | Clustered SE (Entity)")
print(f"{'=' * 80}")
