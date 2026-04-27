"""
McFerran Replication: Panel FE Analysis (KLIPS v4.2)
=====================================================
Hypothesis: Subjective Poverty → Reduced Socializing
Data: klips_master_mcferran_v4.csv (Waves 1-27, N≈417k)
"""

import pandas as pd
import numpy as np
from linearmodels.panel import PanelOLS
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import warnings
import os

warnings.filterwarnings("ignore")

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = "/Users/dankim/Downloads/SNU/대학원/논문/data/klips/1-27차 release  (Stata)/klips_master_mcferran_v4.csv"

# =============================================================================
# 1. Data Loading & Indexing
# =============================================================================
print("=" * 70)
print("McFerran Replication: Two-Way Fixed Effects (v4.2)")
print("=" * 70)

df = pd.read_csv(DATA_PATH)
print(f"\nLoaded: {df.shape[0]:,} obs, {df.shape[1]} vars")
print(f"Unique pid: {df['pid'].nunique():,}")
print(f"Years: {int(df['year'].min())} – {int(df['year'].max())}")

df["pid"] = df["pid"].astype(int)
df["year"] = df["year"].astype(int)
df = df.set_index(["pid", "year"])

# Variable definitions
iv_main = "feeling_poor"
iv_alt = "feeling_poor_h"
# age 제거: Entity FE(birth_year 고정) + Time FE(year)와 완벽 공선성
# is_metro 제거: 개인 내 변동(within-variation)이 거의 없음
controls = ["std_log_income", "health", "life_sat"]

dvs = {
    "dv1_social_sat":  "DV1: Social Satisfaction (Attitude)",
    "dv3_family_freq": "DV3: Family Meeting Freq (Behavior)",
}

# Data check
print(f"\n{'─' * 70}")
print("Variable Availability:")
print(f"{'─' * 70}")
for v in [iv_main, iv_alt] + list(dvs.keys()) + controls:
    if v in df.columns:
        print(f"  {v:25s} → {df[v].notna().sum():>10,} obs")
    else:
        print(f"  {v:25s} → ⚠ NOT FOUND")

# =============================================================================
# 2. Panel FE Helper
# =============================================================================
def run_fe(data, dv, iv, ctrls, label=""):
    needed = [dv, iv] + ctrls
    needed = [v for v in needed if v in data.columns]
    df_reg = data[needed].dropna()

    if len(df_reg) < 100:
        print(f"  ⚠ [{label}] {len(df_reg)} obs — skipping.")
        return None

    ctrl_str = " + ".join(ctrls)
    formula = f"{dv} ~ 1 + {iv} + {ctrl_str} + EntityEffects + TimeEffects"

    try:
        result = PanelOLS.from_formula(formula, data=df_reg, drop_absorbed=True).fit(
            cov_type="clustered", cluster_entity=True
        )
        return result
    except Exception as e:
        print(f"  ⚠ [{label}] {e}")
        return None


def print_result(m, iv_name, label):
    if m is None:
        return
    b = m.params[iv_name]
    se = m.std_errors[iv_name]
    t = m.tstats[iv_name]
    p = m.pvalues[iv_name]
    s = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""

    print(f"  [{label}]  N={int(m.nobs):,}  R²(w)={m.rsquared_within:.4f}")
    print(f"    {iv_name}: β={b:.4f}{s}  SE={se:.4f}  t={t:.3f}  p={p:.4f}")

    if b < 0 and p < 0.05:
        print(f"    → ✅ Supports McFerran (significant negative)")
    elif b < 0 and p < 0.1:
        print(f"    → ⚠️ Weak support (marginally significant)")
    elif b < 0:
        print(f"    → ❌ Negative but not significant")
    else:
        print(f"    → ❌ Does not support (positive/zero)")


# =============================================================================
# 3. Model 1 & 2: Main Effect (feeling_poor)
# =============================================================================
print(f"\n{'=' * 70}")
print("MAIN ANALYSIS: feeling_poor → Socializing")
print(f"Controls: {controls}")
print(f"{'=' * 70}")

results = {}
for dv, label in dvs.items():
    print(f"\n▶ {label}")
    m = run_fe(df, dv, iv_main, controls, label=dv)
    results[f"{dv}_main"] = m
    print_result(m, iv_main, "Main IV")

# =============================================================================
# 4. Model 3 & 4: Alt IV (feeling_poor_h)
# =============================================================================
if iv_alt in df.columns and df[iv_alt].notna().sum() > 100:
    print(f"\n{'=' * 70}")
    print("ROBUSTNESS: feeling_poor_h → Socializing")
    print(f"{'=' * 70}")

    for dv, label in dvs.items():
        print(f"\n▶ {label}")
        m = run_fe(df, dv, iv_alt, controls, label=f"{dv}_alt")
        results[f"{dv}_alt"] = m
        print_result(m, iv_alt, "Alt IV")

# =============================================================================
# 5. Moderation: feeling_poor_h × std_log_income
# =============================================================================
print(f"\n{'=' * 70}")
print("MODERATION: feeling_poor_h × std_log_income")
print("Does feeling poor hurt more when objectively poor?")
print(f"{'=' * 70}")

