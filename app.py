"""
서울교통공사 지하철 혼잡도 대시보드
Phase 2: MVP 대시보드
"""
import streamlit as st
import plotly.express as px
from data_loader import (
    load_data, 
    get_reference_date, 
    calculate_peak,
    calculate_commute_avg,
    calculate_evening_avg,
    get_peak_top10,
    get_station_peak_summary
)

# 페이지 설정
st.set_page_config(
    page_title="지하철 혼잡도",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 제목
st.title("🚇 서울교통공사 지하철 혼잡도 대시보드")

# 데이터 로딩
with st.spinner("데이터를 로딩하는 중..."):
    df, error_msg = load_data()

# 오류 처리
if error_msg:
    st.error(f"❌ 데이터 로딩 실패: {error_msg}")
    st.stop()

# 기준일
ref_date = get_reference_date()

# ========================================
# 사이드바 필터
# ========================================
st.sidebar.header("🔍 필터")

# 기준일 표시
st.sidebar.info(f"📅 데이터 기준일: **{ref_date}**")
st.sidebar.markdown("---")

# 요일구분
all_days = df['요일구분'].unique().tolist()
selected_days = st.sidebar.multiselect(
    "요일 구분",
    options=all_days,
    default=all_days
)

# 호선
all_lines = sorted(df['호선'].unique().tolist())
selected_lines = st.sidebar.multiselect(
    "호선",
    options=all_lines,
    default=all_lines
)

# 방향
all_directions = df['상하선구분'].unique().tolist()
selected_directions = st.sidebar.multiselect(
    "방향",
    options=all_directions,
    default=all_directions
)

# 역명 검색
station_search = st.sidebar.text_input(
    "역명 검색 (부분 문자열)",
    value="",
    placeholder="예: 강남"
)

st.sidebar.markdown("---")
st.sidebar.subheader("⏰ 출퇴근 시간대 설정")

# 출근 시간대 토글
include_9 = st.sidebar.toggle(
    "출근시간 9시 포함",
    value=True,
    help="출근시간 평균 계산 시 9시를 포함합니다 (7~9시)"
)

# 퇴근 시간대 토글
include_20 = st.sidebar.toggle(
    "퇴근시간 20시 포함",
    value=True,
    help="퇴근시간 평균 계산 시 20시를 포함합니다 (17~20시)"
)

# ========================================
# 필터 적용
# ========================================
filtered_df = df.copy()

# 요일 필터
if selected_days:
    filtered_df = filtered_df[filtered_df['요일구분'].isin(selected_days)]

# 호선 필터
if selected_lines:
    filtered_df = filtered_df[filtered_df['호선'].isin(selected_lines)]

# 방향 필터
if selected_directions:
    filtered_df = filtered_df[filtered_df['상하선구분'].isin(selected_directions)]

# 역명 검색 필터
if station_search:
    filtered_df = filtered_df[filtered_df['역명'].str.contains(station_search, na=False)]

# 필터링 결과 확인
if filtered_df.empty:
    st.warning("⚠️ 선택한 필터 조건에 해당하는 데이터가 없습니다. 필터를 조정해주세요.")
    st.stop()

# ========================================
# KPI 메트릭
# ========================================
st.markdown("---")
st.subheader("📈 주요 지표")

col1, col2, col3 = st.columns(3)

# 피크 혼잡
peak_crowding, peak_time = calculate_peak(filtered_df)
with col1:
    st.metric(
        "최대 피크 혼잡",
        f"{peak_crowding:.1f}%",
        help="선택된 범위 내 최대 혼잡도"
    )
    st.caption(f"발생 시간: {peak_time}")

# 출근 평균
commute_avg = calculate_commute_avg(filtered_df, include_9=include_9)
with col2:
    time_range = "7~9시" if include_9 else "7~9시 미만"
    st.metric(
        f"출근시간 평균 ({time_range})",
        f"{commute_avg:.1f}%",
        help="출근 시간대 평균 혼잡도"
    )

# 퇴근 평균
evening_avg = calculate_evening_avg(filtered_df, include_20=include_20)
with col3:
    time_range = "17~20시" if include_20 else "17~20시 미만"
    st.metric(
        f"퇴근시간 평균 ({time_range})",
        f"{evening_avg:.1f}%",
        help="퇴근 시간대 평균 혼잡도"
    )

# ========================================
# 피크 TOP10 테이블
# ========================================
st.markdown("---")
st.subheader("🔥 피크 혼잡 TOP 10")

top10_df = get_peak_top10(filtered_df)

if not top10_df.empty:
    # 피크혼잡 컬럼 포맷팅
    display_df = top10_df.copy()
    display_df['피크혼잡'] = display_df['피크혼잡'].apply(lambda x: f"{x:.1f}%")
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )
else:
    st.info("조건에 맞는 데이터가 없습니다.")

# ========================================
# 역 선택 시간대별 라인차트
# ========================================
st.markdown("---")
st.subheader("📊 역별 시간대별 혼잡도")

# 역 선택
available_stations = sorted(filtered_df['역명'].unique().tolist())

if available_stations:
    selected_station = st.selectbox(
        "역 선택",
        options=available_stations,
        index=0
    )
    
    # 선택한 역 데이터 필터링
    station_df = filtered_df[filtered_df['역명'] == selected_station].copy()
    
    # 방향별로 그룹화하여 평균 계산
    station_agg = station_df.groupby(['time', 'hour', 'minute', 'time_order', '상하선구분']).agg({
        'crowding': 'mean'
    }).reset_index()
    
    # 시간 순서대로 정렬
    station_agg = station_agg.sort_values('time_order')
    
    if not station_agg.empty:
        # Plotly 라인차트
        fig = px.line(
            station_agg,
            x='time',
            y='crowding',
            color='상하선구분',
            markers=True,
            title=f"{selected_station}역 시간대별 혼잡도",
            labels={
                'time': '시간대',
                'crowding': '혼잡도 (%)',
                '상하선구분': '방향'
            }
        )
        
        fig.update_layout(
            xaxis_tickangle=-45,
            hovermode='x unified',
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"{selected_station}역에 대한 데이터가 없습니다.")
else:
    st.info("표시할 역이 없습니다.")

# ========================================
# 역별 피크 테이블
# ========================================
st.markdown("---")
st.subheader("🚉 역별 피크 혼잡 요약")

station_summary = get_station_peak_summary(filtered_df)

if not station_summary.empty:
    # 피크혼잡 컬럼 포맷팅
    display_summary = station_summary.copy()
    display_summary['피크혼잡'] = display_summary['피크혼잡'].apply(lambda x: f"{x:.1f}%")
    
    st.dataframe(
        display_summary,
        use_container_width=True,
        hide_index=True,
        height=400
    )
else:
    st.info("조건에 맞는 데이터가 없습니다.")

# 하단 정보
st.markdown("---")
st.caption("Phase 2: MVP 대시보드 - 서울교통공사 지하철 혼잡도")
