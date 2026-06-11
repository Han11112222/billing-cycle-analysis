import streamlit as st
import pandas as pd
import plotly.express as px
import os
import base64

st.set_page_config(page_title="빌링 납기별 분석", layout="wide")

logo_jpg = "logo.jpg"
logo_png = "logo.png"

if os.path.exists(logo_jpg):
    st.sidebar.image(logo_jpg, use_container_width=True)
elif os.path.exists(logo_png):
    st.sidebar.image(logo_png, use_container_width=True)

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
        elif '일반납기' in sheet_name:
            category_name = '일반납기'
            
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
    
    ordered_categories = ['산업용 1회', '산업용월말(2회)', '산업용기타(2회)', '산업용3회', '업무용 납기', '일반납기']
    
    for cat in ordered_categories:
        if cat not in summary['부문'].values:
            empty_row = pd.DataFrame({'부문': [cat], '부문별 판매량(m3)': [0.0], '업체수(개소)': [0]})
            summary = pd.concat([summary, empty_row], ignore_index=True)
            
    summary['부문'] = pd.Categorical(summary['부문'], categories=ordered_categories, ordered=True)
    summary = summary.sort_values('부문').reset_index(drop=True)
    
    visible_total = summary['부문별 판매량(m3)'].sum()
    total_companies = summary['업체수(개소)'].sum()
    summary['전체대비 비율(%)'] = (summary['부문별 판매량(m3)'] / visible_total) * 100

    # 📌 [수정] 전역을 완벽한 중간 정렬(Center)로 세팅
    center_header_styles = [
        {'selector': 'th', 'props': [('background-color', '#1B4F72'), ('color', 'white'), ('font-weight', 'bold'), ('font-size', '14px'), ('text-align', 'center')]},
        {'selector': 'td', 'props': [('text-align', 'center')]}
    ]

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
        formatted_df['전체대비 비율(%)'] = formatted_df['전체대비 비율(%)'].map('{:.1f}%'.format)
        
        def style_table(row):
            if '총합계' in str(row['부문']):
                return ['background-color: #D6EAF8; font-weight: bold; color: #1B4F72;'] * len(row)
            # ✅ [수정] 산업용기타(2회) 연한 회색 하이라이트 적용
            elif '산업용기타(2회)' in str(row['부문']):
                return ['background-color: #F2F3F4;'] * len(row)
            return [''] * len(row)
            
        # ✅ [수정] 중앙 정렬 반영
        styled_table = formatted_df.style.apply(style_table, axis=1)\
                                         .set_table_styles(center_header_styles)\
                                         .set_properties(**{'text-align': 'center'})
                                     
        st.dataframe(styled_table, use_container_width=True, hide_index=True)

    with col_chart:
        st.markdown("##### 📊 부문별 판매량 비율")
        
        fig = px.pie(
            summary,
            names='부문',
            values='부문별 판매량(m3)',
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Teal_r
        )
        
        text_positions = ['outside' if cat in ['산업용3회', '업무용 납기', '일반납기'] else 'inside' for cat in summary['부문']]
        
        fig.update_traces(
            textposition=text_positions,
            textinfo='label+percent',
            texttemplate='<b>%{label}</b><br>%{percent:.1%}',
            textfont_size=14,
            insidetextorientation='horizontal'
        )
        
        fig.update_layout(
            showlegend=False, 
            margin=dict(t=10, b=10, l=120, r=40)
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ----------------------------------------------------
    # 2️⃣ 중앙 레이아웃: 활성화 버튼 기반 부문별 업체 조회
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
                display_list['비율(%)'] = (display_list['사용량'] / total_sector_vol) * 100
                
                display_list['사용량'] = display_list['사용량'].map('{:,.0f} m³'.format)
                display_list['비율(%)'] = display_list['비율(%)'].map('{:.1f}%'.format)
                
                def highlight_bottom_total(row):
                    if '총계' in str(row['고객명']):
                        return ['background-color: #D6EAF8; font-weight: bold; color: #1B4F72;'] * len(row)
                    return [''] * len(row)
                    
                # ✅ [수정] 중앙 정렬 반영
                styled_list = display_list.style.apply(highlight_bottom_total, axis=1)\
                                                .set_table_styles(center_header_styles)\
                                                .set_properties(**{'text-align': 'center'})
                
                # ✅ [수정] 고객명을 'large'로 둬서 순위의 'small' 너비가 확실히 작동하게 끔 유도
                st.dataframe(
                    styled_list, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "순위": st.column_config.Column(width="small"),
                        "고객명": st.column_config.Column(width="large")
                    }
                )

    st.divider()

    # ----------------------------------------------------
    # 3️⃣ 하단 레이아웃: 전체 산업용 Top 30 기업 표
    # ----------------------------------------------------
    st.markdown("### 🏆 3. 전체 산업용 고객 판매량 Top 30")
    
    top30_df = df_master.groupby(['고객명', '부문'], as_index=False)['사용량'].sum()
    top30_df = top30_df.sort_values(by='사용량', ascending=False).head(30).reset_index(drop=True)
    
    top30_df.insert(0, '순위', range(1, len(top30_df) + 1))
    top30_df.rename(columns={'부문': '납기구분', '사용량': '사용'}, inplace=True)
    
    top30_df['전체대비 비율(%)'] = (top30_df['사용'] / visible_total) * 100
    top30_df['사용'] = top30_df['사용'].map('{:,.0f} m³'.format)
    top30_df['전체대비 비율(%)'] = top30_df['전체대비 비율(%)'].map('{:.1f}%'.format)
    
    display_top30 = top30_df[['순위', '고객명', '사용', '납기구분', '전체대비 비율(%)']]
    
    # ✅ [수정] 중앙 정렬 반영
    styled_top30 = display_top30.style.set_table_styles(center_header_styles)\
                                      .set_properties(**{'text-align': 'center'})
    
    # ✅ [수정] 고객명을 'large'로 둬서 순위의 'small' 너비가 확실히 작동하게 끔 유도
    st.dataframe(
        styled_top30, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "순위": st.column_config.Column(width="small"),
            "고객명": st.column_config.Column(width="large")
        }
    )

    st.divider()

    # ----------------------------------------------------
    # 4️⃣ 최하단 레이아웃: 청구 사이클 비교 뷰어
    # ----------------------------------------------------
    st.markdown("### 📅 4. 부문별 청구 사이클 비교 (사용일 기준)")
    
    img_jpg = "청구사이클비교.jpg"
    img_png = "청구사이클비교.png"
    pdf_file = "청구사이클비교.pdf"
    
    if os.path.exists(img_jpg):
        st.image(img_jpg, use_container_width=True)
    elif os.path.exists(img_png):
        st.image(img_png, use_container_width=True)
    elif os.path.exists(pdf_file):
        with open(pdf_file, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        st.info("💡 '청구사이클비교' 이미지(.jpg, .png) 또는 PDF 파일을 레포지토리에 올려주세요.")
