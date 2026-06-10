import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="빌링 납기별 분석", layout="wide")
st.title("📊 산업용 빌링 납기 부문별 종합 분석 대시보드 (6대 부문)")

@st.cache_data
def load_and_process_data():
    encodings = ['cp949', 'utf-8', 'euc-kr', 'utf-8-sig']
    
    # 1. [기준점] 판매량정산서(확정) 원장 데이터 로드 및 산업용 필터링
    main_file = "가정용외_202605.csv"
    total_industrial_volume = 0
    
    if os.path.exists(main_file):
        for enc in encodings:
            try:
                df_main = pd.read_csv(main_file, encoding=enc)
                df_ind_main = df_main[df_main['상품명'].str.contains('산업용', na=False)].copy()
                
                if df_ind_main['사용량(m3)'].dtype == object:
                    df_ind_main['사용량(m3)'] = df_ind_main['사용량(m3)'].astype(str).str.replace(',', '')
                df_ind_main['사용량(m3)'] = pd.to_numeric(df_ind_main['사용량(m3)'], errors='coerce').fillna(0)
                
                # 원장 기준 산업용 상품 전체 합 확정
                total_industrial_volume = df_ind_main['사용량(m3)'].sum()
                break
            except:
                continue

    # 2. 엑셀 파일 내 시트명과 6대 부문 매핑 (요청하신 순서 및 시트 매칭)
    excel_file = "5월 산업용 상품_20260610.xlsx"
    
    sheet_to_category = {
        '산업용월말(1회)_5월': '산업용 1회',                    # 1번째 시트
        '산업용월말(2회)_5월1회차': '산업용월말(2회)',             # 2번째 시트
        '산업용월말(2회)_5월2회차': '산업용월말(2회)',             # 3번째 시트
        '산업용기타(2회)_1회차_5월1회차': '산업용기타(2회)',         # 4번째 시트
        '산업용기타(2회)_5월2회차': '산업용기타(2회)',             # 5번째 시트
        '산업용3회_5월1회차': '산업용3회',                     # 6번째 시트
        '산업용3회_5월2회차': '산업용3회',                     # 7번째 시트
        '산업용3회_5월3회차': '산업용3회',                     # 8번째 시트
        '업무용_5월': '업무용 납기',                            # 업무용 납기 시트
        '일반납기_5월': '기타'                                 # 기타 부문의 기본 베이스
    }
    
    if not os.path.exists(excel_file):
        st.error(f"❌ '{excel_file}' 엑셀 파일이 레포지토리에 없습니다. 파일명을 확인해주세요.")
        return None, 0

    try:
        excel_sheets = pd.read_excel(excel_file, sheet_name=None, engine='openpyxl')
    except Exception as e:
        st.error(f"❌ 엑셀 시트를 읽어오는 중 에러가 발생했습니다: {e}")
        return None, 0

    all_data_list = []
    for sheet_name, df_sheet in excel_sheets.items():
        if sheet_name in sheet_to_category:
            category_name = sheet_to_category[sheet_name]
            df_filtered = df_sheet[['고객명', '사용량']].copy()
            df_filtered['부문'] = category_name
            all_data_list.append(df_filtered)
            
    if not all_data_list:
        st.error("❌ 엑셀 파일 내에서 매칭 가능한 시트를 찾지 못했습니다.")
        return None, 0
        
    df_master = pd.concat(all_data_list, ignore_index=True)
    
    if df_master['사용량'].dtype == object:
        df_master['사용량'] = df_master['사용량'].astype(str).str.replace(',', '')
    df_master['사용량'] = pd.to_numeric(df_master['사용량'], errors='coerce').fillna(0)
    
    return df_master, total_industrial_volume

# --- 데이터 로드 ---
result = load_and_process_data()

