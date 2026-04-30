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
        * (1) 가구(h) 파일 준비
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
            
            * 주관적 경제상태 (h2705: 1~27차 공통)
            cap rename h`ww'2705 subj_econ_status
            
            * 객관적 월 소득 3종 합산 (4~27차만 존재)
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
            
            * 가구주 성별 및 출생년도 추출 로직
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
            
            * 왕래 빈도
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
        * (2) 개인(p) 파일 준비
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
        
        * [추가] 근로시간 및 초과근무 추출 (Time Poverty)
        cap rename p`ww'1003 reg_fixed     // 정규근로시간 정해져 있는가? (1:예, 2:아니오)
        cap rename p`ww'1004 reg_hr_no     // (아니오) 일주일 평균 시간
        cap rename p`ww'1005 reg_day_no    // (아니오) 일주일 평균 일
        cap rename p`ww'1006 reg_hr_yes    // (예) 일주일 평균 시간
        cap rename p`ww'1007 reg_day_yes   // (예) 일주일 평균 일
        
        cap rename p`ww'1011 ot_exists     // 초과근무 여부 (1:없다, 2:있다)
        cap rename p`ww'1019 ot_period     // 주/월 구분 (1:주, 2:월 추정)
        cap rename p`ww'1012 ot_hr         // 초과근무 시간
        cap rename p`ww'1013 ot_day        // 초과근무 일

        * -----------------------------------------------------------
        * (3) 병합
        * -----------------------------------------------------------
        cap merge m:1 hhid using "`h_temp'"
        if _rc == 0 {
            keep if _merge == 3
            drop _merge
        }
        gen year = 1997 + `w'
        
        * [추가] keepvars에 근로시간 변수들 포함
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
        
        * 음수(-1: 모름/무응답 등) 결측치 처리
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

* --- [DV 생성] ---
gen dv1_social_sat = 6 - sat_social_raw
foreach target in p i c {
    gen `target'_freq = .
    replace `target'_freq = `target'_contact_m if !missing(`target'_contact_m)
    replace `target'_freq = `target'_contact_y / 12 if missing(`target'_freq) & !missing(`target'_contact_y)
    replace `target'_freq = 0 if `target'_contact_none == 3
}
egen dv2_family_freq = rowtotal(p_freq i_freq c_freq), missing

* --- [IV 및 통제변수] ---
gen feeling_poor = feeling_poor_raw
gen feeling_poor_h = subj_econ_status

gen log_income = ln(monthly_income + 1)
egen std_log_income = std(log_income)

gen health = 6 - health_raw
gen life_sat = 6 - life_sat_raw
gen age = year - birth_year

* --- [NEW: Time Poverty (총 주당 근로시간) 변수 생성] ---

* 1. 정규 근로시간 (주당 시간 기준)
gen reg_work_hr = .
replace reg_work_hr = reg_hr_yes if reg_fixed == 1
replace reg_work_hr = reg_hr_no if reg_fixed == 2

* 2. 초과 근로시간 (주당 시간 기준 변환)
gen ot_weekly_hr = 0
* 비경제활동인구 등 정규 근로시간이 없는 경우 초과근로시간도 missing으로 통일
replace ot_weekly_hr = . if missing(reg_work_hr)

* 초과근무가 있다고 응답한 경우 (ot_exists == 2)
* ot_period == 2 (월 단위)인 경우, 한 달을 4.345주로 가정하고 주당 시간으로 환산
replace ot_weekly_hr = ot_hr if ot_exists == 2 & (ot_period == 1 | missing(ot_period))
replace ot_weekly_hr = ot_hr / 4.345 if ot_exists == 2 & ot_period == 2

* 3. 총 주당 근로시간 (Total Weekly Working Hours)
* 결측치가 하나라도 있으면 missing 처리하여 데이터 왜곡 방지
egen total_work_hr = rowtotal(reg_work_hr ot_weekly_hr), missing


* 4. Export
export delimited using "klips_master_mcferran_v6_timepoverty.csv", replace
display "V6.0 Master File (Time Poverty variables added) Saved."