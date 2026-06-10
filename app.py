import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="빌링 납기별 분석", layout="wide")
st.title("📊 산업용 빌링 납기별 판매량 분석 대시보드")

@st.cache_data
def load_data():
    # 1. 가정용외 원장 데이터 로드 (CSV)
    main_file = "가정용외_202605.csv"
    df_main = None
    
    if os.path.exists(main_file):
        for enc in ['cp949', 'utf-8', 'euc-kr', 'utf-8-sig']:
            try:
                df_main = pd.read_csv(main_file, encoding=enc)
                break
            except:
                continue
    else:
        st.error(f"❌ '{main_file}' 파일을 찾을 수 없습니다.")
        return None, None
        
    if df_main is not None:
        # Q열(상품명)에서 '산업용' 필터링
        df_ind_main = df_main[df_main['상품명'].str.contains('산업용', na=False)]
    else:
        st.error("❌ 메인 CSV 파일의 인코딩을 읽을 수 없습니다.")
        return None, None

    # 2. 산업용 상품 엑셀 파일 로드 (.xlsx)
    excel_file = "5월 관리납기 산업용 상품..xlsx"
    df_sub = None
    
    if os.path.exists(excel_file):
        try:
            # sheet_name=None 으로 설정하면 엑셀 내의 모든 시트를 한 번에 불러옵니다.
            excel_dict = pd.read_excel(excel_file, sheet_name=None, engine='openpyxl')
            
            # 불러온 모든 시트의 데이터를 하나의 데이터프레임으로 세로 병합
            df_sub = pd.concat(excel_dict.values(), ignore_index=True)
            
        except Exception as e:
            st.error(f"❌ 엑셀 파일을 읽는 중 오류가 발생했습니다: {e}")
            return None, None
    else:
        st.error(f"❌ '{excel_file}' 파일을 찾을 수 없습니다. 깃허브의 파일명과 정확히 일치하는지 확인해주세요.")
        return None, None
        
    return df_ind_main, df_sub

# 데이터 불러오기 및 대시보드 실행
df_main, df_sub = load_data()

if df_main is not None and df_sub is not None:
    st.success("✅ 엑셀 파일의 모든 시트와 메인 데이터가 성공적으로 로드되었습니다!")
    
    st.markdown("### 📌 데이터 요약 정보")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="전체 원장 내 산업용 데이터 수", value=f"{len(df_main):,} 건")
        st.dataframe(df_main[['고객명', '상품명', '사용량(m3)', '납기구분']].head())
    with col2:
        st.metric(label="엑셀 전 시트 병합 데이터 수", value=f"{len(df_sub):,} 건")
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
