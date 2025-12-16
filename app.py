"""
서울교통공사 지하철 혼잡도 대시보드
Phase 1: 데이터 로딩 및 전처리 검증
"""
import streamlit as st
from data_loader import load_data, get_reference_date, get_data_summary

# 페이지 설정
st.set_page_config(
    page_title="지하철 혼잡도",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 제목
st.title("🚇 서울교통공사 지하철 혼잡도 대시보드")
st.markdown("---")

# 데이터 로딩
with st.spinner("데이터를 로딩하는 중..."):
    df, error_msg = load_data()

# 오류 처리
if error_msg:
    st.error(f"❌ 데이터 로딩 실패: {error_msg}")
    st.stop()

# 성공 메시지
st.success("✅ 데이터 로딩 완료")

# 기준일 표시
ref_date = get_reference_date()
st.info(f"📅 데이터 기준일: **{ref_date}**")

# 데이터 요약 정보
st.subheader("📊 데이터 요약")
summary = get_data_summary(df)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("총 데이터 행수", f"{summary['총 행수']:,}")
with col2:
    st.metric("역 수", f"{summary['역 수']}")
with col3:
    st.metric("시간대 수", f"{summary['시간대 수']}")
with col4:
    st.metric("혼잡도 결측", f"{summary['혼잡도 결측']:,}")

# 추가 정보
with st.expander("상세 정보 보기"):
    st.write("**요일 구분:**", ", ".join(summary['요일구분']))
    st.write("**호선:**", ", ".join(summary['호선']))
    st.write("**혼잡도 범위:**", summary['혼잡도 범위'])

st.markdown("---")

# 데이터 미리보기
st.subheader("🔍 데이터 미리보기 (상위 20행)")
st.dataframe(
    df.head(20),
    use_container_width=True,
    height=400
)

# 데이터 필터링 테스트 (개발용)
st.markdown("---")
st.subheader("🧪 필터링 테스트")

col1, col2 = st.columns(2)

with col1:
    # 역 선택
    selected_station = st.selectbox(
        "역 선택",
        options=sorted(df['역명'].unique()),
        index=0
    )

with col2:
    # 요일 선택
    selected_day = st.selectbox(
        "요일 선택",
        options=df['요일구분'].unique().tolist(),
        index=0
    )

# 필터링된 데이터
filtered_df = df[
    (df['역명'] == selected_station) & 
    (df['요일구분'] == selected_day)
]

st.write(f"**{selected_station}역 - {selected_day}** 데이터 ({len(filtered_df)}행)")
st.dataframe(
    filtered_df,
    use_container_width=True,
    height=300
)

# 하단 정보
st.markdown("---")
st.caption("Phase 1: 데이터 로딩/전처리 모듈 - 개발 중")
