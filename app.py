import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="빌링 납기별 분석", layout="wide")
st.title("📊 산업용 빌링 납기 부문별 종합 분석 대시보드 (6대 부문)")

@st.cache_data
def load_and_process_data():
    # 1. 정산서 기준 총합계 명시적 고정 (Han형님 요청값)
    total_baseline = 17076293.0
    
    # 2. 엑셀 파일 내 시트 로드
    excel_file = "5월 산업용 상품_20260610.xlsx"
    
    if not os.path.exists(excel_file):
        st.error(f"❌ '{excel_file}' 엑셀 파일이 레포지토리에 없습니다. 파일명을 확인해주세요.")
        return None, 0

    try:
        excel_sheets = pd.read_excel(excel_file, sheet_name=None, engine='openpyxl')
    except Exception as e:
        st.error(f"❌ 엑셀 시트를 읽어오는 중 에러가 발생했습니다: {e}")
        return None, 0

    all_data_list = []
    
    # [수정포인트 1] 시트명 키워드 매칭 방식 도입 (띄어쓰기 오차로 인한 합산 누락 방지)
    for raw_sheet_name, df_sheet in excel_sheets.items():
        sheet_name = str(raw_sheet_name).strip()
        category_name = None
        
        if '산업용월말(1회)' in sheet_name:
            category_name = '산업용 1회'
        elif '산업용월말(2회)' in sheet_name:
            category_name = '산업용월말(2회)'
        elif '산업용기타(2회)' in sheet_name:
            category_name = '산업용기타(2회)'
        elif '산업용3회' in sheet_name:
            category_name = '산업용3회'
        elif '업무용' in sheet_name:
            category_name = '업무용 납기'
        elif '일반납기' in sheet_name:
            category_name = '기타'
            
        if category_name:
            # 컬럼명에 있는 공백 제거 후 데이터 추출
            df_sheet.columns = df_sheet.columns.str.strip()
            if '고객명' in df_sheet.columns and '사용량' in df_sheet.columns:
                df_filtered = df_sheet[['고객명', '사용량']].copy()
                df_filtered['부문'] = category_name
                all_data_list.append(df_filtered)
            
    if not all_data_list:
        st.error("❌ 엑셀 파일 내에서 매칭 가능한 시트를 찾지 못했습니다.")
        return None, 0
        
    df_master = pd.concat(all_data_list, ignore_index=True)
    
    # 사용량 숫자형 변환 (쉼표 제거)
    if df_master['사용량'].dtype == object:
        df_master['사용량'] = df_master['사용량'].astype(str).str.replace(',', '', regex=False)
    df_master['사용량'] = pd.to_numeric(df_master['사용량'], errors='coerce').fillna(0)
    
    return df_master, total_baseline

# --- 데이터 로드 ---
result = load_and_process_data()

if result[0] is not None:
    df_master, total_baseline = result
    
    # 1. 시트별 기초 집계
    summary = df_master.groupby('부문')['사용량'].sum().reset_index()
    summary.columns = ['부문', '부문별 판매량(m3)']
    
    ordered_categories = ['산업용 1회', '산업용월말(2회)', '산업용기타(2회)', '산업용3회', '업무용 납기', '기타']
    
    for cat in ordered_categories:
        if cat not in summary['부문'].values:
            summary = pd.concat([summary, pd.DataFrame({'부문': [cat], '부문별 판매량(m3)': [0.0]})], ignore_index=True)
            
    # 2. 기타 물량 재계산 (총합계 17,076,293 보장)
    sum_1_to_5 = summary[summary['부문'] != '기타']['부문별 판매량(m3)'].sum()
    corrected_etc_volume = total_baseline - sum_1_to_5
    summary.loc[summary['부문'] == '기타', '부문별 판매량(m3)'] = corrected_etc_volume
    
    summary['부문'] = pd.Categorical(summary['부문'], categories=ordered_categories, ordered=True)
    summary = summary.sort_values('부문').reset_index(drop=True)
    
    # [수정포인트 2] 고정된 총합계(17,076,293)를 분모로 한 정확한 비율 계산
    summary['전체대비 비율(%)'] = (summary['부문별 판매량(m3)'] / total_baseline) * 100

    # ----------------------------------------------------
    # 1️⃣ 상단 레이아웃: 요약 표 & 도넛 차트
    # ----------------------------------------------------
    st.markdown("### 📊 1. 6대 납기 부문별 판매량 및 비율 현황")
    
    col_table, col_chart = st.columns([5, 5])
    
    with col_table:
        st.markdown("##### 📋 부문별 최종 정산 요약표")
        
        total_row = pd.DataFrame({
            '부문': ['📊 총합계 (Grand Total)'],
            '부문별 판매량(m3)': [total_baseline],
            '전체대비 비율(%)': [100.0]
        })
        
        display_df = pd.concat([summary, total_row], ignore_index=True)
        
        formatted_df = display_df.copy()
        formatted_df['부문별 판매량(m3)'] = formatted_df['부문별 판매량(m3)'].map('{:,.0f} m³'.format)
        formatted_df['전체대비 비율(%)'] = formatted_df['전체대비 비율(%)'].map('{:.2f}%'.format)
        
        # [수정포인트 3] 표 최상단 헤더와 최하단 총합계 동시 하이라이트 스타일링
        def style_table(row):
            if '총합계' in str(row['부문']):
                return ['background-color: #D6EAF8; font-weight: bold; color: #1B4F72;'] * len(row)
            return [''] * len(row)
            
        header_styles = [
            {'selector': 'th', 'props': [('background-color', '#1B4F72'), ('color', 'white'), ('font-weight', 'bold'), ('font-size', '14px')]}
        ]
        
        styled_table = formatted_df.style.apply(style_table, axis=1).set_table_styles(header_styles)
        st.dataframe(styled_table, use_container_width=True, hide_index=True)

    with col_chart:
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
