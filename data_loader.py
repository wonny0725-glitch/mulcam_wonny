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

