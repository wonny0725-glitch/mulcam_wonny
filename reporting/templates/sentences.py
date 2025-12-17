"""
보고서 문장 템플릿
운영 권고안 및 해석 문구 생성
"""
from typing import Dict, Any, List


def generate_recommendations(report_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    보고서 데이터 기반 운영 권고안 생성
    
    Parameters:
    -----------
    report_data : Dict[str, Any]
        보고서 데이터
    
    Returns:
    --------
    List[Dict[str, str]]
        권고안 리스트 (각 항목은 category, title, content 포함)
    """
    recommendations = []
    
    kpi = report_data['kpi']
    top10 = report_data['top10']
    line_summary = report_data['line_summary']
    
    # 1. 피크 혼잡도 기반 권고안
    if kpi['peak_crowding'] > 100:
        # 정원 초과 (매우 혼잡)
        recommendations.append({
            'category': '즉시',
            'priority': 1,
            'title': '정원 초과 구간 배차 간격 조정',
            'content': f"최대 피크 혼잡도가 {kpi['peak_crowding']:.1f}%로 정원을 초과하였습니다. "
                      f"{kpi['peak_time']} 시간대에 배차 간격을 단축하여 승객 분산을 유도해야 합니다."
        })
    elif kpi['peak_crowding'] > 70:
        # 혼잡
        recommendations.append({
            'category': '단기',
            'priority': 2,
            'title': '혼잡 시간대 모니터링 강화',
            'content': f"피크 혼잡도가 {kpi['peak_crowding']:.1f}%로 혼잡 수준입니다. "
                      f"{kpi['peak_time']} 시간대 모니터링을 강화하고 승객 안내를 강화해야 합니다."
        })
    
    # 2. TOP 혼잡 역 기반 권고안
    if top10['peak']:
        top_station = top10['peak'][0]
        peak_crowding = top_station.get('피크혼잡', 0.0)
        if peak_crowding > 100:
            recommendations.append({
                'category': '즉시',
                'priority': 1,
                'title': f"{top_station.get('역명', 'N/A')}역 혼잡 완화 조치",
                'content': f"{top_station.get('역명', 'N/A')}역 ({top_station.get('호선', 'N/A')}, {top_station.get('상하선구분', 'N/A')})의 "
                          f"피크 혼잡도가 {peak_crowding:.1f}%로 매우 높습니다. "
                          f"승강장 정리 인력 배치 및 이용객 분산 유도 안내가 필요합니다."
            })
        
        # TOP 3 역이 모두 같은 호선인 경우
        if len(top10['peak']) >= 3:
            top3_lines = [s['호선'] for s in top10['peak'][:3]]
            if len(set(top3_lines)) == 1:
                line = top3_lines[0]
                recommendations.append({
                    'category': '단기',
                    'priority': 2,
                    'title': f"{line} 전반적 혼잡도 개선",
                    'content': f"{line}의 여러 역이 TOP 3에 포함되어 있습니다. "
                              f"노선 전체의 배차 계획을 재검토하고 증편을 고려해야 합니다."
                })
    
    # 3. 출근시간 혼잡 권고안
    if kpi['commute_avg'] > 70:
        recommendations.append({
            'category': '단기',
            'priority': 2,
            'title': '출근시간대 시차 출근 유도',
            'content': f"출근시간대 평균 혼잡도가 {kpi['commute_avg']:.1f}%입니다. "
                      f"기업 및 기관과 협력하여 시차 출근제 확대를 유도하고, "
                      f"혼잡 정보 실시간 제공을 통해 승객 분산을 유도해야 합니다."
        })
    
    # 4. 퇴근시간 혼잡 권고안
    if kpi['evening_avg'] > 70:
        recommendations.append({
            'category': '단기',
            'priority': 2,
            'title': '퇴근시간대 배차 간격 최적화',
            'content': f"퇴근시간대 평균 혼잡도가 {kpi['evening_avg']:.1f}%입니다. "
                      f"17~20시 시간대의 배차 간격을 조정하여 혼잡을 완화해야 합니다."
        })
    
    # 5. 노선별 권고안
    if line_summary:
        high_congestion_lines = [l for l in line_summary if l['피크혼잡'] > 90]
        if high_congestion_lines:
            line_names = ', '.join([l['호선'] for l in high_congestion_lines])
            recommendations.append({
                'category': '중기',
                'priority': 3,
                'title': '고혼잡 노선 운영 계획 재설계',
                'content': f"{line_names}의 피크 혼잡도가 90%를 초과합니다. "
                          f"중장기적으로 차량 증편, 노선 재조정, 또는 대체 교통수단 연계를 검토해야 합니다."
            })
    
    # 6. 일반 권고안 (항상 포함)
    recommendations.append({
        'category': '즉시',
        'priority': 3,
        'title': '실시간 혼잡도 정보 제공 강화',
        'content': '승객이 혼잡 시간대를 피할 수 있도록 역사 및 모바일 앱을 통한 실시간 혼잡도 정보 제공을 강화해야 합니다.'
    })
    
    recommendations.append({
        'category': '중기',
        'priority': 3,
        'title': '데이터 기반 모니터링 체계 구축',
        'content': '혼잡도 데이터를 지속적으로 수집·분석하여 계절별, 요일별 패턴을 파악하고 선제적 대응 체계를 구축해야 합니다.'
    })
    
    # 우선순위 및 카테고리별 정렬
    recommendations.sort(key=lambda x: (x['priority'], x['category']))
    
    return recommendations


def get_severity_description(crowding: float) -> str:
    """
    혼잡도에 따른 상태 설명 반환
    
    Parameters:
    -----------
    crowding : float
        혼잡도 (%)
    
    Returns:
    --------
    str
        상태 설명
    """
    if crowding < 34:
        return "좌석 여유 ~ 좌석 만석"
    elif crowding < 70:
        return "입석 포함 (정원 이내)"
    elif crowding < 100:
        return "혼잡"
    else:
        return "매우 혼잡 (정원 초과)"


def generate_executive_summary(report_data: Dict[str, Any]) -> str:
    """
    경영진용 요약문 생성
    
    Parameters:
    -----------
    report_data : Dict[str, Any]
        보고서 데이터
    
    Returns:
    --------
    str
        요약문 (3~5줄)
    """
    kpi = report_data['kpi']
    top10 = report_data['top10']
    stats = report_data['statistics']
    
    summary_parts = []
    
    # 기본 정보
    summary_parts.append(
        f"{stats['unique_lines']}개 호선, {stats['unique_stations']}개 역을 대상으로 혼잡도를 분석한 결과, "
    )
    
    # 피크 정보
    if top10['peak']:
        top_station = top10['peak'][0]
        summary_parts.append(
            f"{top_station.get('역명', 'N/A')}역 ({top_station.get('호선', 'N/A')})에서 "
            f"{kpi.get('peak_time', 'N/A')}에 최대 {kpi.get('peak_crowding', 0.0):.1f}%의 혼잡도를 기록하였습니다. "
        )
    
    # 출퇴근 평균
    summary_parts.append(
        f"출근시간대 평균 혼잡도는 {kpi['commute_avg']:.1f}%, "
        f"퇴근시간대 평균 혼잡도는 {kpi['evening_avg']:.1f}%로 나타났습니다. "
    )
    
    # 권고사항
    if kpi['peak_crowding'] > 100:
        summary_parts.append(
            "정원을 초과하는 구간에 대해 즉각적인 배차 조정 및 승객 분산 유도가 필요합니다."
        )
    elif kpi['peak_crowding'] > 70:
        summary_parts.append(
            "혼잡 시간대 모니터링 강화 및 승객 안내 개선이 필요합니다."
        )
    else:
        summary_parts.append(
            "전반적으로 안정적인 운영 상태이나, 지속적인 모니터링이 필요합니다."
        )
    
    return ''.join(summary_parts)

