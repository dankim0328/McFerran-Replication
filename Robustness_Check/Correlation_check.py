import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import warnings

warnings.filterwarnings("ignore")

# 1. Data Load (Absolute path updated)
DATA_PATH = "/Users/dankim/Downloads/SNU/대학원/논문/data/klips/1-27차 release  (Stata)/klips_master_mcferran_v6_timepoverty.csv"
fallback = "/Users/dankim/Downloads/SNU/대학원/논문/data/klips/1-27차 release  (Stata)/klips_master_mcferran_v5.csv"

try:
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {DATA_PATH} successfully. (N={len(df):,})")
except FileNotFoundError:
    try:
        df = pd.read_csv(fallback)
        print(f"Loaded fallback file {fallback} successfully. (N={len(df):,})")
    except FileNotFoundError:
        print("Error: Data file not found. Check the file path.")
        exit()

# 2. Select variables for analysis and drop missing values
# std_log_income: Objective income (standardized log income)
# feeling_poor: Subjective economic dissatisfaction at the individual level (Main IV)
# feeling_poor_h: Subjective economic status at the household level (Appendix IV)
target_cols = ['std_log_income', 'feeling_poor', 'feeling_poor_h']

print("\n" + "="*60)
print("Correlation Analysis: Objective Income vs Subjective Poverty")
print("="*60)

# Extract only the data where all variables exist
df_corr = df[target_cols].dropna()
print(f"Valid observations for correlation analysis: N = {len(df_corr):,}\n")

# Beautify variable names (for output and graphs)
df_corr.columns = ['Objective Income\n(Std Log Income)', 
                   'Personal Feeling Poor\n(Individual IV)', 
                   'Household Feeling Poor\n(Appendix IV)']

# 3. Calculate Correlation Coefficients (Pearson & Spearman)
# Since subjective feeling of poverty is a 1-5 point scale (ordinal variable), it is standard to also look at the Spearman correlation coefficient.
corr_pearson = df_corr.corr(method='pearson')
corr_spearman = df_corr.corr(method='spearman')

print("--- [1] Pearson Correlation Coefficients ---")
print(corr_pearson.round(3))
print("\n--- [2] Spearman Rank Correlation Coefficients ---")
print(corr_spearman.round(3))

# 4. Visualization: Draw Correlation Map (Heatmap)
plt.figure(figsize=(8, 6))

# Generate heatmap (Color theme: Blue-Red, display numerical values)
sns.heatmap(corr_pearson, 
            annot=True,          # Display numerical values
            fmt=".3f",           # Up to 3 decimal places
            cmap="coolwarm",     # From blue (-) to red (+)
            vmin=-1, vmax=1,     # Fix the range of correlation coefficients
            center=0,            # Set 0 to white
            square=True, 
            linewidths=.5,
            annot_kws={"size": 12}) # Font size

plt.title("Correlation Map: Objective vs Subjective Poverty\n(Pearson Correlation)", fontsize=14, pad=15)
plt.xticks(rotation=15, ha='right')
plt.yticks(rotation=0)
plt.tight_layout()

# Save and output the graph
save_path = "correlation_heatmap.png"
plt.savefig(save_path, dpi=300)
print(f"\n✅ Correlation heatmap saved as: {save_path}")

# Display the graph window on Mac environment
plt.show()