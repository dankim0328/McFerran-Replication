import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import warnings

warnings.filterwarnings("ignore")

# 1. 데이터 로드 (v6 버전에 맞게 이름 수정, 없을 시 fallback 경로 사용)
# 1. 데이터 로드 (절대경로로 수정)
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

# 2. 분석할 변수 선택 및 결측치 제거
# std_log_income: 객관적 소득 (표준화된 로그 소득)
# feeling_poor: 개인 차원의 주관적 경제적 불만족 (Main IV)
# feeling_poor_h: 가구 차원의 주관적 경제 상태 (Appendix IV)
target_cols = ['std_log_income', 'feeling_poor', 'feeling_poor_h']

print("\n" + "="*60)
print("Correlation Analysis: Objective Income vs Subjective Poverty")
print("="*60)

# 모든 변수가 존재하는 데이터만 추출
df_corr = df[target_cols].dropna()
print(f"Valid observations for correlation analysis: N = {len(df_corr):,}\n")

# 변수명 예쁘게 변경 (출력 및 그래프용)
df_corr.columns = ['Objective Income\n(Std Log Income)', 
                   'Personal Feeling Poor\n(Individual IV)', 
                   'Household Feeling Poor\n(Appendix IV)']

# 3. 상관계수 계산 (Pearson & Spearman)
# 주관적 빈곤감은 1~5점 척도(서열 변수)이므로 Spearman 상관계수도 함께 보는 것이 정통입니다.
corr_pearson = df_corr.corr(method='pearson')
corr_spearman = df_corr.corr(method='spearman')

print("--- [1] Pearson Correlation Coefficients ---")
print(corr_pearson.round(3))
print("\n--- [2] Spearman Rank Correlation Coefficients ---")
print(corr_spearman.round(3))

# 4. 시각화: 상관관계 히트맵 (Correlation Map) 그리기
plt.figure(figsize=(8, 6))

# 히트맵 생성 (색상 테마: 파란색-빨간색, 수치 표시)
sns.heatmap(corr_pearson, 
            annot=True,          # 수치 표시
            fmt=".3f",           # 소수점 3자리까지
            cmap="coolwarm",     # 파란색(-)에서 빨간색(+)으로
            vmin=-1, vmax=1,     # 상관계수 범위 고정
            center=0,            # 0을 흰색으로
            square=True, 
            linewidths=.5,
            annot_kws={"size": 12}) # 폰트 크기

plt.title("Correlation Map: Objective vs Subjective Poverty\n(Pearson Correlation)", fontsize=14, pad=15)
plt.xticks(rotation=15, ha='right')
plt.yticks(rotation=0)
plt.tight_layout()

# 그래프 저장 및 출력
save_path = "correlation_heatmap.png"
plt.savefig(save_path, dpi=300)
print(f"\n✅ Correlation heatmap saved as: {save_path}")

# Mac 환경에서 그래프 창 띄우기
plt.show()