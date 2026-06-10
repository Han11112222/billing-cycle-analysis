import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="빌링 납기별 분석", layout="wide")

st.title("📊 산업용 빌링 납기별 판매량 분석 대시보드")

@st.cache_data
def load_data():
    # 1. 첫 번째 파일 (가정용외 원장 데이터) - 인코딩은 환경에 따라 'cp949' 또는 'utf-8' 적용
    df_main = pd.read_csv("가정용외_202605.csv", encoding='utf-8')
    # Q열(상품명)에서 '산업용' 필터링 (컬럼명이 다를 경우 실제 데이터에 맞게 수정)
    df_ind_main = df_main[df_main['상품명'].str.contains('산업용', na=False)]
    
    # 2. 나머지 4개 파일 (각 시트별 데이터) 병합
    file_list = [
        "5월 관리납기 산업용 상품.xlsx - 5월 월말.csv",
        "5월 관리납기 산업용 상품.xlsx - 5월 산업용 월말2.csv",
        "5월 관리납기 산업용 상품.xlsx - 5월 산업용2회 기타2.csv",
        "5월 관리납기 산업용 상품.xlsx - 6월 산업용2회 기타1.csv"
    ]
    
    df_sub_list = []
    for file in file_list:
        temp_df = pd.read_csv(file, encoding='utf-8')
        df_sub_list.append(temp_df)
        
    df_sub = pd.concat(df_sub_list, ignore_index=True)
    
    return df_ind_main, df_sub

try:
    df_main, df_sub = load_data()
    
    st.markdown("### 📌 데이터 미리보기")
    col1, col2 = st.columns(2)
    with col1:
        st.write("1. 가정용외 데이터 (산업용 필터링)")
        st.dataframe(df_main[['고객명', '상품명', '사용량(m3)', '납기구분']].head())
    with col2:
        st.write("2. 산업용 개별 시트 병합 데이터")
        st.dataframe(df_sub[['고객명', '상  품', '사용량', '납기구분']].head())

    st.divider()

    # --- 분석 1: 납기구분별 판매량 비율 (전체 산업용 판매량 중) ---
    st.markdown("### 1️⃣ 납기구분별 판매량 비율")
    
    # sub 데이터의 '납기구분'과 '사용량' 기준 집계
    # (실제 컬럼명이 '사용량(m3)' 등일 경우 파일에 맞게 수정해주세요)
    billing_ratio = df_sub.groupby('납기구분')['사용량'].sum().reset_index()
    
    fig_pie = px.pie(
        billing_ratio, 
        names='납기구분', 
        values='사용량', 
        title="전체 산업용 판매량 내 납기구분 비율",
        hole=0.4 # 도넛 차트 형태
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    # --- 분석 2: 고객명별 사용량 (Top 20) ---
    st.markdown("### 2️⃣ 고객명별 산업용 가스 사용량 (Top 20)")
    
    # 고객별로 사용량 합산 후 내림차순 정렬
    customer_usage = df_sub.groupby('고객명')['사용량'].sum().reset_index()
    customer_usage = customer_usage.sort_values(by='사용량', ascending=False).head(20)
    
    fig_bar = px.bar(
        customer_usage, 
        x='고객명', 
        y='사용량', 
        text='사용량',
        title="주요 고객별 사용량 현황",
        color='사용량',
        color_continuous_scale=px.colors.sequential.Blues
    )
    fig_bar.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    st.plotly_chart(fig_bar, use_container_width=True)

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다. 파일 경로 및 인코딩을 확인해주세요. 오류: {e}")
