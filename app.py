"""
서울교통공사 지하철 혼잡도 대시보드
Phase 5: 지도 시각화 포함
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import os
import tempfile
from datetime import datetime

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
    get_station_full_summary,
    get_station_crowding_for_map
)

from reporting.collector import collect_report_data, generate_yaml_snapshot
from reporting.renderer_pdf import generate_pdf_report

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

st.sidebar.markdown("---")
st.sidebar.subheader("📥 데이터 다운로드")

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
    st.sidebar.info("필터 조건에 맞는 데이터가 없어 다운로드할 수 없습니다.")
    st.stop()

# ========================================
# KPI 계산 (보고서에서도 사용)
# ========================================
peak_crowding, peak_time = calculate_peak(filtered_df)
commute_avg = calculate_commute_avg(filtered_df, include_9=include_9)
evening_avg = calculate_evening_avg(filtered_df, include_20=include_20)

# TOP10 데이터 (보고서에서도 사용)
top10_peak = get_peak_top10(filtered_df)
top10_commute = get_commute_top10(filtered_df, include_9=include_9)
top10_evening = get_evening_top10(filtered_df, include_20=include_20)

# 요약 데이터 (보고서에서도 사용)
line_summary = get_line_summary(filtered_df, include_9=include_9, include_20=include_20)
station_summary = get_station_full_summary(filtered_df, include_9=include_9, include_20=include_20)

# ========================================
# 사이드바 다운로드 버튼
# ========================================
# 필터링된 전체 데이터 다운로드
csv_data = filtered_df.to_csv(index=False, encoding='utf-8-sig')
st.sidebar.download_button(
    label="필터 적용 데이터 다운로드 (CSV)",
    data=csv_data,
    file_name=f"혼잡도_필터적용_{ref_date}.csv",
    mime="text/csv",
    help="현재 필터 조건에 맞는 전체 데이터를 다운로드합니다"
)

# ========================================
# PDF 보고서 생성 (Phase 6)
# ========================================
st.sidebar.markdown("---")
st.sidebar.subheader("📄 보고서 생성")

if st.sidebar.button("PDF 보고서 생성", type="primary"):
    with st.spinner("보고서를 생성하는 중..."):
        pdf_path = None
        try:
            # 보고서 데이터 수집
            report_data = collect_report_data(
                filtered_df=filtered_df,
                ref_date=ref_date,
                filters={
                    'selected_days': selected_days,
                    'selected_lines': selected_lines,
                    'selected_directions': selected_directions,
                    'station_search': station_search,
                    'include_9': include_9,
                    'include_20': include_20
                },
                kpi_data={
                    'peak_crowding': peak_crowding,
                    'peak_time': peak_time,
                    'commute_avg': commute_avg,
                    'evening_avg': evening_avg
                },
                top10_data={
                    'peak': top10_peak,
                    'commute': top10_commute,
                    'evening': top10_evening
                },
                line_summary=line_summary,
                station_summary=station_summary
            )
            
            # 임시 파일로 PDF 생성 (한글 경로 문제 방지)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            temp_dir = tempfile.gettempdir()
            # 파일명을 영문으로 변경하여 경로 문제 방지
            pdf_path = os.path.join(temp_dir, f"subway_report_{ref_date}_{timestamp}.pdf")
            
            # PDF 생성
            st.sidebar.info("📝 PDF 보고서 생성 중...")
            generate_pdf_report(report_data, pdf_path)
            
            # 생성된 PDF 읽기
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
            # 임시 파일 삭제
            try:
                os.remove(pdf_path)
            except:
                pass
            
            # 다운로드 버튼 제공
            st.sidebar.download_button(
                label="📥 보고서 다운로드 (PDF)",
                data=pdf_bytes,
                file_name=f"혼잡도_보고서_{ref_date}.pdf",
                mime="application/pdf",
                key="pdf_download"
            )
            
            # YAML 스냅샷도 제공
            yaml_snapshot = generate_yaml_snapshot(report_data)
            st.sidebar.download_button(
                label="📥 설정 스냅샷 다운로드 (YAML)",
                data=yaml_snapshot,
                file_name=f"보고서_설정_{ref_date}.yaml",
                mime="text/yaml",
                key="yaml_download"
            )
            
            st.sidebar.success("✅ 보고서가 생성되었습니다!")
            st.sidebar.info("💡 위의 버튼을 클릭하여 다운로드하세요.")
            
        except Exception as e:
            st.sidebar.error(f"❌ 보고서 생성 실패: {str(e)}")
            # 자세한 오류 정보 표시 (디버깅용)
            import traceback
            with st.sidebar.expander("🔍 오류 상세 정보"):
                st.code(traceback.format_exc())
            
            # 임시 파일 정리
            if pdf_path and os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                except:
                    pass

# ========================================
# KPI 메트릭
# ========================================
st.markdown("---")
st.subheader("📈 주요 지표")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "최대 피크 혼잡",
        f"{peak_crowding:.1f}%",
        help="선택된 범위 내 최대 혼잡도"
    )
    st.caption(f"발생 시간: {peak_time}")

with col2:
    time_range = "7~9시" if include_9 else "7~9시 미만"
    st.metric(
        f"출근시간 평균 ({time_range})",
        f"{commute_avg:.1f}%",
        help="출근 시간대 평균 혼잡도"
    )

with col3:
    time_range = "17~20시" if include_20 else "17~20시 미만"
    st.metric(
        f"퇴근시간 평균 ({time_range})",
        f"{evening_avg:.1f}%",
        help="퇴근 시간대 평균 혼잡도"
    )

# ========================================
# 랭킹 TOP10 탭
# ========================================
st.markdown("---")
st.subheader("🔥 혼잡도 랭킹 TOP 10")

tab1, tab2, tab3 = st.tabs(["피크 TOP10", "출근 평균 TOP10", "퇴근 평균 TOP10"])

with tab1:
    st.markdown("##### 피크 혼잡도 기준")
    if not top10_peak.empty:
        display_df = top10_peak.copy()
        display_df['피크혼잡'] = display_df['피크혼잡'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
        
        csv_top10 = display_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 피크 TOP10 다운로드 (CSV)",
            data=csv_top10,
            file_name=f"피크TOP10_{ref_date}.csv",
            mime="text/csv"
        )
    else:
        st.info("조건에 맞는 데이터가 없습니다.")

with tab2:
    time_range = "7~9시" if include_9 else "7~9시 미만"
    st.markdown(f"##### 출근시간({time_range}) 평균 혼잡도 기준")
    if not top10_commute.empty:
        display_df = top10_commute.copy()
        display_df['출근평균'] = display_df['출근평균'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
        
        csv_commute = display_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 출근평균 TOP10 다운로드 (CSV)",
            data=csv_commute,
            file_name=f"출근평균TOP10_{ref_date}.csv",
            mime="text/csv"
        )
    else:
        st.info("조건에 맞는 데이터가 없습니다.")

with tab3:
    time_range = "17~20시" if include_20 else "17~20시 미만"
    st.markdown(f"##### 퇴근시간({time_range}) 평균 혼잡도 기준")
    if not top10_evening.empty:
        display_df = top10_evening.copy()
        display_df['퇴근평균'] = display_df['퇴근평균'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
        
        csv_evening = display_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 퇴근평균 TOP10 다운로드 (CSV)",
            data=csv_evening,
            file_name=f"퇴근평균TOP10_{ref_date}.csv",
            mime="text/csv"
        )
    else:
        st.info("조건에 맞는 데이터가 없습니다.")

# ========================================
# 노선별 비교 차트
# ========================================
st.markdown("---")
st.subheader("🚆 노선별 혼잡도 비교")

if not line_summary.empty:
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='전체 평균',
        x=line_summary['호선'],
        y=line_summary['평균혼잡'],
        marker_color='lightblue',
        text=line_summary['평균혼잡'].apply(lambda x: f'{x:.1f}%'),
        textposition='outside'
    ))
    
    fig.add_trace(go.Bar(
        name='피크',
        x=line_summary['호선'],
        y=line_summary['피크혼잡'],
        marker_color='red',
        text=line_summary['피크혼잡'].apply(lambda x: f'{x:.1f}%'),
        textposition='outside'
    ))
    
    fig.add_trace(go.Bar(
        name='출근 평균',
        x=line_summary['호선'],
        y=line_summary['출근평균'],
        marker_color='orange',
        text=line_summary['출근평균'].apply(lambda x: f'{x:.1f}%'),
        textposition='outside'
    ))
    
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
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("📋 노선별 상세 수치 보기"):
        display_summary = line_summary.copy()
        display_summary['평균혼잡'] = display_summary['평균혼잡'].apply(lambda x: f"{x:.1f}%")
        display_summary['피크혼잡'] = display_summary['피크혼잡'].apply(lambda x: f"{x:.1f}%")
        display_summary['출근평균'] = display_summary['출근평균'].apply(lambda x: f"{x:.1f}%")
        display_summary['퇴근평균'] = display_summary['퇴근평균'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(display_summary, use_container_width=True, hide_index=True)
else:
    st.info("조건에 맞는 데이터가 없습니다.")

# ========================================
# 역 선택 시간대별 라인차트
# ========================================
st.markdown("---")
st.subheader("📊 역별 시간대별 혼잡도")

available_stations = sorted(filtered_df['역명'].unique().tolist())

if available_stations:
    selected_station = st.selectbox("역 선택", options=available_stations, index=0)
    
    station_df = filtered_df[filtered_df['역명'] == selected_station].copy()
    station_agg = station_df.groupby(['time', 'hour', 'minute', 'time_order', '상하선구분']).agg({
        'crowding': 'mean'
    }).reset_index()
    station_agg = station_agg.sort_values('time_order')
    
    if not station_agg.empty:
        fig = px.line(
            station_agg,
            x='time',
            y='crowding',
            color='상하선구분',
            markers=True,
            title=f"{selected_station}역 시간대별 혼잡도",
            labels={'time': '시간대', 'crowding': '혼잡도 (%)', '상하선구분': '방향'}
        )
        fig.update_layout(xaxis_tickangle=-45, hovermode='x unified', height=500)
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

if not station_summary.empty:
    display_summary = station_summary.copy()
    display_summary['피크혼잡'] = display_summary['피크혼잡'].apply(lambda x: f"{x:.1f}%")
    display_summary['출근평균'] = display_summary['출근평균'].apply(lambda x: f"{x:.1f}%")
    display_summary['퇴근평균'] = display_summary['퇴근평균'].apply(lambda x: f"{x:.1f}%")
    
    st.dataframe(display_summary, use_container_width=True, hide_index=True, height=400)
    
    csv_station_summary = display_summary.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 역별 종합 요약 다운로드 (CSV)",
        data=csv_station_summary,
        file_name=f"역별종합요약_{ref_date}.csv",
        mime="text/csv"
    )
    
    st.caption(f"💡 출근평균: 7~9시{'(9시 포함)' if include_9 else ''} | 퇴근평균: 17~20시{'(20시 포함)' if include_20 else ''}")
else:
    st.info("조건에 맞는 데이터가 없습니다.")

# ========================================
# 전체 노선 시간대별 혼잡도 히트맵
# ========================================
st.markdown("---")
st.subheader("🌡️ 전체 노선 시간대별 혼잡도 히트맵")

heatmap_data = filtered_df.groupby(['호선', '상하선구분', 'time', 'time_order']).agg({
    'crowding': 'mean'
}).reset_index()

heatmap_data['노선방향'] = heatmap_data['호선'] + '-' + heatmap_data['상하선구분']

if not heatmap_data.empty:
    heatmap_data = heatmap_data.sort_values('time_order')
    
    pivot_data = heatmap_data.pivot_table(
        index='노선방향',
        columns='time',
        values='crowding',
        aggfunc='mean'
    )
    
    line_order = []
    for line in sorted(filtered_df['호선'].unique()):
        for direction in ['상행', '하행']:
            line_key = f"{line}-{direction}"
            if line_key in pivot_data.index:
                line_order.append(line_key)
    
    if line_order:
        pivot_data = pivot_data.reindex(line_order)
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_data.values,
        x=pivot_data.columns,
        y=pivot_data.index,
        colorscale=[
            [0, 'white'],
            [0.34, '#ffffcc'],
            [0.5, '#ffeda0'],
            [0.7, '#feb24c'],
            [0.85, '#fc4e2a'],
            [1, '#bd0026']
        ],
        colorbar=dict(title=dict(text="혼잡도 (%)", side="right"), tickmode="linear", tick0=0, dtick=20),
        hovertemplate='<b>%{y}</b><br>시간: %{x}<br>혼잡도: %{z:.1f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title={'text': '전체 노선 시간대별 평균 혼잡도', 'x': 0.5, 'xanchor': 'center'},
        xaxis_title='시간대',
        yaxis_title='노선-방향',
        xaxis={'tickangle': -45},
        height=max(400, len(pivot_data.index) * 30),
        hovermode='closest'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.caption("""
    💡 **색상 해석**: 
    - 🤍 흰색/연한색 (0-34%): 좌석 여유~만석 
    - 🟡 노란색 (34-70%): 입석 포함 (정원 이내)
    - 🟠 주황색 (70-100%): 혼잡 
    - 🔴 붉은색 (100% 이상): 매우 혼잡 (정원 초과)
    """)
else:
    st.info("조건에 맞는 데이터가 없습니다.")

# ========================================
# 역별 혼잡도 지도 시각화
# ========================================
st.markdown("---")
st.subheader("🗺️ 역별 혼잡도 지도")

col_map1, col_map2 = st.columns([1, 3])

with col_map1:
    st.markdown("##### 지도 표시 옵션")
    
    crowding_type = st.radio(
        "혼잡도 기준",
        options=["average", "peak", "commute", "evening"],
        format_func=lambda x: {
            "average": "전체 평균",
            "peak": "피크 혼잡",
            "commute": f"출근 평균 (7~9시{'포함' if include_9 else '미만'})",
            "evening": f"퇴근 평균 (17~20시{'포함' if include_20 else '미만'})"
        }[x],
        index=0,
        help="지도에 표시할 혼잡도 기준을 선택합니다"
    )
    
    st.markdown("##### 색상 범례")
    st.markdown("""
    <div style='font-size: 0.9em;'>
    🟢 <strong>초록색 (0-34%)</strong><br/>
    &nbsp;&nbsp;&nbsp;좌석 여유~만석<br/><br/>
    🟡 <strong>노란색 (34-70%)</strong><br/>
    &nbsp;&nbsp;&nbsp;입석 포함 (정원 이내)<br/><br/>
    🟠 <strong>주황색 (70-100%)</strong><br/>
    &nbsp;&nbsp;&nbsp;혼잡<br/><br/>
    🔴 <strong>빨간색 (100%+)</strong><br/>
    &nbsp;&nbsp;&nbsp;매우 혼잡 (정원 초과)
    </div>
    """, unsafe_allow_html=True)

with col_map2:
    map_data = get_station_crowding_for_map(
        filtered_df, 
        crowding_type=crowding_type,
        include_9=include_9,
        include_20=include_20
    )
    
    if not map_data.empty:
        m = folium.Map(location=[37.5665, 126.9780], zoom_start=11, tiles='OpenStreetMap')
        
        def get_color(crowding):
            if crowding < 34:
                return '#2ECC71'
            elif crowding < 70:
                return '#F1C40F'
            elif crowding < 100:
                return '#E67E22'
            else:
                return '#E74C3C'
        
        def get_radius(crowding):
            min_radius = 5
            max_radius = 20
            normalized = min(crowding / 150, 1.0)
            return min_radius + (max_radius - min_radius) * normalized
        
        for _, row in map_data.iterrows():
            crowding = row['crowding_value']
            color = get_color(crowding)
            radius = get_radius(crowding)
            
            popup_html = f"""
            <div style='font-family: Arial; min-width: 200px;'>
                <h4 style='margin: 0 0 10px 0; color: #2C3E50;'>{row['역명']}역</h4>
                <p style='margin: 5px 0;'><strong>호선:</strong> {row['호선']}</p>
                <p style='margin: 5px 0;'><strong>혼잡도:</strong> {crowding:.1f}%</p>
                <p style='margin: 5px 0; font-size: 0.9em; color: #7F8C8D;'>
                    {'🟢 여유' if crowding < 34 else '🟡 보통' if crowding < 70 else '🟠 혼잡' if crowding < 100 else '🔴 매우 혼잡'}
                </p>
            </div>
            """
            
            folium.CircleMarker(
                location=[row['lat'], row['lng']],
                radius=radius,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{row['역명']}역: {crowding:.1f}%",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=2
            ).add_to(m)
        
        st_folium(m, width=None, height=600)
        
        st.caption(f"""
        💡 **지도 정보**: 
        총 {len(map_data)}개 역 표시 | 
        평균 혼잡도: {map_data['crowding_value'].mean():.1f}% | 
        최고 혼잡도: {map_data['crowding_value'].max():.1f}% ({map_data.iloc[0]['역명']}역)
        """)
    else:
        st.info("조건에 맞는 데이터가 없거나 위경도 정보가 없는 역입니다.")

# 하단 정보
st.markdown("---")
st.caption("Phase 6: PDF 보고서 생성 - 서울교통공사 지하철 혼잡도")
