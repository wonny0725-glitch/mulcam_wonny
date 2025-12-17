"""
보고서 데이터 수집 모듈
대시보드 상태에서 필터/KPI/분석 결과를 수집하여 보고서용 데이터팩 생성
"""
import pandas as pd
import yaml
from datetime import datetime
from typing import Dict, Any, List


def collect_report_data(
    filtered_df: pd.DataFrame,
    ref_date: str,
    filters: Dict[str, Any],
    kpi_data: Dict[str, Any],
    top10_data: Dict[str, pd.DataFrame],
    line_summary: pd.DataFrame,
    station_summary: pd.DataFrame
) -> Dict[str, Any]:
    """
    보고서 생성을 위한 전체 데이터 수집
    
    Parameters:
    -----------
    filtered_df : pd.DataFrame
        필터 적용된 원본 데이터
    ref_date : str
        기준일 (YYYY-MM-DD)
    filters : Dict
        사용자가 선택한 필터 조건
        - selected_days: List[str]
        - selected_lines: List[str]
        - selected_directions: List[str]
        - station_search: str
        - include_9: bool
        - include_20: bool
    kpi_data : Dict
        KPI 3종 데이터
        - peak_crowding: float
        - peak_time: str
        - commute_avg: float
        - evening_avg: float
    top10_data : Dict[str, pd.DataFrame]
        TOP10 데이터프레임
        - peak: 피크 TOP10
        - commute: 출근 TOP10
        - evening: 퇴근 TOP10
    line_summary : pd.DataFrame
        노선별 요약
    station_summary : pd.DataFrame
        역별 종합 요약
    
    Returns:
    --------
    Dict[str, Any]
        보고서 생성에 필요한 모든 데이터
    """
    # 필터 데이터 검증 및 정리
    safe_filters = {
        'selected_days': filters.get('selected_days', []),
        'selected_lines': filters.get('selected_lines', []),
        'selected_directions': filters.get('selected_directions', []),
        'station_search': filters.get('station_search', ''),
        'include_9': filters.get('include_9', True),
        'include_20': filters.get('include_20', True)
    }
    
    # KPI 데이터 검증
    safe_kpi = {
        'peak_crowding': float(kpi_data.get('peak_crowding', 0.0)),
        'peak_time': str(kpi_data.get('peak_time', 'N/A')),
        'commute_avg': float(kpi_data.get('commute_avg', 0.0)),
        'evening_avg': float(kpi_data.get('evening_avg', 0.0))
    }
    
    # TOP10 데이터 안전하게 변환
    safe_top10 = {}
    for key in ['peak', 'commute', 'evening']:
        df = top10_data.get(key, pd.DataFrame())
        if isinstance(df, pd.DataFrame) and not df.empty:
            safe_top10[key] = df.to_dict('records')
        else:
            safe_top10[key] = []
    
    # 요약 데이터 안전하게 변환
    safe_line_summary = []
    if isinstance(line_summary, pd.DataFrame) and not line_summary.empty:
        safe_line_summary = line_summary.to_dict('records')
    
    safe_station_summary = []
    if isinstance(station_summary, pd.DataFrame) and not station_summary.empty:
        safe_station_summary = station_summary.to_dict('records')
    
    report_data = {
        'metadata': {
            'ref_date': ref_date,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'organization': '서울교통공사',
            'report_title': '서울 지하철 혼잡도 분석 보고서',
            'version': '1.0.0'
        },
        'filters': safe_filters,
        'kpi': safe_kpi,
        'top10': safe_top10,
        'line_summary': safe_line_summary,
        'station_summary': safe_station_summary,
        'statistics': {
            'total_records': len(filtered_df) if not filtered_df.empty else 0,
            'unique_stations': filtered_df['역명'].nunique() if not filtered_df.empty else 0,
            'unique_lines': filtered_df['호선'].nunique() if not filtered_df.empty else 0
        }
    }
    
    return report_data


