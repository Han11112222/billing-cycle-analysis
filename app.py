import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="빌링 납기별 분석", layout="wide")
st.title("📊 산업용 빌링 납기별 판매량 분석 대시보드")

@st.cache_data
def load_data():
    # 한글 깨짐 및 인코딩 에러 방지를 위한 후보군
    encodings = ['cp949', 'utf-8', 'euc-kr', 'utf-8-sig']
    
    # 1. 메인 원장 데이터 로드 (인코딩 자동 시도)
    main_file = "가정용외_202605.csv"
    df_main = None
    
    if not os.path.exists(main_file):
        st.error(f"❌ '{main_file}' 파일을 찾을 수 없습니다. 깃허브에 파일이 올바르게 업로드되었는지 확인해주세요.")
        return None, None

    for enc in encodings:
        try:
            df_main = pd.read_csv(main_file, encoding=enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
            
    if df_main is None:
        st.error(f"❌ '{main_file}' 파일의 인코딩을 읽을 수 없습니다. 파일 서식을 확인해주세요.")
        return None, None
        
    # Q열(상품명)에서 '산업용' 필터링
    df_ind_main = df_main[df_main['상품명'].str.contains('산업용', na=False)]
    
    # 2. 변경된 파일명 반영 (점 두 개 '..xlsx' 반영)
    file_list = [
        "5월 관리납기 산업용 상품..xlsx - 5월 월말.csv",
        "5월 관리납기 산업용 상품..xlsx - 5월 산업용 월말2.csv",
        "5월 관리납기 산업용 상품..xlsx - 5월 산업용2회 기타2.csv",
        "5월 관리납기 산업용 상품..xlsx - 6월 산업용2회 기타1.csv"
    ]
    
    df_sub_list = []
    for file in file_list:
        if not os.path.exists(file):
            st.error(f"❌ '{file}' 파일을 찾을 수 없습니다. 깃허브 레포지토리의 파일명(공백, 점 개수 등)을 다시 확인해주세요.")
            return None, None
            
        temp_df = None
        for enc in encodings:
            try:
                temp_df = pd.read_csv(file, encoding=enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue
                
        if temp_df is not None:
            df_sub_list.append(temp_df)
        else:
            st.error(f"❌ '{file}' 파일의 인코딩을 읽을 수 없습니다.")
            return None, None
        
    df_sub = pd.concat(df_sub_list, ignore_index=True)
    return df_ind_main, df_sub

# 데이터 불러오기 및 실행
df_main, df_sub = load_data()

if df_main is not None and df_sub is not None:
    st.success("✅ 모든 데이터가 성공적으로 로드되었습니다!")
    
    st.markdown("### 📌 데이터 요약 정보")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="전체 원장 내 산업용 데이터 수", value=f"{len(df_main):,} 건")
        st.dataframe(df_main[['고객명', '상품명', '사용량(m3)', '납기구분']].head())
    with col2:
        st.metric(label="분할 시트 병합 데이터 수", value=f"{len(df_sub):,} 건")
        st.dataframe(df_sub[['고객명', '상  품', '사용량', '납기구분']].head())

    st.divider()

    # --- 분석 1: 납기구분별 판매량 비율 ---
    st.markdown("### 1️⃣ 납기구분별 판매량 비율")
    billing_ratio = df_sub.groupby('납기구분')['사용량'].sum().reset_index()
    
    fig_pie = px.pie(
        billing_ratio, 
        names='납기구분', 
        values='사용량', 
        title="전체 산업용 판매량 내 납기구분 비율",
        hole=0.4
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    # --- 분석 2: 고객명별 사용량 (Top 20) ---
    st.markdown("### 2️⃣ 고객명별 산업용 가스 사용량 (Top 20)")
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
