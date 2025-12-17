"""
차트 이미지 생성 모듈
Plotly 차트를 PNG 이미지로 내보내기
"""
import plotly.graph_objects as go
import plotly.express as px
from typing import Optional, Dict, Any
import pandas as pd


def export_line_comparison_chart(line_summary: pd.DataFrame, output_path: str) -> str:
    """
    노선별 비교 바 차트를 PNG로 내보내기
    
    Parameters:
    -----------
    line_summary : pd.DataFrame
        노선별 요약 데이터
    output_path : str
        출력 파일 경로
    
    Returns:
    --------
    str
        생성된 파일 경로
    """
    if line_summary.empty:
        return None
    
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
        title='노선별 혼잡도 비교',
        barmode='group',
        xaxis_title='호선',
        yaxis_title='혼잡도 (%)',
        height=500,
        width=1000,
        hovermode='x unified',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        font=dict(family='Malgun Gothic', size=12)
    )
    
    # PNG로 저장
    fig.write_image(output_path, engine='kaleido')
    
    return output_path


def export_station_timeseries_chart(
    filtered_df: pd.DataFrame,
    station_name: str,
    output_path: str
) -> Optional[str]:
    """
    특정 역의 시간대별 혼잡도 라인차트를 PNG로 내보내기
    
    Parameters:
    -----------
    filtered_df : pd.DataFrame
        필터링된 데이터
    station_name : str
        역명
    output_path : str
        출력 파일 경로
    
    Returns:
    --------
    str or None
        생성된 파일 경로 (데이터 없으면 None)
    """
    station_df = filtered_df[filtered_df['역명'] == station_name].copy()
    
    if station_df.empty:
        return None
    
    # 방향별로 그룹화하여 평균 계산
    station_agg = station_df.groupby(['time', 'hour', 'minute', 'time_order', '상하선구분']).agg({
        'crowding': 'mean'
    }).reset_index()
    
    # 시간 순서대로 정렬
    station_agg = station_agg.sort_values('time_order')
    
    if station_agg.empty:
        return None
    
    # Plotly 라인차트
    fig = px.line(
        station_agg,
        x='time',
        y='crowding',
        color='상하선구분',
        markers=True,
        title=f"{station_name}역 시간대별 혼잡도",
        labels={
            'time': '시간대',
            'crowding': '혼잡도 (%)',
            '상하선구분': '방향'
        }
    )
    
    fig.update_layout(
        xaxis_tickangle=-45,
        hovermode='x unified',
        height=400,
        width=1000,
        font=dict(family='Malgun Gothic', size=11)
    )
    
    # PNG로 저장
    fig.write_image(output_path, engine='kaleido')
    
    return output_path


def export_heatmap_chart(
    filtered_df: pd.DataFrame,
    output_path: str
) -> Optional[str]:
    """
    전체 노선 시간대별 혼잡도 히트맵을 PNG로 내보내기
    
    Parameters:
    -----------
    filtered_df : pd.DataFrame
        필터링된 데이터
    output_path : str
        출력 파일 경로
    
    Returns:
    --------
    str or None
        생성된 파일 경로 (데이터 없으면 None)
    """
    # 노선별, 방향별, 시간대별 평균 혼잡도 계산
    heatmap_data = filtered_df.groupby(['호선', '상하선구분', 'time', 'time_order']).agg({
        'crowding': 'mean'
    }).reset_index()
    
    # 노선+방향 컬럼 생성
    heatmap_data['노선방향'] = heatmap_data['호선'] + '-' + heatmap_data['상하선구분']
    
    if heatmap_data.empty:
        return None
    
    # 시간 순서대로 정렬
    heatmap_data = heatmap_data.sort_values('time_order')
    
    # 피벗 테이블 생성
    pivot_data = heatmap_data.pivot_table(
        index='노선방향',
        columns='time',
        values='crowding',
        aggfunc='mean'
    )
    
    # 노선별로 정렬
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
            [0, 'white'],
            [0.34, '#ffffcc'],
            [0.5, '#ffeda0'],
            [0.7, '#feb24c'],
            [0.85, '#fc4e2a'],
            [1, '#bd0026']
        ],
        colorbar=dict(
            title=dict(text="혼잡도 (%)", side="right"),
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
        height=max(400, len(pivot_data.index) * 30),
        width=1200,
        hovermode='closest',
        font=dict(family='Malgun Gothic', size=10)
    )
    
    # PNG로 저장
    fig.write_image(output_path, engine='kaleido')
    
    return output_path


def create_kpi_chart(kpi_data: Dict[str, Any], output_path: str) -> str:
    """
    KPI 3종을 시각화한 차트 생성
    
    Parameters:
    -----------
    kpi_data : Dict[str, Any]
        KPI 데이터
    output_path : str
        출력 파일 경로
    
    Returns:
    --------
    str
        생성된 파일 경로
    """
    labels = ['최대 피크', '출근 평균', '퇴근 평균']
    values = [
        kpi_data['peak_crowding'],
        kpi_data['commute_avg'],
        kpi_data['evening_avg']
    ]
    
    colors = ['#E74C3C', '#F39C12', '#9B59B6']
    
    fig = go.Figure(data=[
        go.Bar(
            x=labels,
            y=values,
            text=[f'{v:.1f}%' for v in values],
            textposition='outside',
            marker_color=colors
        )
    ])
    
    fig.update_layout(
        title='주요 혼잡도 지표',
        xaxis_title='지표',
        yaxis_title='혼잡도 (%)',
        height=400,
        width=800,
        font=dict(family='Malgun Gothic', size=12)
    )
    
    # PNG로 저장
    fig.write_image(output_path, engine='kaleido')
    
    return output_path


def create_top10_bar_chart(
    top10_df: pd.DataFrame,
    metric_name: str,
    title: str,
    output_path: str
) -> Optional[str]:
    """
    TOP10 수평 바 차트 생성
    
    Parameters:
    -----------
    top10_df : pd.DataFrame
        TOP10 데이터프레임
    metric_name : str
        지표 컬럼명 (예: '피크혼잡', '출근평균', '퇴근평균')
    title : str
        차트 제목
    output_path : str
        출력 파일 경로
    
    Returns:
    --------
    str or None
        생성된 파일 경로 (데이터 없으면 None)
    """
    if top10_df.empty:
        return None
    
    # 역명 + 방향 조합
    top10_df = top10_df.copy()
    top10_df['역명_방향'] = top10_df['역명'] + '\n(' + top10_df['상하선구분'] + ')'
    
    # 내림차순 정렬
    top10_df = top10_df.sort_values(metric_name, ascending=True)
    
    fig = go.Figure(data=[
        go.Bar(
            y=top10_df['역명_방향'],
            x=top10_df[metric_name],
            orientation='h',
            text=top10_df[metric_name].apply(lambda x: f'{x:.1f}%'),
            textposition='outside',
            marker_color='#3498DB'
        )
    ])
    
    fig.update_layout(
        title=title,
        xaxis_title='혼잡도 (%)',
        yaxis_title='역명',
        height=500,
        width=900,
        font=dict(family='Malgun Gothic', size=11)
    )
    
    # PNG로 저장
    fig.write_image(output_path, engine='kaleido')
    
    return output_path

