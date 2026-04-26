/* -----------------------------------------------------------------------------
Title: KLIPS Data Cleaning & Merge (Waves 1-27) for McFerran Replication
Description: Loops through panel waves, extracts relevant variables, recodes 
             directionalities safely, and prepares a master long-format CSV.
----------------------------------------------------------------------------- */

clear all
set more off

* 1. Setup Data Environment
global base_path "C:\Users\home\Desktop\JRHT\SNU\Masters\1학년\2학기\소비자행동론\MCFerran Replication\1-27차 release (Stata)"
cd "$base_path"

* Initialize a local macro to store temporary appended waves
local filelist ""

* 2. Loop & Merge: Waves 1 to 27
forvalues w = 1/27 {

    * Format wave number to 2 zero-padded digits (e.g., 01, 14, 27)
    local wave_str : display %02.0f `w'
    
    * Check if the individual (p) file exists
    capture confirm file "klips`wave_str'p.dta"
    if _rc == 0 {
    
        display "Processing Wave `w'..."
        use "klips`wave_str'p.dta", clear
        
        * Standardize the merge key before merging
        capture rename h`wave_str'hhid hhid
        
        * Merge with the Household (h) dataset
        capture confirm file "klips`wave_str'h.dta"
        if _rc == 0 {
            merge m:1 hhid using "klips`wave_str'h.dta"
            keep if _merge == 3
            drop _merge
        }
        else {
            display "Warning: klips`wave_str'h.dta missing. Skipping merge."
        }
        
        * Generate specific Survey Year
        gen year = 1997 + `w'
        
        * Safely rename target variables using 'capture' to bypass missing variables in older waves
        capture rename p`wave_str'0101 gender
        capture rename p`wave_str'0107 birth_year
        capture rename p`wave_str'0314 feeling_poor_raw
        capture rename p`wave_str'0316 socializing_raw
        capture rename p`wave_str'0311 health_raw
        capture rename p`wave_str'0312 life_sat_raw
        
        capture rename h`wave_str'2102 income
        capture rename h`wave_str'0141 region_code
        capture rename h`wave_str'2156 hardship_raw
        
        * Guarantee subset completeness: If some vars don't exist in this wave, create them as missing
        local keepvars pid hhid year gender birth_year feeling_poor_raw socializing_raw health_raw life_sat_raw income region_code hardship_raw
        foreach var of local keepvars {
            capture confirm variable `var'
            if _rc != 0 {
                gen `var' = .
            }
        }
        
        * Extract strictly necessary variables to optimize memory
        keep `keepvars'
        
        * Standardize missing value codes: KLIPS missing codes (e.g., -1) converted to system missing (.)
        foreach var of varlist _all {
            capture replace `var' = . if `var' < 0
        }
        
        * Save to temp local memory
        tempfile wave`w'
        save "`wave`w''"
        
        * Add to running list
        local filelist `filelist' "`wave`w''"
    }
}

* 3. Append All Waves
display "Appending all 27 waves..."
clear
foreach file of local filelist {
    append using "`file'"
}

* 4. Recoding & Operational Variable Generation (Critical Directionality)
display "Calculating final variables..."

* Age
gen age = year - birth_year

* Reverse code so higher = better/more (Assuming 5-point Likert scales where 1=Highest)
gen socializing = 6 - socializing_raw
gen health = 6 - health_raw
gen life_sat = 6 - life_sat_raw

* IV: Feeling Poor (Kept as is. Higher raw value already indicates feeling poorer)
gen feeling_poor = feeling_poor_raw

* Objective wealth parameter
gen log_income = ln(income + 1)

* Determine Metro Resident (1=Seoul, 4=Incheon, 8=Gyeonggi based on KLIPS Codebook)
gen is_metro = inlist(region_code, 1, 4, 8)


* 5. Final Export for Python Intake
display "Exporting long-format master data to CSV..."
local export_path "C:\Users\home\Desktop\McFerran_Replication\klips_master_mcferran.csv"
export delimited using "`export_path'", replace

display "Pipeline Complete! Master file saved at: `export_path'"
