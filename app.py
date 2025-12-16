"""
서울교통공사 지하철 혼잡도 대시보드
Phase 2: MVP 대시보드
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from data_loader import (
    load_data, 
    get_reference_date, 
    calculate_peak,
    calculate_commute_avg,
    calculate_evening_avg,
    get_peak_top10,
    get_commute_top10,
    get_evening_top10,
    get_line_summary,
    get_station_peak_summary,
    get_station_full_summary
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
# 랭킹 TOP10 탭 (피크 / 출근 / 퇴근)
# ========================================
st.markdown("---")
st.subheader("🔥 혼잡도 랭킹 TOP 10")

tab1, tab2, tab3 = st.tabs(["피크 TOP10", "출근 평균 TOP10", "퇴근 평균 TOP10"])

with tab1:
    st.markdown("##### 피크 혼잡도 기준")
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

with tab2:
    time_range = "7~9시" if include_9 else "7~9시 미만"
    st.markdown(f"##### 출근시간({time_range}) 평균 혼잡도 기준")
    commute_top10_df = get_commute_top10(filtered_df, include_9=include_9)
    
    if not commute_top10_df.empty:
        # 출근평균 컬럼 포맷팅
        display_df = commute_top10_df.copy()
        display_df['출근평균'] = display_df['출근평균'].apply(lambda x: f"{x:.1f}%")
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=400
        )
    else:
        st.info("조건에 맞는 데이터가 없습니다.")

with tab3:
    time_range = "17~20시" if include_20 else "17~20시 미만"
    st.markdown(f"##### 퇴근시간({time_range}) 평균 혼잡도 기준")
    evening_top10_df = get_evening_top10(filtered_df, include_20=include_20)
    
    if not evening_top10_df.empty:
        # 퇴근평균 컬럼 포맷팅
        display_df = evening_top10_df.copy()
        display_df['퇴근평균'] = display_df['퇴근평균'].apply(lambda x: f"{x:.1f}%")
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=400
        )
    else:
        st.info("조건에 맞는 데이터가 없습니다.")

# ========================================
# 노선별 비교 차트
# ========================================
st.markdown("---")
st.subheader("🚆 노선별 혼잡도 비교")

line_summary = get_line_summary(filtered_df, include_9=include_9, include_20=include_20)

if not line_summary.empty:
    # Plotly 그룹 바 차트 생성
    fig = go.Figure()
    
    # 평균 혼잡도 바
    fig.add_trace(go.Bar(
        name='전체 평균',
        x=line_summary['호선'],
        y=line_summary['평균혼잡'],
        marker_color='lightblue',
        text=line_summary['평균혼잡'].apply(lambda x: f'{x:.1f}%'),
        textposition='outside'
    ))
    
    # 피크 혼잡도 바
    fig.add_trace(go.Bar(
        name='피크',
        x=line_summary['호선'],
        y=line_summary['피크혼잡'],
        marker_color='red',
        text=line_summary['피크혼잡'].apply(lambda x: f'{x:.1f}%'),
        textposition='outside'
    ))
    
    # 출근 평균 바
    fig.add_trace(go.Bar(
        name='출근 평균',
        x=line_summary['호선'],
        y=line_summary['출근평균'],
        marker_color='orange',
        text=line_summary['출근평균'].apply(lambda x: f'{x:.1f}%'),
        textposition='outside'
    ))
    
    # 퇴근 평균 바
    fig.add_trace(go.Bar(
        name='퇴근 평균',
        x=line_summary['호선'],
        y=line_summary['퇴근평균'],
        marker_color='purple',
        text=line_summary['퇴근평균'].apply(lambda x: f'{x:.1f}%'),
        textposition='outside'
    ))
    
    fig.update_layout(
        barmode='group',
        xaxis_title='호선',
        yaxis_title='혼잡도 (%)',
        height=500,
        hovermode='x unified',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 테이블로도 표시
    with st.expander("📋 노선별 상세 수치 보기"):
        display_summary = line_summary.copy()
        display_summary['평균혼잡'] = display_summary['평균혼잡'].apply(lambda x: f"{x:.1f}%")
        display_summary['피크혼잡'] = display_summary['피크혼잡'].apply(lambda x: f"{x:.1f}%")
        display_summary['출근평균'] = display_summary['출근평균'].apply(lambda x: f"{x:.1f}%")
        display_summary['퇴근평균'] = display_summary['퇴근평균'].apply(lambda x: f"{x:.1f}%")
        
        st.dataframe(
            display_summary,
            use_container_width=True,
            hide_index=True
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
# 역별 종합 요약 테이블
# ========================================
st.markdown("---")
st.subheader("🚉 역별 혼잡도 종합 요약")

station_summary = get_station_full_summary(filtered_df, include_9=include_9, include_20=include_20)

if not station_summary.empty:
    # 컬럼 포맷팅
    display_summary = station_summary.copy()
    display_summary['피크혼잡'] = display_summary['피크혼잡'].apply(lambda x: f"{x:.1f}%")
    display_summary['출근평균'] = display_summary['출근평균'].apply(lambda x: f"{x:.1f}%")
    display_summary['퇴근평균'] = display_summary['퇴근평균'].apply(lambda x: f"{x:.1f}%")
    
    st.dataframe(
        display_summary,
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    st.caption(f"💡 출근평균: 7~9시{'(9시 포함)' if include_9 else ''} | 퇴근평균: 17~20시{'(20시 포함)' if include_20 else ''}")
else:
    st.info("조건에 맞는 데이터가 없습니다.")

# ========================================
# 전체 노선 시간대별 혼잡도 히트맵
# ========================================
st.markdown("---")
st.subheader("🌡️ 전체 노선 시간대별 혼잡도 히트맵")

# 노선별, 방향별, 시간대별 평균 혼잡도 계산
heatmap_data = filtered_df.groupby(['호선', '상하선구분', 'time', 'time_order']).agg({
    'crowding': 'mean'
}).reset_index()

# 노선+방향 컬럼 생성 (예: "1호선-상행")
heatmap_data['노선방향'] = heatmap_data['호선'] + '-' + heatmap_data['상하선구분']

# 피벗 테이블 생성 (행: 노선방향, 열: 시간)
if not heatmap_data.empty:
    # 시간 순서대로 정렬
    heatmap_data = heatmap_data.sort_values('time_order')
    
    # 피벗 테이블 생성
    pivot_data = heatmap_data.pivot_table(
        index='노선방향',
        columns='time',
        values='crowding',
        aggfunc='mean'
    )
    
    # 노선별로 정렬 (1호선-상행, 1호선-하행, 2호선-상행, ...)
    line_order = []
    for line in sorted(filtered_df['호선'].unique()):
        for direction in ['상행', '하행']:
            line_key = f"{line}-{direction}"
            if line_key in pivot_data.index:
                line_order.append(line_key)
    
    if line_order:
        pivot_data = pivot_data.reindex(line_order)
    
    # Plotly 히트맵 생성
    fig = go.Figure(data=go.Heatmap(
        z=pivot_data.values,
        x=pivot_data.columns,
        y=pivot_data.index,
        colorscale=[
            [0, 'white'],      # 0% - 흰색
            [0.34, '#ffffcc'], # 34% - 연한 노란색 (좌석 만석)
            [0.5, '#ffeda0'],  # 50% - 노란색
            [0.7, '#feb24c'],  # 70% - 주황색
            [0.85, '#fc4e2a'], # 85% - 진한 주황색
            [1, '#bd0026']     # 100%+ - 붉은색 (매우 혼잡)
        ],
        colorbar=dict(
            title=dict(
                text="혼잡도 (%)",
                side="right"
            ),
            tickmode="linear",
            tick0=0,
            dtick=20
        ),
        hovertemplate='<b>%{y}</b><br>시간: %{x}<br>혼잡도: %{z:.1f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title={
            'text': '전체 노선 시간대별 평균 혼잡도',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='시간대',
        yaxis_title='노선-방향',
        xaxis={'tickangle': -45},
        height=max(400, len(pivot_data.index) * 30),  # 노선 수에 따라 높이 조정
        hovermode='closest'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 색상 범례 설명
    st.caption("""
    💡 **색상 해석**: 
    - 🤍 흰색/연한색 (0-34%): 좌석 여유~만석 
    - 🟡 노란색 (34-70%): 입석 포함 (정원 이내)
    - 🟠 주황색 (70-100%): 혼잡 
    - 🔴 붉은색 (100% 이상): 매우 혼잡 (정원 초과)
    """)
else:
    st.info("조건에 맞는 데이터가 없습니다.")

# 하단 정보
st.markdown("---")
st.caption("Phase 2: MVP 대시보드 - 서울교통공사 지하철 혼잡도")