def generate_summary_insights(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    보고서 요약 페이지용 핵심 인사이트 생성
    
    Parameters:
    -----------
    report_data : Dict[str, Any]
        수집된 보고서 데이터
    
    Returns:
    --------
    Dict[str, Any]
        요약 인사이트
    """
    kpi = report_data['kpi']
    top10 = report_data['top10']
    
    insights = {
        'peak_issue': None,
        'commute_issue': None,
        'evening_issue': None,
        'top_crowded_line': None,
        'top_crowded_station': None
    }
    
    # 피크 혼잡 이슈
    if kpi['peak_crowding'] > 0:
        insights['peak_issue'] = {
            'crowding': kpi['peak_crowding'],
            'time': kpi['peak_time'],
            'severity': get_severity_level(kpi['peak_crowding'])
        }
    
    # 출근시간 이슈
    if kpi['commute_avg'] > 0:
        insights['commute_issue'] = {
            'avg_crowding': kpi['commute_avg'],
            'severity': get_severity_level(kpi['commute_avg'])
        }
    
    # 퇴근시간 이슈
    if kpi['evening_avg'] > 0:
        insights['evening_issue'] = {
            'avg_crowding': kpi['evening_avg'],
            'severity': get_severity_level(kpi['evening_avg'])
        }
    
    # 최고 혼잡 역 (피크 TOP10의 1위)
    if top10['peak']:
        top_station = top10['peak'][0]
        insights['top_crowded_station'] = {
            'name': top_station['역명'],
            'line': top_station['호선'],
            'direction': top_station['상하선구분'],
            'crowding': top_station['피크혼잡'],
            'time': top_station['피크시간']
        }
    
    # 최고 혼잡 노선
    if report_data['line_summary']:
        lines = report_data['line_summary']
        top_line = max(lines, key=lambda x: x['피크혼잡'])
        insights['top_crowded_line'] = {
            'name': top_line['호선'],
            'peak_crowding': top_line['피크혼잡'],
            'avg_crowding': top_line['평균혼잡']
        }
    
    return insights


def get_severity_level(crowding: float) -> str:
    """
    혼잡도에 따른 심각도 레벨 반환
    
    Parameters:
    -----------
    crowding : float
        혼잡도 (%)
    
    Returns:
    --------
    str
        심각도 레벨 (normal/moderate/high/critical)
    """
    if crowding < 34:
        return 'normal'  # 좌석 여유~만석
    elif crowding < 70:
        return 'moderate'  # 입석 포함 (정원 이내)
    elif crowding < 100:
        return 'high'  # 혼잡
    else:
        return 'critical'  # 매우 혼잡 (정원 초과)


def generate_yaml_snapshot(report_data: Dict[str, Any]) -> str:
    """
    재현용 YAML 스냅샷 생성
    
    Parameters:
    -----------
    report_data : Dict[str, Any]
        보고서 데이터
    
    Returns:
    --------
    str
        YAML 형식 문자열
    """
    # 간략화된 스냅샷 (메타데이터 + 필터 + KPI만)
    snapshot = {
        'metadata': report_data['metadata'],
        'filters': report_data['filters'],
        'kpi': report_data['kpi'],
        'statistics': report_data['statistics']
    }
    
    return yaml.dump(snapshot, allow_unicode=True, default_flow_style=False)


def format_top10_for_report(top10_df: pd.DataFrame, metric_name: str) -> List[Dict[str, Any]]:
    """
    TOP10 데이터프레임을 보고서용 형식으로 변환
    
    Parameters:
    -----------
    top10_df : pd.DataFrame
        TOP10 데이터프레임
    metric_name : str
        지표 컬럼명 (예: '피크혼잡', '출근평균', '퇴근평균')
    
    Returns:
    --------
    List[Dict[str, Any]]
        보고서용 포맷 리스트
    """
    if top10_df.empty:
        return []
    
    formatted = []
    for idx, row in top10_df.iterrows():
        item = {
            'rank': idx + 1,
            'station': row['역명'],
            'line': row['호선'],
            'direction': row['상하선구분'],
            'crowding': row[metric_name]
        }
        
        # 피크시간 정보가 있으면 추가
        if '피크시간' in row:
            item['time'] = row['피크시간']
        
        formatted.append(item)
    
    return formatted

