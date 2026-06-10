import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="빌링 납기별 분석", layout="wide")
st.title("📊 산업용 빌링 납기 부문별 종합 분석 대시보드")

@st.cache_data
def load_and_process_data():
    # 1. 원장 기준 전체 판매량 로드 (가정용외_202605.csv)
    main_file = "가정용외_202605.csv"
    total_industrial_volume = 0
    
    if os.path.exists(main_file):
        for enc in ['cp949', 'utf-8', 'euc-kr', 'utf-8-sig']:
            try:
                df_main = pd.read_csv(main_file, encoding=enc)
                df_ind_main = df_main[df_main['상품명'].str.contains('산업용', na=False)].copy()
                if df_ind_main['사용량(m3)'].dtype == object:
                    df_ind_main['사용량(m3)'] = df_ind_main['사용량(m3)'].astype(str).str.replace(',', '')
                df_ind_main['사용량(m3)'] = pd.to_numeric(df_ind_main['사용량(m3)'], errors='coerce').fillna(0)
                total_industrial_volume = df_ind_main['사용량(m3)'].sum()
                break
            except:
                continue

    # 2. 엑셀 파일 내 시트명과 5대 부문 매핑 정의
    excel_file = "5월 산업용 상품_20260610.xlsx"
    
    sheet_to_category = {
        '산업용월말(1회)_5월': '산업용 1회',
        '산업용월말(2회)_5월1회차': '산업용월말(2회)',
        '산업용월말(2회)_5월2회차': '산업용월말(2회)',
        '산업용기타(2회)_1회차_5월1회차': '산업용기타(2회)',
        '산업용기타(2회)_5월2회차': '산업용기타(2회)',
        '산업용3회_5월1회차': '산업용3회',
        '산업용3회_5월2회차': '산업용3회',
        '산업용3회_5월3회차': '산업용3회',
        '일반납기_5월': '일반납기'
    }
    
    if not os.path.exists(excel_file):
        st.error(f"❌ 깃허브에 '{excel_file}' 파일이 존재하지 않습니다. 파일명을 확인해주세요.")
        return None, 0

    try:
        # openpyxl 엔진을 사용하여 모든 시트를 딕셔너리 형태로 한 번에 로드
        excel_sheets = pd.read_excel(excel_file, sheet_name=None, engine='openpyxl')
    except Exception as e:
        st.error(f"❌ 엑셀 파일을 읽는 중 오류가 발생했습니다: {e}")
        return None, 0

    all_data_list = []
    
    # 엑셀 내 시트들을 순회하며 지정된 부문으로 통합
    for sheet_name, df_sheet in excel_sheets.items():
        # Han형님이 지정해주신 5대 부문에 해당되는 시트만 추출
        if sheet_name in sheet_to_category:
            category_name = sheet_to_category[sheet_name]
            
            # 필요한 컬럼 정제
            df_filtered = df_sheet[['고객명', '사용량']].copy()
            df_filtered['부문'] = category_name
            all_data_list.append(df_filtered)
            
    if not all_data_list:
        st.error("❌ 지정된 시트명과 일치하는 데이터가 엑셀 파일 내에 없습니다.")
        return None, 0
        
    df_master = pd.concat(all_data_list, ignore_index=True)
    
    # 사용량 숫자형 변환 및 예외 처리
    if df_master['사용량'].dtype == object:
        df_master['사용량'] = df_master['사용량'].astype(str).str.replace(',', '')
    df_master['사용량'] = pd.to_numeric(df_master['사용량'], errors='coerce').fillna(0)
    
    # 만약 원장 파일이 없거나 비어있다면 검침 시트 총합을 기준 삼음
    if total_industrial_volume == 0:
        total_industrial_volume = df_master['사용량'].sum()
        
    return df_master, total_industrial_volume

# --- 데이터 로드 및 실행 ---
result = load_and_process_data()