if result[0] is not None:
    df_master, total_baseline = result
    
    # 1. 시트별 기초 집계
    summary = df_master.groupby('부문')['사용량'].sum().reset_index()
    summary.columns = ['부문', '부문별 판매량(m3)']
    
    # 정의된 6대 부문 레이블 순서 고정
    ordered_categories = ['산업용 1회', '산업용월말(2회)', '산업용기타(2회)', '산업용3회', '업무용 납기', '기타']
    
    # 빈 부문이 있을 경우를 대비해 기본값 0 구조 확보
    for cat in ordered_categories:
        if cat not in summary['부문'].values:
            summary = pd.concat([summary, pd.DataFrame({'부문': [cat], '부문별 판매량(m3)': [0.0]})], ignore_index=True)
            
    # 2. 🟩 [핵심 정산 보정] 기타 물량의 재계산 🟩
    # '기타'를 제외한 1~5번 부문의 순수 합계 계산
    sum_1_to_5 = summary[summary['부문'] != '기타']['부문별 판매량(m3)'].sum()
    
    # 기타 물량 = 원장 확정 총합 - 1~5번 부문 합계 (일반납기 및 미매칭 오차 자동 포함)
    corrected_etc_volume = total_baseline - sum_1_to_5
    summary.loc[summary['부문'] == '기타', '부문별 판매량(m3)'] = corrected_etc_volume
    
    # 순서 정렬 적용
    summary['부문'] = pd.Categorical(summary['부문'], categories=ordered_categories, ordered=True)
    summary = summary.sort_values('부문').reset_index(drop=True)
    
    # 비율 계산 (확정 총합계 기준 100% 분할)
    summary['전체대비 비율(%)'] = (summary['부문별 판매량(m3)'] / total_baseline) * 100

    # ----------------------------------------------------
    # 1️⃣ 상단 레이아웃: 요약 표 (최하단 총합계 하이라이트) & 도넛 차트
    # ----------------------------------------------------
    st.markdown("### 📊 1. 6대 납기 부문별 판매량 및 비율 현황")
    
    col_table, col_chart = st.columns([5, 5])
    
    with col_table:
        st.markdown("##### 📋 부문별 최종 정산 요약표")
        
        # 최하단에 원장 확정값과 일치하는 총합계 행 추가
        total_row = pd.DataFrame({
            '부문': ['📊 총합계 (Grand Total)'],
            '부문별 판매량(m3)': [total_baseline],
            '전체대비 비율(%)': [100.0]
        })
        
        display_df = pd.concat([summary, total_row], ignore_index=True)
        
        # 포맷 가공
        formatted_df = display_df.copy()
        formatted_df['부문별 판매량(m3)'] = formatted_df['부문별 판매량(m3)'].map('{:,.0f} m³'.format)
        formatted_df['전체대비 비율(%)'] = formatted_df['전체대비 비율(%)'].map('{:.2f}%'.format)
        
        # 최하단 총합계 행 연푸른색 하이라이트 스타일 적용
        def style_grand_total(row):
            if '총합계' in str(row['부문']):
                return ['background-color: #D6EAF8; font-weight: bold; color: #1B4F72;'] * len(row)
            return [''] * len(row)
            
        styled_table = formatted_df.style.apply(style_grand_total, axis=1)
        st.dataframe(styled_table, use_container_width=True, hide_index=True)

    with col_chart:
        # 도넛 차트 시각화 (기타 보정치 포함 100% 매칭)
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
    
    selected_sector = st.radio(
        "조회할 납기 부문을 선택(활성화)하세요:",
        options=ordered_categories,
        horizontal=True
    )
    
    if selected_sector:
        # 해당 부문 데이터 필터링 후 정렬
        sector_df = df_master[df_master['부문'] == selected_sector]
        
        if len(sector_df) == 0:
            st.info(f"💡 '{selected_sector}' 부문에 직접 매핑된 고객 세부 내역이 시트에 존재하지 않거나 보정 물량 탭입니다.")
        else:
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
                    title=f"[{selected_sector}] 판매량 상위 10개사"
                )
                fig_bar.update_traces(texttemplate='<b>%{text:,.0f} m³</b>', textposition='outside', textfont_size=12)
                fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, margin=dict(r=120))
                st.plotly_chart(fig_bar, use_container_width=True)
                
            with col_list:
                st.markdown(f"##### 🏆 [{selected_sector}] 순위 리스트")
                top_10.index = top_10.index + 1
                top_10['사용량'] = top_10['사용량'].map('{:,.0f} m³'.format)
                st.dataframe(top_10, use_container_width=True)
