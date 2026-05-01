* =============================================================================
* KLIPS Data Cleaning: McFerran Replication (v6.0 - Time Poverty / Working Hours Added)
* =============================================================================

clear all
set more off
set varabbrev off

* 1. Setup
global base_path "/Users/dankim/Downloads/SNU/대학원/논문/data/klips/1-27차 release  (Stata)"
cd "$base_path"
local filelist ""

* 2. Loop & Merge: Waves 1 to 27
forvalues w = 1/27 {
    local ww = string(`w', "%02.0f")
    cap confirm file "klips`ww'p.dta"
    if _rc == 0 {
        display "===== Processing Wave `w' ====="
        
        * -----------------------------------------------------------
        * (1) Prepare household (h) file
        * -----------------------------------------------------------
        cap confirm file "klips`ww'h.dta"
        if _rc == 0 {
            use "klips`ww'h.dta", clear
            rename *, lower
            
            cap confirm variable hhid
            if _rc != 0 {
                cap rename hhid`ww' hhid
                cap rename h`ww'hhid hhid
            }
            cap destring hhid, replace force
            cap duplicates drop hhid, force
            
            * Subjective economic status (h2705: common across waves 1~27)
            cap rename h`ww'2705 subj_econ_status
            
            * Sum of 3 objective monthly income types (exists only in waves 4~27)
            gen monthly_income = .
            if `w' >= 4 {
                cap rename h`ww'2202 inc_labor
                cap rename h`ww'2204 inc_finance
                cap rename h`ww'2206 inc_property
                
                replace monthly_income = 0
                foreach v in inc_labor inc_finance inc_property {
                    cap confirm variable `v'
                    if _rc == 0 {
                        cap destring `v', replace force
                        cap replace `v' = 0 if `v' < 0 | missing(`v')
                        replace monthly_income = monthly_income + `v'
                    }
                }
            }
            
            * Logic to extract household head's gender and birth year
            gen h_head_gender = .
            gen h_head_birth_year = .
            
            forvalues i = 1/15 {
                local n_gen = 240 + `i'
                local v_gen "0`n_gen'"
                local n_rel = 260 + `i'
                local v_rel "0`n_rel'"
                local n_byr = 300 + `i'
                local v_byr "0`n_byr'"
                
                cap confirm variable h`ww'`v_rel'
                if _rc == 0 {
                    cap replace h_head_gender = h`ww'`v_gen' if h`ww'`v_rel' == 10
                    cap replace h_head_birth_year = h`ww'`v_byr' if h`ww'`v_rel' == 10
                }
            }
            
            * Frequency of contact
            cap rename h`ww'1103 p_contact_none
            cap rename h`ww'1104 p_contact_m
            cap rename h`ww'1105 p_contact_y
            cap rename h`ww'1203 i_contact_none
            cap rename h`ww'1204 i_contact_m
            cap rename h`ww'1205 i_contact_y
            cap rename h`ww'1303 c_contact_none
            cap rename h`ww'1304 c_contact_m
            cap rename h`ww'1305 c_contact_y
            
            tempfile h_temp
            save "`h_temp'", replace
        }

        * -----------------------------------------------------------
        * (2) Prepare individual (p) file
        * -----------------------------------------------------------
        use "klips`ww'p.dta", clear
        rename *, lower
        
        cap confirm variable hhid
        if _rc != 0 {
            cap rename hhid`ww' hhid
            cap rename h`ww'hhid hhid
        }
        cap destring hhid, replace force
        
        cap rename p`ww'6501 feeling_poor_raw
        cap rename p`ww'6506 sat_social_raw
        cap rename p`ww'1222 free_time_1
        cap rename p`ww'1223 free_time_2
        cap rename p`ww'1224 free_time_3
        cap rename p`ww'6101 health_raw
        cap rename p`ww'6508 life_sat_raw
        
        * [Addition] Extract working hours and overtime (Time Poverty)
        cap rename p`ww'1003 reg_fixed      // Are regular working hours fixed? (1:Yes, 2:No)
        cap rename p`ww'1004 reg_hr_no      // (If No) Average hours per week
        cap rename p`ww'1005 reg_day_no     // (If No) Average days per week
        cap rename p`ww'1006 reg_hr_yes     // (If Yes) Average hours per week
        cap rename p`ww'1007 reg_day_yes    // (If Yes) Average days per week
        
        cap rename p`ww'1011 ot_exists      // Overtime existence (1:No, 2:Yes)
        cap rename p`ww'1019 ot_period      // Weekly/Monthly classification (1:Week, 2:Month estimated)
        cap rename p`ww'1012 ot_hr          // Overtime hours
        cap rename p`ww'1013 ot_day         // Overtime days

        * -----------------------------------------------------------
        * (3) Merge
        * -----------------------------------------------------------
        cap merge m:1 hhid using "`h_temp'"
        if _rc == 0 {
            keep if _merge == 3
            drop _merge
        }
        gen year = 1997 + `w'
        
        * [Addition] Include working hour variables in keepvars
        local keepvars pid hhid year h_head_gender h_head_birth_year ///
            feeling_poor_raw subj_econ_status sat_social_raw ///
            free_time_1 free_time_2 free_time_3 ///
            p_contact_none p_contact_m p_contact_y ///
            i_contact_none i_contact_m i_contact_y ///
            c_contact_none c_contact_m c_contact_y ///
            monthly_income health_raw life_sat_raw ///
            reg_fixed reg_hr_no reg_day_no reg_hr_yes reg_day_yes ///
            ot_exists ot_period ot_hr ot_day

        foreach var of local keepvars {
            cap confirm variable `var'
            if _rc != 0 {
                gen `var' = .
            }
        }
        keep `keepvars'
        
        * Handle negative missing values (-1: don't know/no response, etc.)
        foreach var of varlist _all {
            if "`var'" != "monthly_income" {
                cap replace `var' = . if `var' < 0
            }
        }
        
        tempfile wave`w'
        save "`wave`w''", replace
        local filelist `filelist' "`wave`w''"
        display "Wave `w' complete."
    }
}

* -----------------------------------------------------------
* 3. Append & Final Recoding
* -----------------------------------------------------------
clear
foreach file of local filelist {
    append using "`file'"
}

rename h_head_gender gender
rename h_head_birth_year birth_year

* --- [DV Generation] ---
gen dv1_social_sat = 6 - sat_social_raw
foreach target in p i c {
    gen `target'_freq = .
    replace `target'_freq = `target'_contact_m if !missing(`target'_contact_m)
    replace `target'_freq = `target'_contact_y / 12 if missing(`target'_freq) & !missing(`target'_contact_y)
    replace `target'_freq = 0 if `target'_contact_none == 3
}
egen dv2_family_freq = rowtotal(p_freq i_freq c_freq), missing

* --- [IV and Control Variables] ---
gen feeling_poor = feeling_poor_raw
gen feeling_poor_h = subj_econ_status

gen log_income = ln(monthly_income + 1)
egen std_log_income = std(log_income)

gen health = 6 - health_raw
gen life_sat = 6 - life_sat_raw
gen age = year - birth_year

* --- [NEW: Time Poverty (Total weekly working hours) variable generation] ---

* 1. Regular working hours (based on weekly hours)
gen reg_work_hr = .
replace reg_work_hr = reg_hr_yes if reg_fixed == 1
replace reg_work_hr = reg_hr_no if reg_fixed == 2

* 2. Overtime hours (converted to weekly hours)
gen ot_weekly_hr = 0
* Standardize overtime to missing if there are no regular working hours (e.g., economically inactive population)
replace ot_weekly_hr = . if missing(reg_work_hr)

* If responded yes to overtime (ot_exists == 2)
* If ot_period == 2 (monthly basis), assume a month has 4.345 weeks and convert to weekly hours
replace ot_weekly_hr = ot_hr if ot_exists == 2 & (ot_period == 1 | missing(ot_period))
replace ot_weekly_hr = ot_hr / 4.345 if ot_exists == 2 & ot_period == 2

* 3. Total Weekly Working Hours
* Treat as missing if any missing value exists to prevent data distortion
egen total_work_hr = rowtotal(reg_work_hr ot_weekly_hr), missing


* 4. Export
export delimited using "klips_master_mcferran_v6_timepoverty.csv", replace
display "V6.0 Master File (Time Poverty variables added) Saved."