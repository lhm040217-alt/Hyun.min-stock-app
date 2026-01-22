import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="Tenbagger Scanner Pro", layout="wide")

st.title("🦅 텐배거 스캐너 Pro (V3.0)")
st.markdown("""
**※ 주의:** 이 도구는 기술적 분석(거래량, 추세)을 기반으로 종목을 필터링합니다. 
투자의 책임은 본인에게 있으며, 반드시 **뉴스 버튼**을 눌러 호재/악재를 직접 확인하세요.
""")

# --- 사이드바 설정 ---
st.sidebar.header("🔍 분석 옵션")
scan_range = st.sidebar.slider("시장별 스캔 개수 (속도 조절)", 50, 300, 100)
top_n = st.sidebar.number_input("최종 선별 개수", min_value=5, max_value=50, value=20)

# --- 분석 함수 ---
def analyze_stock(code, name, country, start_date, end_date):
    score = 0
    reasons = []
    
    try:
        # 데이터 가져오기
        if country == "KR":
            df = fdr.DataReader(code, start_date, end_date)
            news_link = f"https://m.stock.naver.com/item/main.nhn?code={code}#/news/0"
        else:
            df = yf.download(code, start=start_date, progress=False)
            news_link = f"https://finance.yahoo.com/quote/{code}/news"
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

        if len(df) < 60: return None 

        # 데이터 정리
        close = df['Close']
        volume = df['Volume']
        
        curr_price = close.iloc[-1]
        prev_price = close.iloc[-2]
        
        # 1. 추세 점수 (정배열) - 30점
        ma20 = close.rolling(window=20).mean().iloc[-1]
        ma60 = close.rolling(window=60).mean().iloc[-1]
        
        if curr_price > ma20 and ma20 > ma60:
            score += 30
            reasons.append("상승추세")
        
        # 2. 거래량 점수 (수급 폭발) - 40점
        vol_avg = volume.iloc[-20:-1].mean()
        if vol_avg > 0 and volume.iloc[-1] > vol_avg * 2: 
            score += 40
            reasons.append("거래량폭발")
        elif vol_avg > 0 and volume.iloc[-1] > vol_avg * 1.5:
            score += 20
            reasons.append("거래량증가")
            
        # 3. 신고가 영역 - 30점
        month_high = close.iloc[-60:].max()
        if curr_price >= month_high * 0.95: 
            score += 30
            reasons.append("신고가임박")
            
        if score < 50: return None # 기준 미달 탈락

        change_rate = (curr_price - prev_price) / prev_price * 100

        return {
            "종목명": name,
            "코드": code,
            "현재가": f"{curr_price:,.0f}" if country=="KR" else f"${curr_price:.2f}",
            "등락률": f"{change_rate:+.2f}%",
            "점수": score,
            "특이사항": ", ".join(reasons),
            "뉴스": news_link
        }

    except Exception as e:
        return None

# --- 메인 실행 로직 ---
if st.button("🚀 시장 정밀 분석 시작"):
    start_time = time.time()
    st.info("데이터를 분석 중입니다... 잠시만 기다려주세요.")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=100)
    results = []
    
    progress_bar = st.progress(0)
    
    # 1. 한국 주식 (속도 개선됨: fdr 사용)
    st.write("🇰🇷 코스닥 유망주 스캔 중...")
    try:
        # KOSDAQ 전 종목 리스트를 한번에 가져옴 (빠름)
        df_kr = fdr.StockListing('KOSDAQ')
        # 시가총액 정보가 있다면 상위주 위주로, 없으면 앞부분만
        target_kr = df_kr.head(scan_range)
        
        for i, row in target_kr.iterrows():
            res = analyze_stock(row['Code'], row['Name'], "KR", start_date, end_date)
            if res: results.append(res)
            progress_bar.progress((i + 1) / (scan_range * 2))
    except Exception as e:
        st.error(f"한국 주식 목록 로딩 실패: {e}")

    # 2. 미국 주식
    st.write("🇺🇸 나스닥 기술주 스캔 중...")
    try:
        df_nasdaq = fdr.StockListing('NASDAQ')
        target_us = df_nasdaq.head(scan_range)
        
        for i, row in target_us.iterrows():
            res = analyze_stock(row['Symbol'], row['Name'], "US", start_date, end_date)
            if res: results.append(res)
            progress_bar.progress(0.5 + (i + 1) / (scan_range * 2))
    except Exception as e:
        st.error(f"미국 주식 목록 로딩 실패: {e}")

    progress_bar.empty()

    # --- 결과 출력 ---
    if results:
        df_res = pd.DataFrame(results)
        df_res = df_res.sort_values(by="점수", ascending=False).head(top_n)
        
        st.success(f"✅ 분석 완료! 상위 {len(df_res)}개 종목 포착")
        
        for idx, row in df_res.iterrows():
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.subheader(f"{row['종목명']}")
                    st.caption(f"코드: {row['코드']} | {row['특이사항']}")
                    st.write(f"가격: **{row['현재가']}** ({row['등락률']})")
                with col2:
                    st.markdown(f"### [🔗뉴스]({row['뉴스']})")
                    st.write(f"🏆 {row['점수']}점")
                st.divider()
    else:
        st.warning("조건에 맞는 종목이 없습니다. 스캔 범위를 늘려보세요.")

