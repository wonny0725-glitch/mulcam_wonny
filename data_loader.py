"""
데이터 로딩 및 전처리 모듈
서울교통공사 지하철 혼잡도 CSV 파일을 로딩하고 long format으로 변환
"""
import streamlit as st
import pandas as pd
import re
import glob
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime
from station_coords import STATION_COORDS


def find_csv_file() -> Optional[str]:
    """현재 폴더에서 혼잡도 CSV 파일 자동 탐색"""
    pattern = "*혼잡도*.csv"
    files = glob.glob(pattern)
    if files:
        return files[0]
    return None


def parse_reference_date(filename: str) -> Optional[str]:
    """
    파일명에서 기준일 파싱
    예: 서울교통공사_지하철혼잡도정보_20250930.csv -> 2025-09-30
    """
    match = re.search(r'(\d{8})', filename)
    if match:
        date_str = match.group(1)
        try:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            return None
    return None


def load_csv_with_encoding(filepath: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    다양한 인코딩으로 CSV 로딩 시도
    cp949 -> euc-kr -> utf-8 순으로 시도
    """
    encodings = ['cp949', 'euc-kr', 'utf-8']
    
    for encoding in encodings:
        try:
            df = pd.read_csv(filepath, encoding=encoding)
            return df, None
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return None, f"파일 읽기 오류 ({encoding}): {str(e)}"
    
    return None, f"지원하는 인코딩으로 파일을 읽을 수 없습니다: {encodings}"


def parse_time_column(time_str: str) -> Tuple[Optional[int], Optional[int]]:
    """
    시간 문자열 파싱
    예: '8시30분' -> (8, 30)
    예: '00시30분' -> (24, 30)  # 자정 이후 처리
    """
    match = re.search(r'(\d+)시(\d+)분', str(time_str))
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        
        # 00시는 24시로 처리 (자정 이후)
        if hour == 0:
            hour = 24
            
        return hour, minute
    return None, None


@st.cache_data
def load_data() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    CSV 파일 로딩 및 전처리
    Returns:
        (DataFrame, error_message) 튜플
        성공 시: (df, None)
        실패 시: (None, error_message)
    """
    # 1. CSV 파일 찾기
    csv_file = find_csv_file()
    if not csv_file:
        return None, "혼잡도 CSV 파일을 찾을 수 없습니다."
    
    # 2. CSV 로딩
    df_raw, error = load_csv_with_encoding(csv_file)
    if error:
        return None, error
    
    # 3. 컬럼 확인
    expected_meta_cols = ['요일구분', '호선', '역번호', '출발역', '상하구분']
    
    # 실제 컬럼명 확인 (공백 제거)
    df_raw.columns = df_raw.columns.str.strip()
    
    # 메타 컬럼이 존재하는지 확인
    missing_cols = [col for col in expected_meta_cols if col not in df_raw.columns]
    if missing_cols:
        return None, f"필수 컬럼이 없습니다: {missing_cols}"
    
    # 4. 컬럼명 표준화 (일관성을 위해)
    df_raw = df_raw.rename(columns={
        '출발역': '역명',
        '상하구분': '상하선구분'
    })
    
    # 표준화된 컬럼명으로 업데이트
    expected_meta_cols = ['요일구분', '호선', '역번호', '역명', '상하선구분']
    
    # 5. 시간 컬럼 추출 (메타 컬럼이 아닌 것들)
    time_cols = [col for col in df_raw.columns if col not in expected_meta_cols]
    
    if not time_cols:
        return None, "시간대 컬럼을 찾을 수 없습니다."
    
    # 6. Wide to Long 변환
    df_long = pd.melt(
        df_raw,
        id_vars=expected_meta_cols,
        value_vars=time_cols,
        var_name='time',
        value_name='crowding'
    )
    
    # 7. 혼잡도 값 전처리
    # 공백 제거 및 숫자 변환
    df_long['crowding'] = df_long['crowding'].astype(str).str.strip()
    df_long['crowding'] = pd.to_numeric(df_long['crowding'], errors='coerce')
    
    # 8. 시간 파싱
    time_parsed = df_long['time'].apply(parse_time_column)
    df_long['hour'] = time_parsed.apply(lambda x: x[0])
    df_long['minute'] = time_parsed.apply(lambda x: x[1])
    
    # 9. 시간 정렬용 컬럼 생성
    df_long['time_order'] = df_long['hour'] * 60 + df_long['minute']
    
    # 10. 시간 파싱 실패한 행 확인
    invalid_time = df_long['hour'].isna().sum()
    if invalid_time > 0:
        st.warning(f"시간 파싱에 실패한 행: {invalid_time}개")
    
    # 11. 데이터 정렬 (호선, 역번호, 요일구분, 상하선구분, 시간순)
    df_long = df_long.sort_values(
        by=['호선', '역번호', '요일구분', '상하선구분', 'time_order']
    ).reset_index(drop=True)
    
    return df_long, None


@st.cache_data
def get_reference_date() -> str:
    """
    기준일 반환
    파일명에서 파싱하거나, 실패 시 '미상' 반환
    """
    csv_file = find_csv_file()
    if not csv_file:
        return "미상"
    
    ref_date = parse_reference_date(csv_file)
    if ref_date:
        return ref_date
    
    return "미상"


def get_data_summary(df: pd.DataFrame) -> dict:
    """데이터 요약 정보 반환 (디버깅/검증용)"""
    return {
        "총 행수": len(df),
        "요일구분": df['요일구분'].unique().tolist(),
        "호선": sorted(df['호선'].unique().tolist()),
        "역 수": df['역명'].nunique(),
        "시간대 수": df['time'].nunique(),
        "혼잡도 결측": df['crowding'].isna().sum(),
        "혼잡도 범위": f"{df['crowding'].min():.1f} ~ {df['crowding'].max():.1f}",
    }


def calculate_peak(df: pd.DataFrame) -> Tuple[float, str]:
    """
    피크 혼잡도와 피크 시간 반환
    Returns:
        (피크 혼잡도, 피크 시간) 튜플
    """
    if df.empty or df['crowding'].isna().all():
        return 0.0, "-"
    
    # 결측값 제외
    valid_df = df.dropna(subset=['crowding'])
    
    # 피크 혼잡도
    peak_crowding = valid_df['crowding'].max()
    
    # 피크 시간 (동률 시 가장 이른 시간)
    peak_row = valid_df[valid_df['crowding'] == peak_crowding].iloc[0]
    peak_time = peak_row['time']
    
    return peak_crowding, peak_time


def calculate_commute_avg(df: pd.DataFrame, include_9: bool = True) -> float:
    """
    출근 시간대(7~9시) 평균 혼잡도
    Args:
        df: 데이터프레임
        include_9: 9시 포함 여부 (기본 True)
    Returns:
        평균 혼잡도
    """
    if df.empty:
        return 0.0
    
    if include_9:
        # 7시 ~ 9시 포함
        time_filtered = df[(df['hour'] >= 7) & (df['hour'] <= 9)]
    else:
        # 7시 ~ 9시 미만
        time_filtered = df[(df['hour'] >= 7) & (df['hour'] < 9)]
    
    if time_filtered.empty:
        return 0.0
    
    return time_filtered['crowding'].mean()


def calculate_evening_avg(df: pd.DataFrame, include_20: bool = True) -> float:
    """
    퇴근 시간대(17~20시) 평균 혼잡도
    Args:
        df: 데이터프레임
        include_20: 20시 포함 여부 (기본 True)
    Returns:
        평균 혼잡도
    """
    if df.empty:
        return 0.0
    
    if include_20:
        # 17시 ~ 20시 포함
        time_filtered = df[(df['hour'] >= 17) & (df['hour'] <= 20)]
    else:
        # 17시 ~ 20시 미만
        time_filtered = df[(df['hour'] >= 17) & (df['hour'] < 20)]
    
    if time_filtered.empty:
        return 0.0
    
    return time_filtered['crowding'].mean()


def get_peak_top10(df: pd.DataFrame) -> pd.DataFrame:
    """
    피크 혼잡 TOP10 테이블 반환
    호선, 역명, 상하선구분, 요일구분 기준으로 그룹화
    """
    if df.empty:
        return pd.DataFrame()
    
    # 그룹별 피크 계산
    def get_peak_info(group):
        valid_group = group.dropna(subset=['crowding'])
        if valid_group.empty:
            return pd.Series({
                '피크혼잡': 0.0,
                '피크시간': '-'
            })
        
        peak_crowding = valid_group['crowding'].max()
        peak_row = valid_group[valid_group['crowding'] == peak_crowding].iloc[0]
        
        return pd.Series({
            '피크혼잡': peak_crowding,
            '피크시간': peak_row['time']
        })
    
    peak_df = df.groupby(['호선', '역명', '상하선구분', '요일구분']).apply(
        get_peak_info
    ).reset_index()
    
    # 피크 혼잡 기준 내림차순 정렬
    peak_df = peak_df.sort_values('피크혼잡', ascending=False).head(10).reset_index(drop=True)
    
    # 순위 추가
    peak_df.insert(0, '순위', range(1, len(peak_df) + 1))
    
    # 컬럼명 변경
    peak_df = peak_df.rename(columns={
        '상하선구분': '방향',
        '요일구분': '요일'
    })
    
    return peak_df


def get_commute_top10(df: pd.DataFrame, include_9: bool = True) -> pd.DataFrame:
    """
    출근시간 평균 혼잡 TOP10 테이블 반환
    호선, 역명, 상하선구분, 요일구분 기준으로 그룹화
    Args:
        df: 데이터프레임
        include_9: 9시 포함 여부 (기본 True)
    """
    if df.empty:
        return pd.DataFrame()
    
    # 출근 시간대 필터링
    if include_9:
        time_filtered = df[(df['hour'] >= 7) & (df['hour'] <= 9)]
    else:
        time_filtered = df[(df['hour'] >= 7) & (df['hour'] < 9)]
    
    if time_filtered.empty:
        return pd.DataFrame()
    
    # 그룹별 평균 계산
    commute_df = time_filtered.groupby(['호선', '역명', '상하선구분', '요일구분']).agg({
        'crowding': 'mean'
    }).reset_index()
    
    commute_df = commute_df.rename(columns={'crowding': '출근평균'})
    
    # 출근 평균 기준 내림차순 정렬
    commute_df = commute_df.sort_values('출근평균', ascending=False).head(10).reset_index(drop=True)
    
    # 순위 추가
    commute_df.insert(0, '순위', range(1, len(commute_df) + 1))
    
    # 컬럼명 변경
    commute_df = commute_df.rename(columns={
        '상하선구분': '방향',
        '요일구분': '요일'
    })
    
    return commute_df


def get_evening_top10(df: pd.DataFrame, include_20: bool = True) -> pd.DataFrame:
    """
    퇴근시간 평균 혼잡 TOP10 테이블 반환
    호선, 역명, 상하선구분, 요일구분 기준으로 그룹화
    Args:
        df: 데이터프레임
        include_20: 20시 포함 여부 (기본 True)
    """
    if df.empty:
        return pd.DataFrame()
    
    # 퇴근 시간대 필터링
    if include_20:
        time_filtered = df[(df['hour'] >= 17) & (df['hour'] <= 20)]
    else:
        time_filtered = df[(df['hour'] >= 17) & (df['hour'] < 20)]
    
    if time_filtered.empty:
        return pd.DataFrame()
    
    # 그룹별 평균 계산
    evening_df = time_filtered.groupby(['호선', '역명', '상하선구분', '요일구분']).agg({
        'crowding': 'mean'
    }).reset_index()
    
    evening_df = evening_df.rename(columns={'crowding': '퇴근평균'})
    
    # 퇴근 평균 기준 내림차순 정렬
    evening_df = evening_df.sort_values('퇴근평균', ascending=False).head(10).reset_index(drop=True)
    
    # 순위 추가
    evening_df.insert(0, '순위', range(1, len(evening_df) + 1))
    
    # 컬럼명 변경
    evening_df = evening_df.rename(columns={
        '상하선구분': '방향',
        '요일구분': '요일'
    })
    
    return evening_df


def get_line_summary(df: pd.DataFrame, include_9: bool = True, include_20: bool = True) -> pd.DataFrame:
    """
    노선별 혼잡도 요약 (평균, 피크, 출근평균, 퇴근평균)
    Args:
        df: 데이터프레임
        include_9: 출근시간 9시 포함 여부
        include_20: 퇴근시간 20시 포함 여부
    Returns:
        노선별 요약 데이터프레임
    """
    if df.empty:
        return pd.DataFrame()
    
    # 전체 평균 및 피크 혼잡도 (최적화: 한 번의 groupby로 통합)
    line_summary = df.groupby('호선').agg({
        'crowding': ['mean', 'max']
    }).reset_index()
    
    # 컬럼명 평탄화
    line_summary.columns = ['호선', '평균혼잡', '피크혼잡']
    
    # 출근 평균
    if include_9:
        commute_df = df[(df['hour'] >= 7) & (df['hour'] <= 9)]
    else:
        commute_df = df[(df['hour'] >= 7) & (df['hour'] < 9)]
    
    line_commute = commute_df.groupby('호선').agg({
        'crowding': 'mean'
    }).reset_index()
    line_commute = line_commute.rename(columns={'crowding': '출근평균'})
    
    # 퇴근 평균
    if include_20:
        evening_df = df[(df['hour'] >= 17) & (df['hour'] <= 20)]
    else:
        evening_df = df[(df['hour'] >= 17) & (df['hour'] < 20)]
    
    line_evening = evening_df.groupby('호선').agg({
        'crowding': 'mean'
    }).reset_index()
    line_evening = line_evening.rename(columns={'crowding': '퇴근평균'})
    
    # 병합
    line_summary = line_summary.merge(line_commute, on='호선', how='left')
    line_summary = line_summary.merge(line_evening, on='호선', how='left')
    
    # 결측값 처리
    line_summary['출근평균'] = line_summary['출근평균'].fillna(0)
    line_summary['퇴근평균'] = line_summary['퇴근평균'].fillna(0)
    
    # 호선 정렬
    line_summary = line_summary.sort_values('호선')
    
    return line_summary


def get_station_peak_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    역별 피크 요약 테이블 반환
    역 단위로 통합 (방향/요일 통합)
    """
    if df.empty:
        return pd.DataFrame()
    
    # 역별 피크 계산
    def get_peak_info(group):
        valid_group = group.dropna(subset=['crowding'])
        if valid_group.empty:
            return pd.Series({
                '피크혼잡': 0.0,
                '피크시간': '-'
            })
        
        peak_crowding = valid_group['crowding'].max()
        peak_row = valid_group[valid_group['crowding'] == peak_crowding].iloc[0]
        
        return pd.Series({
            '피크혼잡': peak_crowding,
            '피크시간': peak_row['time']
        })
    
    station_df = df.groupby(['호선', '역명']).apply(
        get_peak_info
    ).reset_index()
    
    # 피크 혼잡 기준 내림차순 정렬
    station_df = station_df.sort_values('피크혼잡', ascending=False).reset_index(drop=True)
    
    return station_df


def get_station_full_summary(df: pd.DataFrame, include_9: bool = True, include_20: bool = True) -> pd.DataFrame:
    """
    역별 전체 요약 테이블 반환 (피크, 출근평균, 퇴근평균 포함)
    Args:
        df: 데이터프레임
        include_9: 출근시간 9시 포함 여부
        include_20: 퇴근시간 20시 포함 여부
    Returns:
        역별 전체 요약 데이터프레임
    """
    if df.empty:
        return pd.DataFrame()
    
    # 역별 피크 계산
    def get_peak_info(group):
        valid_group = group.dropna(subset=['crowding'])
        if valid_group.empty:
            return pd.Series({
                '피크혼잡': 0.0,
                '피크시간': '-'
            })
        
        peak_crowding = valid_group['crowding'].max()
        peak_row = valid_group[valid_group['crowding'] == peak_crowding].iloc[0]
        
        return pd.Series({
            '피크혼잡': peak_crowding,
            '피크시간': peak_row['time']
        })
    
    station_peak = df.groupby(['호선', '역명']).apply(
        get_peak_info
    ).reset_index()
    
    # 출근 시간대 필터링
    if include_9:
        commute_df = df[(df['hour'] >= 7) & (df['hour'] <= 9)]
    else:
        commute_df = df[(df['hour'] >= 7) & (df['hour'] < 9)]
    
    # 역별 출근 평균
    station_commute = commute_df.groupby(['호선', '역명']).agg({
        'crowding': 'mean'
    }).reset_index()
    station_commute = station_commute.rename(columns={'crowding': '출근평균'})
    
    # 퇴근 시간대 필터링
    if include_20:
        evening_df = df[(df['hour'] >= 17) & (df['hour'] <= 20)]
    else:
        evening_df = df[(df['hour'] >= 17) & (df['hour'] < 20)]
    
    # 역별 퇴근 평균
    station_evening = evening_df.groupby(['호선', '역명']).agg({
        'crowding': 'mean'
    }).reset_index()
    station_evening = station_evening.rename(columns={'crowding': '퇴근평균'})
    
    # 병합
    station_summary = station_peak.merge(station_commute, on=['호선', '역명'], how='left')
    station_summary = station_summary.merge(station_evening, on=['호선', '역명'], how='left')
    
    # 결측값 처리
    station_summary['출근평균'] = station_summary['출근평균'].fillna(0)
    station_summary['퇴근평균'] = station_summary['퇴근평균'].fillna(0)
    
    # 피크 혼잡 기준 내림차순 정렬
    station_summary = station_summary.sort_values('피크혼잡', ascending=False).reset_index(drop=True)
    
    return station_summary


def get_station_crowding_for_map(df: pd.DataFrame, crowding_type: str = "average", 
                                  include_9: bool = True, include_20: bool = True) -> pd.DataFrame:
    """
    지도 시각화용 역별 혼잡도 데이터 생성 (위경도 포함)
    Args:
        df: 데이터프레임
        crowding_type: 혼잡도 유형 ("average", "peak", "commute", "evening")
        include_9: 출근시간 9시 포함 여부
        include_20: 퇴근시간 20시 포함 여부
    Returns:
        역명, 호선, 위도, 경도, 혼잡도 데이터프레임
    """
    if df.empty:
        return pd.DataFrame()
    
    # 역별 혼잡도 계산
    if crowding_type == "peak":
        # 피크 혼잡도
        def get_peak(group):
            valid_group = group.dropna(subset=['crowding'])
            if valid_group.empty:
                return pd.Series({'crowding_value': 0.0})
            return pd.Series({'crowding_value': valid_group['crowding'].max()})
        
        station_crowding = df.groupby(['호선', '역명']).apply(get_peak).reset_index()
        
    elif crowding_type == "commute":
        # 출근 평균
        if include_9:
            time_filtered = df[(df['hour'] >= 7) & (df['hour'] <= 9)]
        else:
            time_filtered = df[(df['hour'] >= 7) & (df['hour'] < 9)]
        
        if time_filtered.empty:
            return pd.DataFrame()
        
        station_crowding = time_filtered.groupby(['호선', '역명']).agg({
            'crowding': 'mean'
        }).reset_index()
        station_crowding = station_crowding.rename(columns={'crowding': 'crowding_value'})
        
    elif crowding_type == "evening":
        # 퇴근 평균
        if include_20:
            time_filtered = df[(df['hour'] >= 17) & (df['hour'] <= 20)]
        else:
            time_filtered = df[(df['hour'] >= 17) & (df['hour'] < 20)]
        
        if time_filtered.empty:
            return pd.DataFrame()
        
        station_crowding = time_filtered.groupby(['호선', '역명']).agg({
            'crowding': 'mean'
        }).reset_index()
        station_crowding = station_crowding.rename(columns={'crowding': 'crowding_value'})
        
    else:  # average (기본값)
        # 전체 평균
        station_crowding = df.groupby(['호선', '역명']).agg({
            'crowding': 'mean'
        }).reset_index()
        station_crowding = station_crowding.rename(columns={'crowding': 'crowding_value'})
    
    # 위경도 데이터 병합
    coords_list = []
    for _, row in station_crowding.iterrows():
        station_name = row['역명']
        coord = STATION_COORDS.get(station_name)
        
        if coord:
            coords_list.append({
                '호선': row['호선'],
                '역명': station_name,
                'crowding_value': row['crowding_value'],
                'lat': coord['lat'],
                'lng': coord['lng']
            })
    
    # 결과 데이터프레임 생성
    if not coords_list:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(coords_list)
    
    # 혼잡도 기준 정렬
    result_df = result_df.sort_values('crowding_value', ascending=False).reset_index(drop=True)
    
    return result_df
