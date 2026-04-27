/* -----------------------------------------------------------------------------
   Title: KLIPS Data Cleaning & Merge (Waves 1-27) for McFerran Replication
   Description: Loops through panel waves, extracts relevant variables, recodes
                directionalities safely, and prepares a master long-format CSV.
   DVs: (1) Social relationship satisfaction (Attitude)
        (2) Social gathering participation (Behavior - Dummy)
        (3) Family meeting frequency (Behavior - Frequency)
----------------------------------------------------------------------------- */

clear all
set more off

* 1. Setup Data Environment
global base_path "/Users/dankim/Downloads/SNU/대학원/논문/data/klips/1-27차 release  (Stata)"
cd "$base_path"

local filelist ""

* 2. Loop & Merge: Waves 1 to 27
forvalues w = 1/27 {

    local ww = string(`w', "%02.0f")

    cap confirm file "klips`ww'p.dta"
    if _rc == 0 {

        display "Processing Wave `w'..."
        use "klips`ww'p.dta", clear

        * Standardize the merge key
        cap rename h`ww'hhid hhid

        * Merge with Household (h) file
        cap confirm file "klips`ww'h.dta"
        if _rc == 0 {
            merge m:1 hhid using "klips`ww'h.dta"
            keep if _merge == 3
            drop _merge
        }
        else {
            display "Warning: klips`ww'h.dta missing. Skipping merge."
        }

        * Survey Year
        gen year = 1997 + `w'

        * --- Individual-level (p file) variables ---
        cap rename p`ww'0101 gender
        cap rename p`ww'0107 birth_year
        cap rename p`ww'0314 feeling_poor_raw
        cap rename p`ww'0311 health_raw
        cap rename p`ww'0312 life_sat_raw
        cap rename p`ww'0316 sat_social_raw
        cap rename p`ww'3001 gathering_raw
        cap rename p`ww'0412 family_freq_raw

        * --- Household-level (h file) variables ---
        cap rename h`ww'2102 income
        cap rename h`ww'0141 region_code
        cap rename h`ww'2156 hardship_raw

        * If variable does not exist in this wave, create as missing
        local keepvars pid hhid year gender birth_year feeling_poor_raw sat_social_raw gathering_raw family_freq_raw health_raw life_sat_raw income region_code hardship_raw
        foreach var of local keepvars {
            cap confirm variable `var'
            if _rc != 0 {
                gen `var' = .
            }
        }

        keep `keepvars'

        * Replace KLIPS missing codes (negative values) with Stata missing
        foreach var of varlist _all {
            cap replace `var' = . if `var' < 0
        }

        * Replace Don't Know / Refusal codes for ordinal variables
        local ordvars feeling_poor_raw sat_social_raw family_freq_raw health_raw life_sat_raw hardship_raw
        foreach var of local ordvars {
            cap replace `var' = . if `var' >= 9
        }

        * gathering_raw: 1=Yes, 2=No. Values >= 3 are invalid
        cap replace gathering_raw = . if gathering_raw >= 3

        * family_freq_raw: value 7 = Not applicable -> missing
        cap replace family_freq_raw = . if family_freq_raw == 7

        * Save wave to temp
        tempfile wave`w'
        save "`wave`w''"
        local filelist `filelist' "`wave`w''"
    }
}

* 3. Append All Waves
display "Appending all 27 waves..."
clear
foreach file of local filelist {
    append using "`file'"
}

* 4. Recoding (Higher value = More/Better)
display "Calculating final variables..."

* Age
gen age = year - birth_year

* DV1: Social relationship satisfaction (1=Very Satisfied ~ 5=Very Dissatisfied -> reverse)
gen dv1_social_sat = 6 - sat_social_raw

* DV2: Social gathering participation (1=Yes, 2=No -> dummy 1=participate, 0=not)
gen dv2_gathering_dummy = (gathering_raw == 1) if !missing(gathering_raw)

* DV3: Family meeting frequency (1=Almost daily ~ 6=Never, 7=N/A already missing -> reverse)
gen dv3_family_freq = 7 - family_freq_raw if family_freq_raw > 0 & family_freq_raw <= 6

* IV: Feeling Poor (higher = feeling poorer, keep as-is)
gen feeling_poor = feeling_poor_raw

* Controls
gen health = 6 - health_raw
gen life_sat = 6 - life_sat_raw
gen log_income = ln(income + 1)
gen is_metro = inlist(region_code, 1, 4, 8)
gen financial_hardship = (hardship_raw == 1) if !missing(hardship_raw)

* 5. Big 5 Personality Traits (from Wave 18 Supplemental Survey)
display "Extracting Big 5 Personality Traits from klips18a.dta..."

preserve

    use "$base_path/klips18a.dta", clear

    * Keep only pid and the 15 personality items (7-point Likert scale)
    keep pid a188101-a188115

    * Handle Missing Values (replace < 0 or > 7 with missing)
    foreach var of varlist a188101-a188115 {
        cap replace `var' = . if `var' < 0 | `var' > 7
    }

    * Reverse-code the negative items (8 - value)
    replace a188103 = 8 - a188103
    replace a188107 = 8 - a188107
    replace a188112 = 8 - a188112

    * Calculate average scores for each of the 5 traits
    egen conscientiousness = rowmean(a188101 a188107 a188111)
    egen extroversion      = rowmean(a188102 a188108 a188112)
    egen agreeableness     = rowmean(a188103 a188106 a188113)
    egen openness          = rowmean(a188104 a188109 a188114)
    egen neuroticism       = rowmean(a188105 a188110 a188115)

    * Keep only final trait variables
    keep pid conscientiousness extroversion agreeableness openness neuroticism

    * Remove duplicates (keep first observation per pid)
    bysort pid: keep if _n == 1

    tempfile big5_temp
    save "`big5_temp'"

restore

* Merge Big 5 into master dataset
merge m:1 pid using "`big5_temp'"
keep if _merge == 1 | _merge == 3
drop _merge

* Fill Big 5 across all waves (personality is time-invariant)
local b5vars conscientiousness extroversion agreeableness openness neuroticism
foreach var of local b5vars {
    bysort pid (`var'): replace `var' = `var'[1] if missing(`var')
}

display "Big 5 Personality Traits merged and filled successfully."

* 6. Export
display "Exporting long-format master data to CSV..."
export delimited using "klips_master_mcferran.csv", replace

display "Pipeline Complete! Master file saved."
