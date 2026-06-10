import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="빌링 납기별 분석", layout="wide")
st.title("📊 산업용 빌링 납기 부문별 종합 분석 대시보드")

@st.cache_data
def load_and_process_data():
    excel_file = "5월 산업용 상품_20260610.xlsx"
    
    if not os.path.exists(excel_file):
        st.error(f"❌ '{excel_file}' 엑셀 파일이 레포지토리에 없습니다. 파일명을 확인해주세요.")
        return None

    try:
        excel_sheets = pd.read_excel(excel_file, sheet_name=None, engine='openpyxl')
    except Exception as e:
        st.error(f"❌ 엑셀 시트를 읽어오는 중 에러가 발생했습니다: {e}")
        return None

    all_data_list = []
    
    # 시트명 키워드 매칭 (기타/일반납기 제외, 순수 5대 부문만 추출)
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
            
        if category_name:
            df_sheet.columns = df_sheet.columns.str.strip()
            if '고객명' in df_sheet.columns and '사용량' in df_sheet.columns:
                df_filtered = df_sheet[['고객명', '사용량']].copy()
                df_filtered['부문'] = category_name
                all_data_list.append(df_filtered)
            
    if not all_data_list:
        st.error("❌ 엑셀 파일 내에서 매칭 가능한 시트를 찾지 못했습니다.")
        return None
        
    df_master = pd.concat(all_data_list, ignore_index=True)
    
    if df_master['사용량'].dtype == object:
        df_master['사용량'] = df_master['사용량'].astype(str).str.replace(',', '', regex=False)
    df_master['사용량'] = pd.to_numeric(df_master['사용량'], errors='coerce').fillna(0)
    
    return df_master

# --- 데이터 로드 ---
df_master = load_and_process_data()

if df_master is not None:
    # 1. 시트별 기초 집계 (보이는 5대 부문만)
    summary = df_master.groupby('부문')['사용량'].sum().reset_index()
    summary.columns = ['부문', '부문별 판매량(m3)']
    
    ordered_categories = ['산업용 1회', '산업용월말(2회)', '산업용기타(2회)', '산업용3회', '업무용 납기']
    
    for cat in ordered_categories:
        if cat not in summary['부문'].values:
            summary = pd.concat([summary, pd.DataFrame({'부문': [cat], '부문별 판매량(m3)': [0.0]})], ignore_index=True)
            
    summary['부문'] = pd.Categorical(summary['부문'], categories=ordered_categories, ordered=True)
    summary = summary.sort_values('부문').reset_index(drop=True)
    
    # 화면에 보이는 부문들의 순수 총합 계산
    visible_total = summary['부문별 판매량(m3)'].sum()
    summary['전체대비 비율(%)'] = (summary['부문별 판매량(m3)'] / visible_total) * 100

    # ----------------------------------------------------
    # 1️⃣ 상단 레이아웃: 요약 표 & 도넛 차트
    # ----------------------------------------------------
    st.markdown("### 📊 1. 납기 부문별 판매량 및 비율 현황")
    
    col_table, col_chart = st.columns([5, 5])
    
    with col_table:
        st.markdown("##### 📋 부문별 정산 요약표")
        
        total_row = pd.DataFrame({
            '부문': ['📊 총합계 (Grand Total)'],
            '부문별 판매량(m3)': [visible_total],
            '전체대비 비율(%)': [100.0]
        })
        
        display_df = pd.concat([summary, total_row], ignore_index=True)
        
        formatted_df = display_df.copy()
        formatted_df['부문별 판매량(m3)'] = formatted_df['부문별 판매량(m3)'].map('{:,.0f} m³'.format)
        formatted_df['전체대비 비율(%)'] = formatted_df['전체대비 비율(%)'].map('{:.2f}%'.format)
        
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
    # 2️⃣ 하단 레이아웃: 활성화 버튼 기반 부문별 업체 조회
    # ----------------------------------------------------
    st.markdown("### 🏢 2. 부문별 판매량 고객 현황")
    
    selected_sector = st.radio(
        "조회할 납기 부문을 선택(활성화)하세요:",
        options=ordered_categories,
        horizontal=True
    )
    
    if selected_sector:
        sector_df = df_master[df_master['부문'] == selected_sector]
        
        if len(sector_df) == 0:
            st.info(f"💡 '{selected_sector}' 부문의 고객 내역이 없습니다.")
        else:
            # 상위 10개 추출
            top_10 = sector_df.groupby('고객명')['사용량'].sum().reset_index()
            top_10 = top_10.sort_values(by='사용량', ascending=False).head(10).reset_index(drop=True)
            
            col_bar, col_list = st.columns([6, 4])
            
            with col_bar:
                # "상위 10개사" 문구 삭제, 요청하신 문구로 대체
                fig_bar = px.bar(
                    top_10,
                    x='사용량',
                    y='고객명',
                    orientation='h',
                    text='사용량',
                    color='사용량',
                    color_continuous_scale=px.colors.sequential.Teal,
                    title=f"[{selected_sector}] 판매량 고객"
                )
                fig_bar.update_traces(texttemplate='<b>%{text:,.0f} m³</b>', textposition='outside', textfont_size=12)
                fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, margin=dict(r=120))
                st.plotly_chart(fig_bar, use_container_width=True)
                
            with col_list:
                st.markdown(f"##### 🏆 [{selected_sector}] 판매량 고객")
                
                # 표 최하단 합계 행 추가 로직
                total_usage = top_10['사용량'].sum()
                top_10.loc[len(top_10)] = ['🟦 합계', total_usage]
                
                # 순위 인덱스 (마지막 합계는 '-' 표기)
                top_10.index = list(range(1, len(top_10))) + ['-']
                
                top_10['사용량'] = top_10['사용량'].map('{:,.0f} m³'.format)
                
                def highlight_bottom_total(row):
                    if '합계' in str(row['고객명']):
                        return ['background-color: #D6EAF8; font-weight: bold; color: #1B4F72;'] * len(row)
                    return [''] * len(row)
                    
                styled_top10 = top_10.style.apply(highlight_bottom_total, axis=1)
                st.dataframe(styled_top10, use_container_width=True)

    st.divider()

    # ----------------------------------------------------
    # 3️⃣ 최하단 레이아웃: 부문별 사용일 기준표 (가로형)
    # ----------------------------------------------------
    st.markdown("### 📅 3. 부문별 사용일 기준 (관리납기)")
    
    # 사진을 기반으로 재구성한 데이터 (텍스트는 업무 상황에 맞게 수정 가능)
    schedule_data = {
        '청구유형(부문)': ['산업용 1회', '산업용월말(2회)', '산업용기타(2회)', '산업용3회', '업무용 납기'],
        '1회차 (사용기간)': ['전월 1일 ~ 전월 말일', '전월 1일 ~ 전월 15일', '전월 16일 ~ 당월 15일', '전월 1일 ~ 전월 10일', '전월 16일 ~ 당월 15일'],
        '2회차 (사용기간)': ['-', '전월 16일 ~ 전월 말일', '당월 1일 ~ 당월 15일', '전월 11일 ~ 전월 20일', '-'],
        '3회차 (사용기간)': ['-', '-', '-', '전월 21일 ~ 전월 말일', '-']
    }
    
    df_schedule = pd.DataFrame(schedule_data)
    
    # 깔끔한 테이블 렌더링
    st.table(df_schedule)
