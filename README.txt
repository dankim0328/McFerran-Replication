=============================================================================
Project: McFerran Replication & Extension using KLIPS Data
=============================================================================

# Description
This repository contains the data cleaning, analysis, and robustness check scripts 
for the replication and extension of McFerran's research. The project utilizes the 
Korean Labor and Income Panel Study (KLIPS) dataset (Waves 1-27). It handles extensive 
panel data processing, generates structural control and time poverty variables, and 
runs multiple regression models (OLS, Panel FE/BE) and correlation analyses.

# Directory & File Overview

[1] Data_cleansing(Stata code)
    1. data_cleaning.do
       - Setup and loops through Waves 1 to 27 of the KLIPS data.
       - Merges household and individual datasets and fixes household head extraction logic.
       - Generates baseline control variables and exports the v5.0 master file.
       
    2. data_cleaningv2.do
       - Extends the baseline data cleaning.
       - Extracts working hours and overtime data to construct Time Poverty variables (Total Weekly Working Hours).
       - Exports the v6.0 master file (Time Poverty included).

[2] Regression(Python code)
    3. mcferran_replication_timepoverty_v2.py
       - Runs Cross-sectional Hierarchical OLS (2024 wave).
       - Runs Panel Fixed Effects (FE) and Between Effects (BE) across 27 waves.
       - Includes quartile split analysis based on income.
       - Uses 'total_work_hr' to control for Time Poverty and adjusts for selection bias (unemployed/retired).
       
    4. panel_regression_analysis_appendix.py
       - Conducts robustness checks using Household-Level Subjective Poverty (feeling_poor_h) as the IV.
       - Replicates Table 2 methodology (Fixed Effects, Between-Effects, Income Quartile Splits) across all 4 dependent variables using the v5.0 master file.

    5. panel_regression_analysis.py
       - Main replication script for Table 2 methodology using Individual-Level Subjective Poverty (feeling_poor) as the IV.
       - Runs Fixed Effects (M6), Between-Effects (M7), and Income Quartile Splits (M8-M11) across all dependent variables.
       
    6. table1_cross_sectional.py
       - Replicates Table 1 methodology running Cross-sectional Hierarchical OLS using only the 2024 wave data.
       - Compares Set A (feeling_poor) and Set B (feeling_poor_h) across stepwise models (M1 to M4) for all dependent variables.

[3] Robustness_Check
    7. Correlation_check.py
       - Analyzes the correlation between Objective Income (std_log_income) and Subjective Poverty (feeling_poor, feeling_poor_h).
       - Calculates both Pearson and Spearman correlation coefficients.
       - Generates and saves a correlation heatmap visualization (correlation_heatmap.png).

# Requirements
- Stata 16 or higher (for .do files)
- Python 3.8+ (for .py files)
  * Required Python libraries: pandas, numpy, statsmodels, linearmodels, seaborn, matplotlib

# Usage
1. Update the base paths in the Stata scripts to point to your local KLIPS raw data.
2. Run the Stata scripts sequentially to generate the master CSV files (v5.0 and v6.0).
3. Update the DATA_PATH in the Python scripts to point to the generated CSV files.
4. Run the Python scripts in the Regression and Robustness_Check folders to output the summary tables and visualizations.