if result[0] is not None:
    df_master, total_baseline = result
    
    # 부문별 총합 계산
    summary = df_master.groupby('부문')['사용량'].sum().reset_index()
    summary.columns = ['부문', '부문별 판매량(m3)']
    
    # Han형님 요청 순서로 정렬 고정
    ordered_categories = ['산업용 1회', '산업용월말(2회)', '산업용기타(2회)', '산업용3회', '일반납기']
    summary['부문'] = pd.Categorical(summary['부문'], categories=ordered_categories, ordered=True)
    summary = summary.sort_values('부문').reset_index(drop=True)
    
    # 비율 계산 (원장 전체 판매량 대비 차지하는 비율)
    summary['전체대비 비율(%)'] = (summary['부문별 판매량(m3)'] / total_baseline) * 100
    
    # 시트 합계 총합산량 계산
    sheets_total_volume = summary['부문별 판매량(m3)'].sum()
    sheets_total_ratio = summary['전체대비 비율(%)'].sum()

    # ----------------------------------------------------
    # 1️⃣ 상단 레이아웃: 표 (하단 총합계 하이라이트) & 도넛 차트
    # ----------------------------------------------------
    st.markdown("### 📊 1. 납기 부문별 판매량 및 비율 현황")
    
    col_table, col_chart = st.columns([5, 5])
    
    with col_table:
        st.markdown("##### 📋 부문별 판매량 요약")
        
        # ✅ 요청 반영: 표 맨 하단(최하단)에 배치할 총합계 행 생성
        total_row = pd.DataFrame({
            '부문': ['📊 총합계 (Grand Total)'],
            '부문별 판매량(m3)': [sheets_total_volume],
            '전체대비 비율(%)': [sheets_total_ratio]
        })
        
        display_df = pd.concat([summary, total_row], ignore_index=True)
        
        # 데이터 출력 포맷 가공
        formatted_df = display_df.copy()
        formatted_df['부문별 판매량(m3)'] = formatted_df['부문별 판매량(m3)'].map('{:,.0f} m³'.format)
        formatted_df['전체대비 비율(%)'] = formatted_df['전체대비 비율(%)'].map('{:.2f}%'.format)
        
        # ✅ 요청 반영: 맨 하단 총합계 행 하이라이트 스타일 함수
        def style_grand_total(row):
            if '총합계' in str(row['부문']):
                return ['background-color: #D6EAF8; font-weight: bold; color: #1B4F72;'] * len(row)
            return [''] * len(row)
            
        styled_table = formatted_df.style.apply(style_grand_total, axis=1)
        st.dataframe(styled_table, use_container_width=True, hide_index=True)

    with col_chart:
        # 도넛 차트 표현 (양과 비율 모두 바깥쪽에 표시)
        fig = px.pie(
            summary,
            names='부문',
            values='부문별 판매량(m3)',
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Teal_r
        )
        fig.update_traces(
            textposition='outside',
            textinfo='label+value+percent',
            texttemplate='<b>%{label}</b><br>%{value:,.0f} m³<br>(%{percent})',
            textfont_size=13
        )
        fig.update_layout(showlegend=False, margin=dict(t=40, b=40, l=40, r=40))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ----------------------------------------------------
    # 2️⃣ 하단 레이아웃: 활성화 버튼 기반 부문별 Top 10 업체
    # ----------------------------------------------------
    st.markdown("### 🏢 2. 부문별 최다 사용 업체 순위 (Top 10)")
    
    # 부문 선택 라디오 버튼 (활성화 토글)
    selected_sector = st.radio(
        "조회할 납기 부문을 선택(활성화)하세요:",
        options=ordered_categories,
        horizontal=True
    )
    
    if selected_sector:
        # 선택된 부문의 데이터만 필터링 후 업체별 합산 정렬
        sector_df = df_master[df_master['부문'] == selected_sector]
        top_10 = sector_df.groupby('고객명')['사용량'].sum().reset_index()
        top_10 = top_10.sort_values(by='사용량', ascending=False).head(10).reset_index(drop=True)
        
        col_bar, col_list = st.columns([6, 4])
        
        with col_bar:
            fig_bar = px.bar(
                top_10,
                x='사용량',
                y='고객명',
                orientation='h',
                text='사용량',
                color='사용량',
                color_continuous_scale=px.colors.sequential.Teal,
                title=f"[{selected_sector}] 판매량 상위 10개사 그래프"
            )
            fig_bar.update_traces(texttemplate='<b>%{text:,.0f} m³</b>', textposition='outside', textfont_size=12)
            fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, margin=dict(r=120))
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_list:
            st.markdown(f"##### 🏆 [{selected_sector}] 순위 리스트")
            top_10.index = top_10.index + 1  # 1등부터 표기
            top_10['사용량'] = top_10['사용량'].map('{:,.0f} m³'.format)
            st.dataframe(top_10, use_container_width=True)
