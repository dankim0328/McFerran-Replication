import pandas as pd

# 데이터 로드
df = pd.read_csv("/Users/dankim/Downloads/SNU/대학원/논문/data/klips/1-27차 release  (Stata)/klips_master_mcferran.csv")

# 각 핵심 변수별 실제 데이터 개수 최종 확인
print("--- 변수별 유효 데이터 개수 ---")
print(df[['feeling_poor', 'feeling_poor_alt', 'dv1_social_sat', 'dv2_gathering_dummy', 'dv3_family_freq', 'log_income']].count())