import os
import gc
import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
from linearmodels.panel import PanelOLS

import openpyxl.worksheet.properties
_original_init = openpyxl.worksheet.properties.WorksheetProperties.__init__

def patched_init(self, *args, **kwargs):
    if 'synchVertical' in kwargs:
        kwargs['syncVertical'] = kwargs.pop('synchVertical')
    _original_init(self, *args, **kwargs)

openpyxl.worksheet.properties.WorksheetProperties.__init__ = patched_init


def merge_big5_personality(panel_df, base_path):
    """
    [PLACEHOLDER FUNCTION] - Merging Big 5 Personality Traits
    
    The paper uses Big 5 personality traits from a supplemental survey.
    In KLIPS, supplemental modules ('a' files, e.g., klips26a.xlsx) contain specific items.
    """
    print("\n[NOTE] Big 5 Personality: Check supplemental 'a' files to merge real traits.")
    big5_cols = ['extroversion', 'agreeableness', 'conscientiousness', 'neuroticism', 'openness']
    for col in big5_cols:
        panel_df[col] = np.nan 
        
    return panel_df

def safe_read(file_base, cols_needed):
    """
    Safely reads CSV or Excel files, strictly loading only the needed columns 
    to prevent out-of-memory errors on large panels.
    """
    # usecols as a callable avoids ValueError if a column isn't in a specific wave
    # We use `.lower()` to handle any capitalization inconsistencies
    lower_needed = [c.lower() for c in cols_needed]
    usecols_callable = lambda c: str(c).lower() in lower_needed

    # 1. Look for various potential CSV names first (Expedient & memory friendly!)
    csv_paths = [
        f"{file_base}.csv",
        f"{file_base}.xlsx - Data.csv",  
        f"{file_base}_Data.csv"
    ]
    
    for csv_path in csv_paths:
        if os.path.exists(csv_path):
            try:
                return pd.read_csv(csv_path, usecols=usecols_callable, low_memory=False)
            except Exception as e:
                print(f"Failed CSV read on {csv_path}: {e}")

    # 2. Fallback to Pandas Excel loading with the strict usecols limit
    xlsx_path = f"{file_base}.xlsx"
    if os.path.exists(xlsx_path):
        try:
            return pd.read_excel(xlsx_path, usecols=usecols_callable)
        except Exception as e:
            print(f"Failed XLSX read on {xlsx_path}: {e}")
            
    return None

