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
    # 1. 시트별 기초 집계
    summary = df_master.groupby('부문').agg(
        부문별_판매량=('사용량', 'sum'),
        업체수=('고객명', 'nunique')
    ).reset_index()
    
    summary.rename(columns={'부문별_판매량': '부문별 판매량(m3)', '업체수': '업체수(개소)'}, inplace=True)
    
    ordered_categories = ['산업용 1회', '산업용월말(2회)', '산업용기타(2회)', '산업용3회', '업무용 납기']
    
    for cat in ordered_categories:
        if cat not in summary['부문'].values:
            empty_row = pd.DataFrame({'부문': [cat], '부문별 판매량(m3)': [0.0], '업체수(개소)': [0]})
            summary = pd.concat([summary, empty_row], ignore_index=True)
            
    summary['부문'] = pd.Categorical(summary['부문'], categories=ordered_categories, ordered=True)
    summary = summary.sort_values('부문').reset_index(drop=True)
    
    visible_total = summary['부문별 판매량(m3)'].sum()
    total_companies = summary['업체수(개소)'].sum()
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
            '업체수(개소)': [total_companies],
            '전체대비 비율(%)': [100.0]
        })
        
        display_df = pd.concat([summary, total_row], ignore_index=True)
        display_df = display_df[['부문', '업체수(개소)', '부문별 판매량(m3)', '전체대비 비율(%)']]
        
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
            total_sector_vol = sector_df['사용량'].sum()
            total_sector_cnt = sector_df['고객명'].nunique()
            
            st.markdown(f"**📌 [{selected_sector}] 전체 업체 수:** {total_sector_cnt:,} 개소 &nbsp;&nbsp;|&nbsp;&nbsp; **전체 사용량 총합:** {total_sector_vol:,.0f} m³")
            
            grouped = sector_df.groupby('고객명')['사용량'].sum().reset_index().sort_values(by='사용량', ascending=False)
            top_10_chart = grouped.head(10).copy()
            
            col_bar, col_list = st.columns([6, 4])
            
            with col_bar:
                fig_bar = px.bar(
                    top_10_chart,
                    x='사용량',
                    y='고객명',
                    orientation='h',
                    text='사용량',
                    color='사용량',
                    color_continuous_scale=px.colors.sequential.Teal,
                    title=f"[{selected_sector}] 판매량 상위 고객"
                )
                fig_bar.update_traces(texttemplate='<b>%{text:,.0f} m³</b>', textposition='outside', textfont_size=12)
                fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, margin=dict(r=120))
                st.plotly_chart(fig_bar, use_container_width=True)
                
            with col_list:
                st.markdown(f"##### 🏆 [{selected_sector}] 판매량 고객 표")
                
                display_list = grouped.head(10).copy()
                
                if len(grouped) > 10:
                    others_vol = grouped.iloc[10:]['사용량'].sum()
                    display_list.loc[len(display_list)] = ['📁 기타', others_vol]
                
                display_list.loc[len(display_list)] = ['🟦 총계', total_sector_vol]
                
                ranks = []
                rank_num = 1
                for name in display_list['고객명']:
                    if '기타' in str(name) or '총계' in str(name):
                        ranks.append('-')
                    else:
                        ranks.append(str(rank_num))
                        rank_num += 1
                        
                display_list.insert(0, '순위', ranks)
                display_list['사용량'] = display_list['사용량'].map('{:,.0f} m³'.format)
                
                def highlight_bottom_total(row):
                    if '총계' in str(row['고객명']):
                        return ['background-color: #D6EAF8; font-weight: bold; color: #1B4F72;'] * len(row)
                    return [''] * len(row)
                    
                styled_list = display_list.style.apply(highlight_bottom_total, axis=1)
                st.dataframe(styled_list, use_container_width=True, hide_index=True)

    st.divider()

    # ----------------------------------------------------
    # 3️⃣ 하단 레이아웃: 부문별 사용일 기준표
    # ----------------------------------------------------
    st.markdown("### 📅 3. 부문별 사용일 기준 (관리납기)")
    
    schedule_data = {
        '청구유형(부문)': ['산업용 1회', '산업용월말(2회)', '산업용기타(2회)', '산업용3회', '업무용 납기'],
        '1회차 (사용기간)': ['전월 1일 ~ 전월 말일', '전월 1일 ~ 전월 15일', '전월 16일 ~ 당월 15일', '전월 1일 ~ 전월 10일', '전월 16일 ~ 당월 15일'],
        '2회차 (사용기간)': ['-', '전월 16일 ~ 전월 말일', '당월 1일 ~ 당월 15일', '전월 11일 ~ 전월 20일', '-'],
        '3회차 (사용기간)': ['-', '-', '-', '전월 21일 ~ 전월 말일', '-']
    }
    
    df_schedule = pd.DataFrame(schedule_data)
    st.table(df_schedule)

    st.divider()

    # ----------------------------------------------------
    # 4️⃣ 최하단 레이아웃: 전체 산업용 Top 30 기업 표
    # ----------------------------------------------------
    st.markdown("### 🏆 4. 전체 산업용 고객 판매량 Top 30")
    
    # 고객명과 부문을 기준으로 전체 사용량 합산 후 상위 30개사 추출
    top30_df = df_master.groupby(['고객명', '부문'], as_index=False)['사용량'].sum()
    top30_df = top30_df.sort_values(by='사용량', ascending=False).head(30).reset_index(drop=True)
    
    # 순위 컬럼 동적 추가 (데이터 길이에 맞춰 1번부터 부여)
    top30_df.insert(0, '순위', range(1, len(top30_df) + 1))
    
    # 요청하신 컬럼명으로 변경
    top30_df.rename(columns={'부문': '납기구분', '사용량': '사용'}, inplace=True)
    
    # 숫자 포맷팅 (콤마 및 m³ 단위)
    top30_df['사용'] = top30_df['사용'].map('{:,.0f} m³'.format)
    
    # 출력할 컬럼 순서 지정
    display_top30 = top30_df[['순위', '고객명', '사용', '납기구분']]
    
    # 깔끔하게 인덱스를 숨기고 화면 너비에 맞게 출력
    st.dataframe(display_top30, use_container_width=True, hide_index=True)
