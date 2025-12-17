"""
PDF 보고서 렌더링 모듈
reportlab 기반 PDF 생성
"""
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from reporting.templates.sentences import generate_recommendations, generate_executive_summary


class PDFReportGenerator:
    """PDF 보고서 생성 클래스"""
    
    def __init__(self, report_data: Dict[str, Any]):
        """
        Parameters:
        -----------
        report_data : Dict[str, Any]
            collector.py에서 수집한 보고서 데이터
        """
        self.report_data = report_data
        self.story = []
        self.styles = None
        self._setup_styles()
    
    def _setup_styles(self):
        """스타일 설정 (한글 폰트 포함)"""
        self.styles = getSampleStyleSheet()
        
        # 한글 폰트 등록 시도 (Windows 환경)
        korean_font = 'Helvetica'  # 기본값
        
        try:
            # Windows 기본 폰트 경로 (TTF 파일만, TTC는 제외)
            font_paths = [
                ('C:\\Windows\\Fonts\\malgun.ttf', 'Korean'),      # 맑은 고딕
                ('C:\\Windows\\Fonts\\malgunbd.ttf', 'KoreanBold'), # 맑은 고딕 볼드
                ('C:\\Windows\\Fonts\\NanumGothic.ttf', 'Korean'), # 나눔고딕
            ]
            
            for font_path, font_name in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                        korean_font = font_name
                        print(f"✓ 한글 폰트 등록 성공: {font_path}")
                        break
                    except Exception as font_error:
                        print(f"폰트 등록 실패 ({font_path}): {font_error}")
                        continue
            
            if korean_font == 'Helvetica':
                print("⚠ 경고: 한글 폰트를 찾을 수 없어 기본 폰트를 사용합니다. 한글이 깨질 수 있습니다.")
        
        except Exception as e:
            print(f"❌ 폰트 설정 오류: {e}")
            korean_font = 'Helvetica'
        
        # 커스텀 스타일 정의
        self.styles.add(ParagraphStyle(
            name='KoreanTitle',
            parent=self.styles['Title'],
            fontName=korean_font,
            fontSize=24,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='KoreanHeading1',
            parent=self.styles['Heading1'],
            fontName=korean_font,
            fontSize=16,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=12,
            spaceBefore=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='KoreanHeading2',
            parent=self.styles['Heading2'],
            fontName=korean_font,
            fontSize=14,
            textColor=colors.HexColor('#34495E'),
            spaceAfter=10,
            spaceBefore=10
        ))
        
        self.styles.add(ParagraphStyle(
            name='KoreanNormal',
            parent=self.styles['Normal'],
            fontName=korean_font,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#2C3E50'),
            alignment=TA_JUSTIFY
        ))
        
        self.styles.add(ParagraphStyle(
            name='KoreanCaption',
            parent=self.styles['Normal'],
            fontName=korean_font,
            fontSize=9,
            textColor=colors.HexColor('#7F8C8D'),
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='CoverTitle',
            fontName=korean_font,
            fontSize=28,
            textColor=colors.HexColor('#2C3E50'),
            alignment=TA_CENTER,
            spaceAfter=20
        ))
        
        self.styles.add(ParagraphStyle(
            name='CoverOrg',
            fontName=korean_font,
            fontSize=18,
            textColor=colors.HexColor('#34495E'),
            alignment=TA_CENTER,
            spaceAfter=10
        ))
    
    def generate(self, output_path: str, include_charts: bool = True) -> str:
        """
        PDF 보고서 생성
        
        Parameters:
        -----------
        output_path : str
            출력 파일 경로
        include_charts : bool
            차트 포함 여부 (기본값: True)
        
        Returns:
        --------
        str
            생성된 파일 경로
        """
        # PDF 문서 생성
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # 콘텐츠 구성
        self._build_cover_page()
        self._build_toc_page()  # 목차 추가
        self._build_summary_page()
        
        # 본문 페이지
        self._build_overview_page()
        self._build_line_analysis_page()
        self._build_station_analysis_page()
        self._build_recommendations_page()
        
        # 부록
        self._build_appendix_page()
        self._build_impact_page()  # 마지막 요약 페이지 추가
        
        # PDF 빌드
        doc.build(self.story)
        
        return output_path
    
    def _build_cover_page(self):
        """표지 페이지 생성 (2025_plan.pdf 양식 참고)"""
        # 상단 여백
        self.story.append(Spacer(1, 5*cm))
        
        # 메인 제목
        title = self.report_data['metadata']['report_title']
        self.story.append(Paragraph(title, self.styles['CoverTitle']))
        self.story.append(Spacer(1, 0.5*cm))
        
        # 부제 (슬로건)
        subtitle_style = ParagraphStyle(
            name='CoverSubtitle',
            parent=self.styles['CoverOrg'],
            fontSize=14,
            textColor=colors.HexColor('#5D6D7E'),
            alignment=TA_CENTER,
            spaceAfter=15
        )
        subtitle_text = "- 데이터 기반 의사결정,<br/>시민을 위한 교통 서비스 개선 -"
        self.story.append(Paragraph(subtitle_text, subtitle_style))
        self.story.append(Spacer(1, 3*cm))
        
        # 날짜 및 기관 정보
        ref_date = self.report_data['metadata']['ref_date']
        generated_at = self.report_data['metadata']['generated_at']
        org_name = self.report_data['metadata']['organization']
        
        date_style = ParagraphStyle(
            name='CoverDate',
            parent=self.styles['CoverOrg'],
            fontSize=16,
            textColor=colors.HexColor('#2C3E50'),
            alignment=TA_CENTER,
            spaceAfter=10
        )
        
        # 날짜 표시
        date_text = f"{ref_date.replace('-', '. ')}."
        self.story.append(Paragraph(date_text, date_style))
        self.story.append(Spacer(1, 0.5*cm))
        
        # 기관명
        self.story.append(Paragraph(org_name, self.styles['CoverOrg']))
        
        self.story.append(PageBreak())
    
    def _build_toc_page(self):
        """목차 페이지 생성 (2025_plan.pdf 스타일)"""
        # 목차 제목
        toc_title_style = ParagraphStyle(
            name='TOCTitle',
            parent=self.styles['KoreanHeading1'],
            fontSize=20,
            alignment=TA_CENTER,
            spaceAfter=30
        )
        self.story.append(Paragraph("순서", toc_title_style))
        self.story.append(Spacer(1, 1*cm))
        
        # 목차 항목
        toc_style = ParagraphStyle(
            name='TOCItem',
            parent=self.styles['KoreanNormal'],
            fontSize=12,
            leading=20,
            leftIndent=20
        )
        
        toc_items = [
            "I. 분석 개요 및 현황",
            "II. 주요 분석 결과",
            "III. 호선별 혼잡도 진단",
            "IV. 혼잡 역 상세 분석",
            "V. 운영 개선방안",
            "VI. 부록"
        ]
        
        for item in toc_items:
            self.story.append(Paragraph(item, toc_style))
            self.story.append(Spacer(1, 0.3*cm))
        
        self.story.append(PageBreak())
    
    def _build_summary_page(self):
        """요약 페이지 생성 (2025_plan.pdf 스타일)"""
        # 섹션 제목
        summary_title_style = ParagraphStyle(
            name='SummaryTitle',
            parent=self.styles['KoreanHeading1'],
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=20
        )
        self.story.append(Paragraph("혼잡도 분석 주요 결과", summary_title_style))
        self.story.append(Spacer(1, 0.5*cm))
        
        # 박스형 요약 (□ 기호 사용)
        self._add_boxed_summary()
        self.story.append(Spacer(1, 0.5*cm))
        
        # KPI 3종 표시
        self._add_kpi_section()
        self.story.append(Spacer(1, 0.5*cm))
        
        # 핵심 이슈 (TOP 3)
        self._add_top_issues_section()
        self.story.append(Spacer(1, 0.5*cm))
        
        # 주요 발견사항
        self._add_key_findings()
    
    def _add_boxed_summary(self):
        """박스형 요약 (2025_plan.pdf 스타일)"""
        kpi = self.report_data['kpi']
        
        box_style = ParagraphStyle(
            name='BoxedSummary',
            parent=self.styles['KoreanNormal'],
            fontSize=11,
            leading=16,
            leftIndent=15,
            spaceAfter=8
        )
        
        # 전체 요약
        summary_text = f"""
        □ <b>피크 혼잡도 분석</b><br/>
        &nbsp;&nbsp;&nbsp;&nbsp;- 최대 피크: {kpi.get('peak_crowding', 0):.1f}% ({kpi.get('peak_time', 'N/A')})<br/>
        &nbsp;&nbsp;&nbsp;&nbsp;- 출근시간 평균: {kpi.get('commute_avg', 0):.1f}% (7~9시)<br/>
        &nbsp;&nbsp;&nbsp;&nbsp;- 퇴근시간 평균: {kpi.get('evening_avg', 0):.1f}% (17~20시)
        """
        
        self.story.append(Paragraph(summary_text, box_style))
        self.story.append(Spacer(1, 0.3*cm))
        
        # 혼잡 역 정보
        top10 = self.report_data['top10']
        if top10.get('peak'):
            top_station = top10['peak'][0]
            station_text = f"""
            □ <b>주요 혼잡 구간</b><br/>
            &nbsp;&nbsp;&nbsp;&nbsp;- 최고 혼잡 역: {top_station.get('역명', 'N/A')}역 ({top_station.get('호선', 'N/A')})<br/>
            &nbsp;&nbsp;&nbsp;&nbsp;- 혼잡도: {top_station.get('피크혼잡', 0):.1f}% ({top_station.get('피크시간', 'N/A')})<br/>
            &nbsp;&nbsp;&nbsp;&nbsp;- 방향: {top_station.get('상하선구분', 'N/A')}
            """
            self.story.append(Paragraph(station_text, box_style))
    
    def _add_kpi_section(self):
        """KPI 3종 섹션 추가"""
        self.story.append(Paragraph("주요 지표", self.styles['KoreanHeading2']))
        
        kpi = self.report_data['kpi']
        
        kpi_data = [
            ['지표', '값', '상세'],
            [
                '최대 피크 혼잡',
                f"{kpi['peak_crowding']:.1f}%",
                f"발생시간: {kpi['peak_time']}"
            ],
            [
                '출근시간 평균',
                f"{kpi['commute_avg']:.1f}%",
                '7~9시 평균'
            ],
            [
                '퇴근시간 평균',
                f"{kpi['evening_avg']:.1f}%",
                '17~20시 평균'
            ]
        ]
        
        kpi_table = Table(kpi_data, colWidths=[4*cm, 3*cm, 6*cm])
        kpi_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Korean'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ECF0F1')])
        ]))
        
        self.story.append(kpi_table)
    
    def _add_top_issues_section(self):
        """핵심 이슈 TOP 3 섹션"""
        self.story.append(Paragraph("핵심 이슈", self.styles['KoreanHeading2']))
        
        top10 = self.report_data['top10']
        
        # 피크 혼잡 1위
        if top10['peak']:
            station = top10['peak'][0]
            issue1 = f"1. 피크 혼잡 최고: {station.get('역명', 'N/A')}역 ({station.get('호선', 'N/A')}, {station.get('상하선구분', 'N/A')}) - {station.get('피크혼잡', 0.0):.1f}%"
            self.story.append(Paragraph(issue1, self.styles['KoreanNormal']))
            self.story.append(Spacer(1, 0.2*cm))
        
        # 출근시간 혼잡 1위
        if top10['commute']:
            station = top10['commute'][0]
            issue2 = f"2. 출근시간 혼잡 최고: {station.get('역명', 'N/A')}역 ({station.get('호선', 'N/A')}, {station.get('상하선구분', 'N/A')}) - {station.get('출근평균', 0.0):.1f}%"
            self.story.append(Paragraph(issue2, self.styles['KoreanNormal']))
            self.story.append(Spacer(1, 0.2*cm))
        
        # 퇴근시간 혼잡 1위
        if top10['evening']:
            station = top10['evening'][0]
            issue3 = f"3. 퇴근시간 혼잡 최고: {station.get('역명', 'N/A')}역 ({station.get('호선', 'N/A')}, {station.get('상하선구분', 'N/A')}) - {station.get('퇴근평균', 0.0):.1f}%"
            self.story.append(Paragraph(issue3, self.styles['KoreanNormal']))
    
    def _add_key_findings(self):
        """주요 발견사항"""
        self.story.append(Paragraph("주요 발견사항", self.styles['KoreanHeading2']))
        
        stats = self.report_data['statistics']
        filters = self.report_data['filters']
        
        # 요일 정보 안전하게 가져오기
        selected_days = filters.get('selected_days', [])
        if isinstance(selected_days, list):
            days_str = ', '.join(selected_days) if selected_days else '전체'
        else:
            days_str = str(selected_days)
        
        findings = [
            f"• 분석 대상: {stats['unique_lines']}개 호선, {stats['unique_stations']}개 역",
            f"• 분석 기간: {days_str}",
            f"• 데이터 건수: {stats['total_records']:,}건"
        ]
        
        for finding in findings:
            self.story.append(Paragraph(finding, self.styles['KoreanNormal']))
            self.story.append(Spacer(1, 0.15*cm))
    
    def _build_overview_page(self):
        """분석 개요 페이지"""
        self.story.append(PageBreak())
        self.story.append(Paragraph("I. 분석 개요 및 현황", self.styles['KoreanHeading1']))
        self.story.append(Spacer(1, 0.5*cm))
        
        # 데이터 출처
        self.story.append(Paragraph("데이터 출처 및 범위", self.styles['KoreanHeading2']))
        overview_text = f"""
        본 보고서는 서울교통공사가 제공하는 지하철 혼잡도 데이터를 기반으로 작성되었습니다. 
        데이터 기준일은 {self.report_data['metadata']['ref_date']}이며, 
        30분 단위로 측정된 열차 평균 혼잡도를 분석하였습니다.
        """
        self.story.append(Paragraph(overview_text, self.styles['KoreanNormal']))
        self.story.append(Spacer(1, 0.3*cm))
        
        # 필터 조건
        filters = self.report_data['filters']
        self.story.append(Paragraph("분석 조건", self.styles['KoreanHeading2']))
        
        # 안전하게 필터 데이터 가져오기
        selected_days = filters.get('selected_days', [])
        selected_lines = filters.get('selected_lines', [])
        selected_directions = filters.get('selected_directions', [])
        
        filter_data = [
            ['항목', '선택값'],
            ['요일', ', '.join(selected_days) if selected_days else '전체'],
            ['호선', ', '.join(selected_lines) if selected_lines else '전체'],
            ['방향', ', '.join(selected_directions) if selected_directions else '전체'],
            ['출근시간', '7~9시' + (' (9시 포함)' if filters.get('include_9', True) else ' (9시 미포함)')],
            ['퇴근시간', '17~20시' + (' (20시 포함)' if filters.get('include_20', True) else ' (20시 미포함)')],
        ]
        
        filter_table = Table(filter_data, colWidths=[4*cm, 9*cm])
        filter_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Korean'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ECF0F1')])
        ]))
        
        self.story.append(filter_table)
        self.story.append(Spacer(1, 0.5*cm))
        
        # 지표 정의
        self.story.append(Paragraph("혼잡도 지표 정의", self.styles['KoreanHeading2']))
        metrics_text = """
        • <b>혼잡도 (%)</b>: 열차 정원 대비 실제 승차 인원의 비율<br/>
        • <b>좌석 만석 기준</b>: 34% (좌석만 모두 찬 경우)<br/>
        • <b>정원 기준</b>: 100% (좌석 + 입석 정원)<br/>
        • <b>피크 혼잡</b>: 전체 시간대 중 최대 혼잡도<br/>
        • <b>출근/퇴근 평균</b>: 해당 시간대의 평균 혼잡도
        """
        self.story.append(Paragraph(metrics_text, self.styles['KoreanNormal']))
    
    def _build_line_analysis_page(self):
        """호선별 분석 페이지"""
        self.story.append(PageBreak())
        self.story.append(Paragraph("II. 호선별 혼잡도 진단", self.styles['KoreanHeading1']))
        self.story.append(Spacer(1, 0.5*cm))
        
        line_summary = self.report_data['line_summary']
        
        if not line_summary:
            self.story.append(Paragraph("분석 대상 데이터가 없습니다.", self.styles['KoreanNormal']))
            return
        
        # 노선별 요약 표
        self.story.append(Paragraph("노선별 혼잡도 요약", self.styles['KoreanHeading2']))
        
        table_data = [['호선', '전체 평균', '피크', '출근 평균', '퇴근 평균']]
        for line in line_summary:
            table_data.append([
                line.get('호선', 'N/A'),
                f"{line.get('평균혼잡', 0.0):.1f}%",
                f"{line.get('피크혼잡', 0.0):.1f}%",
                f"{line.get('출근평균', 0.0):.1f}%",
                f"{line.get('퇴근평균', 0.0):.1f}%"
            ])
        
        line_table = Table(table_data, colWidths=[2.5*cm, 3*cm, 3*cm, 3*cm, 3*cm])
        line_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Korean'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ECF0F1')])
        ]))
        
        self.story.append(line_table)
        self.story.append(Spacer(1, 0.5*cm))
        
        # 해석
        self.story.append(Paragraph("주요 발견사항", self.styles['KoreanHeading2']))
        
        # 가장 혼잡한 노선
        max_line = max(line_summary, key=lambda x: x['피크혼잡'])
        finding1 = f"• 피크 혼잡도가 가장 높은 노선은 <b>{max_line['호선']}</b>이며, 최대 {max_line['피크혼잡']:.1f}%의 혼잡도를 기록했습니다."
        self.story.append(Paragraph(finding1, self.styles['KoreanNormal']))
        self.story.append(Spacer(1, 0.2*cm))
        
        # 출근 평균이 높은 노선
        max_commute_line = max(line_summary, key=lambda x: x['출근평균'])
        finding2 = f"• 출근시간대 혼잡도는 <b>{max_commute_line['호선']}</b>이 {max_commute_line['출근평균']:.1f}%로 가장 높습니다."
        self.story.append(Paragraph(finding2, self.styles['KoreanNormal']))
        self.story.append(Spacer(1, 0.2*cm))
        
        # 퇴근 평균이 높은 노선
        max_evening_line = max(line_summary, key=lambda x: x['퇴근평균'])
        finding3 = f"• 퇴근시간대 혼잡도는 <b>{max_evening_line['호선']}</b>이 {max_evening_line['퇴근평균']:.1f}%로 가장 높습니다."
        self.story.append(Paragraph(finding3, self.styles['KoreanNormal']))
    
    def _build_station_analysis_page(self):
        """역별 분석 페이지"""
        self.story.append(PageBreak())
        self.story.append(Paragraph("III. 혼잡 역 상세 분석", self.styles['KoreanHeading1']))
        self.story.append(Spacer(1, 0.5*cm))
        
        top10 = self.report_data['top10']
        
        # 피크 TOP10
        if top10['peak']:
            self.story.append(Paragraph("피크 혼잡도 TOP 10", self.styles['KoreanHeading2']))
            
            peak_data = [['순위', '역명', '호선', '방향', '피크혼잡', '피크시간']]
            for idx, station in enumerate(top10['peak'][:10], 1):
                peak_data.append([
                    str(idx),
                    station.get('역명', 'N/A'),
                    station.get('호선', 'N/A'),
                    station.get('상하선구분', 'N/A'),
                    f"{station.get('피크혼잡', 0.0):.1f}%",
                    station.get('피크시간', 'N/A')
                ])
            
            peak_table = Table(peak_data, colWidths=[1.5*cm, 3*cm, 2.5*cm, 2*cm, 2.5*cm, 2.5*cm])
            peak_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Korean'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E74C3C')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FADBD8')])
            ]))
            
            self.story.append(peak_table)
            self.story.append(Spacer(1, 0.5*cm))
        
        # 출근 평균 TOP10
        if top10['commute']:
            self.story.append(Paragraph("출근시간 평균 혼잡도 TOP 10", self.styles['KoreanHeading2']))
            
            commute_data = [['순위', '역명', '호선', '방향', '출근평균']]
            for idx, station in enumerate(top10['commute'][:10], 1):
                commute_data.append([
                    str(idx),
                    station.get('역명', 'N/A'),
                    station.get('호선', 'N/A'),
                    station.get('상하선구분', 'N/A'),
                    f"{station.get('출근평균', 0.0):.1f}%"
                ])
            
            commute_table = Table(commute_data, colWidths=[1.5*cm, 3.5*cm, 3*cm, 2.5*cm, 3*cm])
            commute_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Korean'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F39C12')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAE5D3')])
            ]))
            
            self.story.append(commute_table)
            self.story.append(Spacer(1, 0.5*cm))
        
        # 퇴근 평균 TOP10
        if top10['evening']:
            self.story.append(Paragraph("퇴근시간 평균 혼잡도 TOP 10", self.styles['KoreanHeading2']))
            
            evening_data = [['순위', '역명', '호선', '방향', '퇴근평균']]
            for idx, station in enumerate(top10['evening'][:10], 1):
                evening_data.append([
                    str(idx),
                    station.get('역명', 'N/A'),
                    station.get('호선', 'N/A'),
                    station.get('상하선구분', 'N/A'),
                    f"{station.get('퇴근평균', 0.0):.1f}%"
                ])
            
            evening_table = Table(evening_data, colWidths=[1.5*cm, 3.5*cm, 3*cm, 2.5*cm, 3*cm])
            evening_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Korean'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9B59B6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#E8DAEF')])
            ]))
            
            self.story.append(evening_table)
    
    def _build_recommendations_page(self):
        """운영 개선방안 페이지"""
        self.story.append(PageBreak())
        self.story.append(Paragraph("IV. 운영 개선방안", self.styles['KoreanHeading1']))
        self.story.append(Spacer(1, 0.5*cm))
        
        # 권고안 생성
        recommendations = generate_recommendations(self.report_data)
        
        # 카테고리별로 그룹화
        immediate = [r for r in recommendations if r['category'] == '즉시']
        short_term = [r for r in recommendations if r['category'] == '단기']
        mid_term = [r for r in recommendations if r['category'] == '중기']
        
        # 즉시 조치사항
        if immediate:
            self.story.append(Paragraph("즉시 조치사항", self.styles['KoreanHeading2']))
            
            for idx, rec in enumerate(immediate, 1):
                title_para = Paragraph(f"<b>{idx}. {rec['title']}</b>", self.styles['KoreanNormal'])
                self.story.append(title_para)
                self.story.append(Spacer(1, 0.1*cm))
                
                content_para = Paragraph(rec['content'], self.styles['KoreanNormal'])
                self.story.append(content_para)
                self.story.append(Spacer(1, 0.3*cm))
        
        # 단기 개선사항
        if short_term:
            self.story.append(Paragraph("단기 개선사항 (1~3개월)", self.styles['KoreanHeading2']))
            
            for idx, rec in enumerate(short_term, 1):
                title_para = Paragraph(f"<b>{idx}. {rec['title']}</b>", self.styles['KoreanNormal'])
                self.story.append(title_para)
                self.story.append(Spacer(1, 0.1*cm))
                
                content_para = Paragraph(rec['content'], self.styles['KoreanNormal'])
                self.story.append(content_para)
                self.story.append(Spacer(1, 0.3*cm))
        
        # 중기 개선사항
        if mid_term:
            self.story.append(Paragraph("중기 개선사항 (3~12개월)", self.styles['KoreanHeading2']))
            
            for idx, rec in enumerate(mid_term, 1):
                title_para = Paragraph(f"<b>{idx}. {rec['title']}</b>", self.styles['KoreanNormal'])
                self.story.append(title_para)
                self.story.append(Spacer(1, 0.1*cm))
                
                content_para = Paragraph(rec['content'], self.styles['KoreanNormal'])
                self.story.append(content_para)
                self.story.append(Spacer(1, 0.3*cm))
        
        # 기대효과
        self.story.append(Spacer(1, 0.3*cm))
        self.story.append(Paragraph("기대효과", self.styles['KoreanHeading2']))
        
        effects = [
            "• 승객 혼잡도 완화를 통한 이용 만족도 향상",
            "• 안전사고 예방 및 운영 효율성 개선",
            "• 시간대별 승객 분산을 통한 서비스 품질 향상",
            "• 데이터 기반 의사결정 체계 확립"
        ]
        
        for effect in effects:
            self.story.append(Paragraph(effect, self.styles['KoreanNormal']))
            self.story.append(Spacer(1, 0.15*cm))
    
    def _build_appendix_page(self):
        """부록 페이지"""
        self.story.append(PageBreak())
        self.story.append(Paragraph("V. 부록", self.styles['KoreanHeading1']))
        self.story.append(Spacer(1, 0.5*cm))
        
        # 부록 A: 역별 종합 요약
        station_summary = self.report_data['station_summary']
        
        if station_summary and len(station_summary) > 0:
            self.story.append(Paragraph("부록 A. 역별 혼잡도 종합 요약", self.styles['KoreanHeading2']))
            self.story.append(Spacer(1, 0.3*cm))
            
            # 상위 20개만 표시 (페이지 제한)
            display_count = min(20, len(station_summary))
            
            appendix_data = [['순위', '호선', '역명', '방향', '피크', '출근', '퇴근']]
            for idx, station in enumerate(station_summary[:display_count], 1):
                appendix_data.append([
                    str(idx),
                    station.get('호선', 'N/A'),
                    station.get('역명', 'N/A'),
                    station.get('상하선구분', 'N/A'),
                    f"{station.get('피크혼잡', 0.0):.1f}%",
                    f"{station.get('출근평균', 0.0):.1f}%",
                    f"{station.get('퇴근평균', 0.0):.1f}%"
                ])
            
            appendix_table = Table(appendix_data, colWidths=[1.2*cm, 2*cm, 2.5*cm, 1.8*cm, 2*cm, 2*cm, 2*cm])
            appendix_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Korean'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ECF0F1')])
            ]))
            
            self.story.append(appendix_table)
            
            if len(station_summary) > display_count:
                note = f"(전체 {len(station_summary)}개 역 중 상위 {display_count}개만 표시)"
                self.story.append(Spacer(1, 0.2*cm))
                self.story.append(Paragraph(note, self.styles['KoreanCaption']))
        
        # 부록 B: 분석 방법론
        self.story.append(PageBreak())
        self.story.append(Paragraph("부록 B. 분석 방법론", self.styles['KoreanHeading2']))
        self.story.append(Spacer(1, 0.3*cm))
        
        methodology_text = """
        <b>1. 데이터 수집</b><br/>
        - 출처: 서울교통공사 지하철 혼잡도 정보<br/>
        - 측정 단위: 30분 단위 평균 혼잡도<br/>
        - 측정 방식: 해당 역을 통과하는 모든 열차의 평균<br/>
        <br/>
        <b>2. 혼잡도 지표</b><br/>
        - 혼잡도 (%) = (실제 승차 인원 / 열차 정원) × 100<br/>
        - 좌석 만석 기준: 34%<br/>
        - 정원 기준: 100%<br/>
        <br/>
        <b>3. 분석 지표</b><br/>
        - 피크 혼잡: 전체 시간대 중 최대값<br/>
        - 출근 평균: 7~9시 (또는 7~9시 미만) 평균<br/>
        - 퇴근 평균: 17~20시 (또는 17~20시 미만) 평균<br/>
        - 전체 평균: 전 시간대 평균<br/>
        <br/>
        <b>4. TOP10 선정 기준</b><br/>
        - 역명 + 방향(상행/하행) 단위로 분석<br/>
        - 피크 혼잡도, 출근 평균, 퇴근 평균 각각 TOP10 선정<br/>
        """
        
        self.story.append(Paragraph(methodology_text, self.styles['KoreanNormal']))
        
        # 부록 C: 용어 정의
        self.story.append(Spacer(1, 0.5*cm))
        self.story.append(Paragraph("부록 C. 용어 정의", self.styles['KoreanHeading2']))
        self.story.append(Spacer(1, 0.3*cm))
        
        terms_data = [
            ['용어', '정의'],
            ['혼잡도', '열차 정원 대비 실제 승차 인원의 비율 (%)'],
            ['피크 혼잡', '전체 시간대 중 가장 높은 혼잡도'],
            ['출근시간', '평일 오전 출근 시간대 (기본: 7~9시)'],
            ['퇴근시간', '평일 오후 퇴근 시간대 (기본: 17~20시)'],
            ['상행/하행', '열차 운행 방향 (노선별로 정의)'],
            ['정원', '열차가 수용할 수 있는 최대 승객 수 (좌석+입석)'],
        ]
        
        terms_table = Table(terms_data, colWidths=[4*cm, 10*cm])
        terms_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Korean'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ECF0F1')])
        ]))
        
        self.story.append(terms_table)
        
        # 문의처
        self.story.append(Spacer(1, 1*cm))
        self.story.append(Paragraph("문의처", self.styles['KoreanHeading2']))
        self.story.append(Spacer(1, 0.2*cm))
        
        contact_text = f"""
        {self.report_data['metadata']['organization']}<br/>
        보고서 생성일: {self.report_data['metadata']['generated_at']}<br/>
        버전: {self.report_data['metadata']['version']}
        """
        
        self.story.append(Paragraph(contact_text, self.styles['KoreanNormal']))
    
    def _build_impact_page(self):
        """개선 효과 요약 페이지 (2025_plan.pdf 마지막 페이지 스타일)"""
        self.story.append(PageBreak())
        
        # 타이틀
        impact_title_style = ParagraphStyle(
            name='ImpactTitle',
            parent=self.styles['KoreanHeading1'],
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=colors.HexColor('#2C3E50')
        )
        self.story.append(Paragraph("운영 개선으로, 이용객의 경험이 이렇게 바뀝니다", impact_title_style))
        self.story.append(Spacer(1, 1*cm))
        
        kpi = self.report_data['kpi']
        
        # 박스형 개선 효과 (4개 항목, 2x2 그리드)
        impact_items = []
        
        # 1. 피크 시간대 혼잡 완화
        if kpi.get('peak_crowding', 0) > 100:
            impact_items.append({
                'title': '피크 시간대 혼잡 완화',
                'before': f'{kpi.get("peak_crowding", 0):.1f}%',
                'after': '100% 이하',
                'desc': '배차 간격 조정으로\n정원 초과 구간 해소'
            })
        else:
            impact_items.append({
                'title': '피크 시간대 안정 유지',
                'before': f'{kpi.get("peak_crowding", 0):.1f}%',
                'after': '지속 관리',
                'desc': '모니터링 강화로\n안정적 운영 유지'
            })
        
        # 2. 출근 시간 쾌적도 향상
        impact_items.append({
            'title': '출근 시간 쾌적도 향상',
            'before': f'{kpi.get("commute_avg", 0):.1f}%',
            'after': '▼ 10%p',
            'desc': '시차 출근 유도 및\n정보 제공 강화'
        })
        
        # 3. 퇴근 시간 분산 효과
        impact_items.append({
            'title': '퇴근 시간 분산 효과',
            'before': f'{kpi.get("evening_avg", 0):.1f}%',
            'after': '▼ 10%p',
            'desc': '배차 최적화로\n대기 시간 단축'
        })
        
        # 4. 실시간 정보 제공
        impact_items.append({
            'title': '실시간 혼잡도 정보',
            'before': '제한적',
            'after': '전 구간 제공',
            'desc': '스마트폰으로\n혼잡도 확인 가능'
        })
        
        # 2x2 그리드로 배치
        for i in range(0, len(impact_items), 2):
            row_data = []
            for j in range(2):
                if i + j < len(impact_items):
                    item = impact_items[i + j]
                    # 각 박스 내용
                    box_content = [
                        [Paragraph(f"<b>{item['title']}</b>", self.styles['KoreanNormal'])],
                        [Paragraph(f"현재: {item['before']}", self.styles['KoreanCaption'])],
                        [Paragraph(f"목표: {item['after']}", self.styles['KoreanCaption'])],
                        [Paragraph(item['desc'], self.styles['KoreanCaption'])]
                    ]
                    box_table = Table(box_content, colWidths=[7*cm])
                    box_table.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (-1, -1), 'Korean'),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ECF0F1')),
                        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#BDC3C7')),
                        ('TOPPADDING', (0, 0), (-1, -1), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ]))
                    row_data.append(box_table)
            
            # 행 테이블
            if row_data:
                row_table = Table([row_data], colWidths=[7.5*cm, 7.5*cm])
                row_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                self.story.append(row_table)
                self.story.append(Spacer(1, 0.5*cm))


def generate_pdf_report(
    report_data: Dict[str, Any],
    output_path: str
) -> str:
    """
    PDF 보고서 생성 (편의 함수)
    
    Parameters:
    -----------
    report_data : Dict[str, Any]
        보고서 데이터
    output_path : str
        출력 파일 경로
    
    Returns:
    --------
    str
        생성된 파일 경로
    """
    generator = PDFReportGenerator(report_data)
    return generator.generate(output_path)

