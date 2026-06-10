import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="빌링 납기별 분석", layout="wide")
st.title("📊 산업용 빌링 납기 부문별 종합 분석 대시보드")

@st.cache_data
def load_and_process_data():
    encodings = ['cp949', 'utf-8', 'euc-kr', 'utf-8-sig']
    
    # Han형님이 지정해주신 5가지 부문별 파일 매핑 파트
    category_mapping = {
        '산업용 1회': [
            "5월 산업용 상품_20260610.xlsx - 산업용월말(1회)_5월.csv"
        ],
        '산업용월말(2회)': [
            "5월 산업용 상품_20260610.xlsx - 산업용월말(2회)_5월1회차.csv",
            "5월 산업용 상품_20260610.xlsx - 산업용월말(2회)_5월2회차.csv"
        ],
        '산업용기타(2회)': [
            "5월 산업용 상품_20260610.xlsx - 산업용기타(2회)_1회차_5월1회차.csv",
            "5월 산업용 상품_20260610.xlsx - 산업용기타(2회)_5월2회차.csv"
        ],
        '산업용3회': [
            "5월 산업용 상품_20260610.xlsx - 산업용3회_5월1회차.csv",
            "5월 산업용 상품_20260610.xlsx - 산업용3회_5월2회차.csv",
            "5월 산업용 상품_20260610.xlsx - 산업용3회_5월3회차.csv"
        ],
        '일반납기': [
            "5월 산업용 상품_20260610.xlsx - 일반납기_5월.csv"
        ]
    }
    
    all_data_list = []
    
    # 파일 읽기 및 부문 매핑 실행
    for category_name, files in category_mapping.items():
        for file in files:
            if os.path.exists(file):
                for enc in encodings:
                    try:
                        df = pd.read_csv(file, encoding=enc)
                        # 필요한 컬럼만 추출 및 부문 라벨링
                        df_cleaned = df[['고객명', '사용량']].copy()
                        df_cleaned['부문'] = category_name
                        all_data_list.append(df_cleaned)
                        break
                    except:
                        continue
            else:
                st.warning(f"⚠️ 깃허브에 '{file}' 파일이 없는 것 같습니다. 확인이 필요합니다.")
                
    if not all_data_list:
        st.error("❌ 데이터를 하나도 로드하지 못했습니다. 파일명을 확인해주세요.")
        return None
        
    # 전체 데이터 합치기
    df_master = pd.concat(all_data_list, ignore_index=True)
    
    # 사용량 데이터 전처리 (쉼표 제거 및 숫자형 변환)
    if df_master['사용량'].dtype == object:
        df_master['사용량'] = df_master['사용량'].astype(str).str.replace(',', '')
    df_master['사용량'] = pd.to_numeric(df_master['사용량'], errors='coerce').fillna(0)
    
    return df_master

# 데이터 로드
df_master = load_and_process_data()

if df_master is not None:
    # --- 1. 부문별 총합 및 비율 계산 ---
    summary = df_master.groupby('부문')['사용량'].sum().reset_index()
    grand_total_volume = summary['사용량'].sum()
    summary['비율(%)'] = (summary['사용량'] / grand_total_volume) * 100
    
    # Han형님이 정해주신 순서대로 표 정렬
    ordered_categories = ['산업용 1회', '산업용월말(2회)', '산업용기타(2회)', '산업용3회', '일반납기']
    summary['부문'] = pd.Categorical(summary['부문'], categories=ordered_categories, ordered=True)
    summary = summary.sort_values('부문').reset_index(drop=True)

    # --- 2. 상단 레이아웃: 표와 도넛 차트 표현 ---
    st.markdown("### 📊 1. 납기 부문별 판매량 및 비율 (5대 부문)")
    
    col_table, col_chart = st.columns([5, 5])
    
    with col_table:
        st.markdown("##### 📋 부문별 집계 현황 (맨 아래 총합계 고정)")
        
        # 표 하단에 붙일 총합계 데이터 생성
        total_row = pd.DataFrame({
            '부문': ['🟩 총합계 (Grand Total)'],
            '사용량': [grand_total_volume],
            '비율(%)': [100.0]
        })
        
        display_df = pd.concat([summary, total_row], ignore_index=True)
        
        # 포맷팅 적용 (가독성을 위한 콤마 및 % 표기)
        display_df['사용량'] = display_df['사용량'].map('{:,.0f} m³'.format)
        display_df['비율(%)'] = display_df['비율(%)'].map('{:.2f}%'.format)
        
        # 하이라이트 효과를 주기 위해 스트림릿 dataframe 스타일러 활용
        def highlight_total(val):
            if '총합계' in str(val):
                return 'background-color: #eaf2f8; font-weight: bold; color: #1f618d;'
            return ''
            
        styled_df = display_df.style.applymap(highlight_total, subset=['부문'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

    with col_chart:
        # 도넛 차트 (합계 행은 제외하고 부문별 데이터만 그림)
        fig = px.pie(
            summary,
            names='부문',
            values='사용량',
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

    # --- 3. 하단 레이아웃: 활성화 버튼 기반 부문별 Top 10 업체 ---
    st.markdown("### 🏢 2. 부문별 최다 사용 업체 순위 (Top 10)")
    
    # 활성화 수단 (라디오 버튼)
    selected_sector = st.radio(
        "조회할 납기 부문을 선택(활성화)하세요:",
        options=ordered_categories,
        horizontal=True
    )
    
    if selected_sector:
        # 선택된 부문 데이터 필터링 후 업체별 합산
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