def main():
    # --------------------------------------------------------------------------------
    # 1. Data Environment & Context Setup
    # --------------------------------------------------------------------------------
    base_path = r"C:\Users\home\Desktop\JRHT\SNU\Masters\1학년\2학기\소비자행동론\MCFerran Replication\1-27차년도 자료 (Excel)\1-27차 release (Excel)"
    all_waves_data = []
    missing_codes = [-1, 9, 99, 9999]
    
    print("Starting data loading and preprocessing... (Memory Optimized)")
    
    # --------------------------------------------------------------------------------
    # 2. OOM-Optimized Data Loading Loop
    # --------------------------------------------------------------------------------
    for w in range(1, 28):
        wave_str = f"{w:02d}"
        h_base = os.path.join(base_path, f"klips{wave_str}h")
        p_base = os.path.join(base_path, f"klips{wave_str}p")
        
        h_hid_col = f"h{wave_str}hhid"
        
        # We explicitly dictate only the precise columns we need loaded:
        cols_mapping_h = {
            h_hid_col: 'hhid',
            f'h{wave_str}2102': 'income',                 # Total household income
            f'h{wave_str}0141': 'region_code_raw',        # Residential cluster/region
            f'h{wave_str}2156': 'financial_hardship_raw'  # Proxy for borrowing/minimum cost
        }
        
        cols_mapping_p = {
            h_hid_col: 'hhid',
            'pid': 'pid',
            f'p{wave_str}0101': 'gender',
            f'p{wave_str}0107': 'birth_year',
            f'p{wave_str}0314': 'feeling_poor',           
            f'p{wave_str}0316': 'socializing',            
            f'p{wave_str}0311': 'health',                 
            f'p{wave_str}0312': 'life_sat'                
        }

        h_df = safe_read(h_base, list(cols_mapping_h.keys()))
        p_df = safe_read(p_base, list(cols_mapping_p.keys()))

        if h_df is None or p_df is None:
            # Expected if wave files don't physically exist in the test env
            continue
            
        print(f"Processing Wave {w} (Year: {1997 + w})...")
            
        # Clean renames ignoring case inconsistencies
        h_df = h_df.rename(columns=lambda c: cols_mapping_h.get(c.lower()) or cols_mapping_h.get(c))
        p_df = p_df.rename(columns=lambda c: cols_mapping_p.get(c.lower()) or cols_mapping_p.get(c))

        # We must align household IDs to merge them
        if 'hhid' in p_df.columns and 'hhid' in h_df.columns:
            merged = pd.merge(p_df, h_df, on='hhid', how='inner')
        else:
            print(f"Skipping Wave {w} merge error: 'hhid' not found in requested load limit.")
            continue
            
        merged['year'] = 1997 + w
        all_waves_data.append(merged)
        
        # Trigger explicit Garbage Collection post-merge to delete loose pointers and compress memory usage
        del h_df, p_df, merged
        gc.collect()

    if not all_waves_data:
        print("No valid wave data processed.")
        return

    # --------------------------------------------------------------------------------
    # 3. Concatenate and Clean Data Format
    # --------------------------------------------------------------------------------
    print("\nConcatenating waves and mapping missing values...")
    panel_df = pd.concat(all_waves_data, ignore_index=True)
    panel_df.replace(missing_codes, np.nan, inplace=True)
    panel_df['age'] = panel_df['year'] - panel_df['birth_year']
    
    req_cols = ['feeling_poor', 'income', 'age', 'gender', 'health', 'life_sat', 'socializing']
    panel_df = panel_df.dropna(subset=[c for c in req_cols if c in panel_df.columns])
    
    # --------------------------------------------------------------------------------
    # 4. Critical Base Recoding
    # --------------------------------------------------------------------------------
    panel_df['socializing'] = 6 - panel_df['socializing']
    panel_df['health'] = 6 - panel_df['health']
    panel_df['life_sat'] = 6 - panel_df['life_sat']
    
    panel_df['log_income'] = np.log(panel_df['income'] + 1)
    
    # --------------------------------------------------------------------------------
    # 5. Adding New Constructed Control Variables
    # --------------------------------------------------------------------------------
    # 5.1 Residential Proximity (is_metro) - Seoul = 1, Incheon = 4, Gyeonggi = 8
    if 'region_code_raw' in panel_df.columns:
        panel_df['is_metro'] = panel_df['region_code_raw'].isin([1, 4, 8]).astype(int)
    else:
        panel_df['is_metro'] = 0 
        
    # 5.2 Meeting Basic Needs (financial_hardship)
    if 'financial_hardship_raw' in panel_df.columns:
        panel_df['financial_hardship'] = (panel_df['financial_hardship_raw'] == 1).astype(int)
    else:
        panel_df['financial_hardship'] = 0 

    panel_df = merge_big5_personality(panel_df, base_path)

    panel_df['year'] = panel_df['year'].astype(int)
    panel_df['pid'] = panel_df['pid'].astype(int)
    
    panel_df = panel_df.set_index(['pid', 'year'])
    print(f"Data set successfully preprocessed! Dimensions: {panel_df.shape}")

    # Prepare robust formula features 
    actual_big5 = [col for col in ['extroversion', 'agreeableness', 'conscientiousness', 'neuroticism', 'openness'] 
                   if panel_df[col].notna().any()]
    big5_str = (" + " + " + ".join(actual_big5)) if actual_big5 else ""
    
    # Base OLS logic requested by User, seamlessly parses C(gender) as a categorized dummy
    ols_formula = f"socializing ~ feeling_poor + log_income + age + C(gender) + health + life_sat + is_metro + financial_hardship{big5_str}"


    # --------------------------------------------------------------------------------
    # 6. Model 1: Cross-Sectional OLS (WAVE 27) - Replicating Study 1
    # --------------------------------------------------------------------------------
    print("\n" + "="*80)
    print("MODEL 1: CROSS-SECTIONAL OLS (WAVE 27 - 2024)")
    print("="*80)
    
    try:
        df_w27 = panel_df.xs(2024, level='year').reset_index() # reset index to run formula normally
        m1_model = smf.ols(ols_formula, data=df_w27).fit(cov_type='HC3')
        print(m1_model.summary())
    except KeyError:
        print("Warning: Wave 27 (2024) data is not found in the dataset. Skipping Model 1.")
    except Exception as e:
        print(f"Error executing Model 1: {e}")

    # --------------------------------------------------------------------------------
    # 7. Model 2: Panel Fixed Effects - Replicating Model 6
    # --------------------------------------------------------------------------------
    print("\n" + "="*80)
    print("MODEL 2: PANEL FIXED EFFECTS (WAVES 1-27) - Replicating Model 6")
    print("="*80)
    
    try:
        # FE inherently absorbs Gender, Metro (mostly), and Big 5. 
        # For linearmodels we manually pass the design matrix X without C(gender)
        fe_controls = ['log_income', 'age', 'health', 'life_sat', 'financial_hardship']
        # Including is_metro on the off-chance they change region over 27 years.
        if 'is_metro' in panel_df.columns:
            fe_controls.append('is_metro')

        X_panel = panel_df[['feeling_poor'] + fe_controls]
        X_panel = sm.add_constant(X_panel)
        y_panel = panel_df['socializing']
        
        panel_model = PanelOLS(y_panel, X_panel, entity_effects=True, time_effects=True, drop_absorbed=True)
        panel_results = panel_model.fit(cov_type='clustered', cluster_entity=True)
        print(panel_results.summary)
    except Exception as e:
        print(f"Error executing Model 2: {e}")

    # --------------------------------------------------------------------------------
    # 8. Model 3: Between-Effects Panel Model - Replicating Model 7 
    # --------------------------------------------------------------------------------
    print("\n" + "="*80)
    print("MODEL 3: BETWEEN-EFFECTS MODEL - Replicating Model 7")
    print("="*80)
    
    # Aggregated averages for cross-person variance mapping
    # We reset index because 'pid' is needed if we use other metrics, but smf.ols uses columns.
    between_df = panel_df.groupby('pid').mean(numeric_only=True).dropna(subset=['feeling_poor', 'socializing'])
    
    # Round gender to mode behavior (0/1) conceptually for the categorical formula approach 
    # Or just leave it real-valued and strip C(gender) if it's proportion.
    # To keep exact user formula with C(gender), convert aggregated average to nearest 0/1 integer class.
    if 'gender' in between_df.columns:
        between_df['gender'] = between_df['gender'].round().astype(int)
        
    try:
        between_model = smf.ols(ols_formula, data=between_df).fit(cov_type='HC3')
        print(between_model.summary())
    except Exception as e:
        print(f"Error executing Model 3: {e}")

    # --------------------------------------------------------------------------------
    # 9. Models 4-7: Income Quartile Robustness - Replicating Models 8-11
    # --------------------------------------------------------------------------------
    print("\n" + "="*80)
    print("MODELS 4-7: INCOME QUARTILE ROBUSTNESS - Replicating Models 8-11")
    print("="*80)

    try:
        between_df['income_quartile'] = pd.qcut(between_df['log_income'], q=4, labels=['Q1 (Lowest)', 'Q2', 'Q3', 'Q4 (Highest)'], duplicates='drop')
        
        for q in between_df['income_quartile'].cat.categories:
            print(f"\n>>>> Estimating for {q} Average Income Quartile <<<<")
            q_df = between_df[between_df['income_quartile'] == q]
            
            # Using the same OLS formula across each subsection 
            q_model = smf.ols(ols_formula, data=q_df).fit(cov_type='HC3')
            
            print(f"N: {len(q_df)}")
            print(q_model.summary().tables[1])
            
    except Exception as e:
        print(f"Error in quartile regressions: {e}")

if __name__ == "__main__":
    main()