if iv_alt in df.columns and "std_log_income" in df.columns:
    df["fp_h_x_income"] = df[iv_alt] * df["std_log_income"]
    mod_controls = controls + ["fp_h_x_income"]

    for dv, label in dvs.items():
        print(f"\n▶ {label}")
        m = run_fe(df, dv, iv_alt, mod_controls, label=f"{dv}_mod")
        results[f"{dv}_mod"] = m

        if m:
            print_result(m, iv_alt, "Main Effect (feeling_poor_h)")
            if "fp_h_x_income" in m.params.index:
                b_int = m.params["fp_h_x_income"]
                p_int = m.pvalues["fp_h_x_income"]
                s_int = "***" if p_int < 0.01 else "**" if p_int < 0.05 else "*" if p_int < 0.1 else ""
                print(f"    fp_h×income: β={b_int:.4f}{s_int}  p={p_int:.4f}")
                if b_int > 0 and p_int < 0.05:
                    print(f"    → ✅ Higher income buffers the negative effect")
                elif b_int < 0 and p_int < 0.05:
                    print(f"    → ⚠️ Higher income amplifies the negative effect")
                else:
                    print(f"    → Interaction not significant")

# =============================================================================
# 6. Summary Table
# =============================================================================
print(f"\n{'=' * 70}")
print("SUMMARY TABLE")
print(f"{'=' * 70}\n")

rows = []
for key, m in results.items():
    if m is None:
        continue
    # Figure out which IV to report
    if "_alt" in key:
        iv_r = iv_alt
    elif "_mod" in key:
        iv_r = iv_alt
    else:
        iv_r = iv_main

    if iv_r in m.params.index:
        p = m.pvalues[iv_r]
        rows.append({
            "Model": key, "Term": iv_r,
            "β": m.params[iv_r], "SE": m.std_errors[iv_r],
            "t": m.tstats[iv_r], "p": p,
            "sig": "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "",
            "N": int(m.nobs), "R²(w)": m.rsquared_within,
        })

    if "_mod" in key and "fp_h_x_income" in m.params.index:
        p = m.pvalues["fp_h_x_income"]
        rows.append({
            "Model": key, "Term": "fp_h×income",
            "β": m.params["fp_h_x_income"], "SE": m.std_errors["fp_h_x_income"],
            "t": m.tstats["fp_h_x_income"], "p": p,
            "sig": "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "",
            "N": int(m.nobs), "R²(w)": m.rsquared_within,
        })

if rows:
    df_table = pd.DataFrame(rows)
    df_disp = df_table.copy()
    for c in ["β", "SE", "R²(w)"]:
        df_disp[c] = df_disp[c].map("{:.4f}".format)
    df_disp["t"] = df_disp["t"].map("{:.3f}".format)
    df_disp["p"] = df_disp["p"].map("{:.4f}".format)
    df_disp["N"] = df_disp["N"].map("{:,}".format)
    print(df_disp.to_string(index=False))

# =============================================================================
# 7. Visualization: Coefficient Plot
# =============================================================================
print(f"\n{'─' * 70}")
print("Generating plots...")

# --- (a) Coefficient Plot ---
fig, ax = plt.subplots(figsize=(10, 5))
plot_data = []
for key, m in results.items():
    if m is None or "_mod" in key:
        continue
    iv_r = iv_alt if "_alt" in key else iv_main
    if iv_r in m.params.index:
        plot_data.append({
            "model": key.replace("_", "\n"),
            "coef": m.params[iv_r],
            "ci_lo": m.params[iv_r] - 1.96 * m.std_errors[iv_r],
            "ci_hi": m.params[iv_r] + 1.96 * m.std_errors[iv_r],
        })

if plot_data:
    pdf = pd.DataFrame(plot_data)
    y_pos = range(len(pdf))
    ax.barh(y_pos, pdf["coef"], color=["#e74c3c" if c < 0 else "#2ecc71" for c in pdf["coef"]],
            alpha=0.7, height=0.5)
    ax.errorbar(pdf["coef"], y_pos,
                xerr=[pdf["coef"] - pdf["ci_lo"], pdf["ci_hi"] - pdf["coef"]],
                fmt="none", color="black", capsize=4, linewidth=1.5)
    ax.axvline(x=0, color="gray", linestyle="--", linewidth=0.8)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(pdf["model"], fontsize=10)
    ax.set_xlabel("Coefficient (β) with 95% CI", fontsize=11)
    ax.set_title("Effect of Feeling Poor on Socializing\n(Two-Way Fixed Effects, Clustered SE)",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()

    coef_path = os.path.join(OUTPUT_DIR, "coefficient_plot.png")
    fig.savefig(coef_path, dpi=150)
    print(f"  ✅ Coefficient plot → {coef_path}")
    plt.close()

# --- (b) Interaction Plot ---
mod_model = results.get("dv1_social_sat_mod")
if mod_model and iv_alt in mod_model.params.index and "fp_h_x_income" in mod_model.params.index:
    fig2, ax2 = plt.subplots(figsize=(8, 5))

    b_fp = mod_model.params[iv_alt]
    b_int = mod_model.params["fp_h_x_income"]

    income_levels = np.linspace(-2, 2, 100)  # std_log_income range
    marginal_effect = b_fp + b_int * income_levels

    ax2.plot(income_levels, marginal_effect, color="#3498db", linewidth=2.5)
    ax2.axhline(y=0, color="gray", linestyle="--", linewidth=0.8)
    ax2.fill_between(income_levels, marginal_effect, 0, alpha=0.1, color="#3498db")
    ax2.set_xlabel("Standardized Log Income (std_log_income)", fontsize=11)
    ax2.set_ylabel("Marginal Effect of Feeling Poor on Social Satisfaction", fontsize=11)
    ax2.set_title("Interaction: Feeling Poor × Objective Income\n(How income moderates the poverty-socializing link)",
                  fontsize=13, fontweight="bold")
    plt.tight_layout()

    int_path = os.path.join(OUTPUT_DIR, "interaction_plot.png")
    fig2.savefig(int_path, dpi=150)
    print(f"  ✅ Interaction plot → {int_path}")
    plt.close()

print(f"\n{'=' * 70}")
print("Analysis Complete!")
print(f"{'=' * 70}")
