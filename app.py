import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from pykrx import stock
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="Tenbagger Scanner Pro", layout="wide")

st.title("🦅 텐배거 스캐너 Pro")
st.markdown("""
**※ 주의:** 이 도구는 기술적 분석(거래량, 추세)을 기반으로 종목을 필터링합니다. 
투자의 책임은 본인에게 있으며, 반드시 **뉴스 버튼**을 눌러 호재/악재를 직접 확인하세요.
""")

# --- 사이드바 설정 ---
st.sidebar.header("🔍 분석 옵션")
scan_range = st.sidebar.slider("시장별 스캔 개수 (속도 조절)", 50, 200, 100) # 폰 성능 고려 기본 100개
top_n = st.sidebar.number_input("최종 선별 개수", min_value=5, max_value=50, value=20)

# --- 분석 함수 (점수제 도입) ---
def analyze_stock(ticker, country, start_date, end_date):
    score = 0
    reasons = []
    
    try:
        if country == "KR":
            df = fdr.DataReader(ticker, start_date, end_date)
            name = stock.get_market_ticker_name(ticker)
            # 네이버 금융 뉴스 링크
            news_link = f"https://m.stock.naver.com/item/main.nhn?code={ticker}#/news/0"
        else:
            df = yf.download(ticker, start=start_date, progress=False)
            name = ticker
            # 야후 파이낸스 뉴스 링크
            news_link = f"https://finance.yahoo.com/quote/{ticker}/news"
            
            # 멀티인덱스 컬럼 문제 해결 (yfinance 업데이트 대응)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

        if len(df) < 60: return None # 데이터 너무 적으면 탈락

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
            reasons.append("상승추세(정배열)")
        
        # 2. 거래량 점수 (수급 폭발) - 40점
        vol_avg = volume.iloc[-20:-1].mean()
        if volume.iloc[-1] > vol_avg * 2: # 평소보다 2배 이상 터짐
            score += 40
            reasons.append("거래량폭발")
        elif volume.iloc[-1] > vol_avg * 1.5:
            score += 20
            reasons.append("거래량증가")
            
        # 3. 변동성 점수 (눌림목 탈출 시도) - 30점
        # 최근 1달간 최고가 근처인지 확인
        month_high = close.iloc[-20:].max()
        if curr_price >= month_high * 0.95: # 신고가 근처
            score += 30
            reasons.append("신고가임박")
            
        # 4. 필터링 (점수가 50점 미만이면 과감히 버림)
        if score < 50:
            return None

        # 등락률 계산
        change_rate = (curr_price - prev_price) / prev_price * 100

        return {
            "종목명": name,
            "코드": ticker,
            "현재가": f"{curr_price:,.0f}" if country=="KR" else f"${curr_price:.2f}",
            "등락률": f"{change_rate:+.2f}%",
            "점수": score,
            "특이사항": ", ".join(reasons),
            "뉴스": news_link
        }

    except Exception as e:
        return None

# --- 메인 실행 로직 ---
if st.button("🚀 시장 정밀 분석 시작 (약 3분 소요)"):
    start_time = time.time()
    st.info("데이터를 긁어오는 중입니다. 화면을 끄지 말고 기다려주세요...")
    
    # 날짜 설정
    end_date = datetime.now()
    start_date = end_date - timedelta(days=100)
    
    results = []
    
    # 1. 한국 주식 스캔
    progress_bar = st.progress(0)
    st.write("🇰🇷 코스닥 시가총액 상위 종목 스캔 중...")
    
    # 코스닥 시총 상위 N개 가져오기
    kr_tickers = stock.get_market_ticker_list(market="KOSDAQ")
    # 우량주 위주로 먼저 보기 위해 시가총액순 정렬이 필요하나, 속도상 단순 리스트 슬라이싱 사용
    # (실전 팁: 앞쪽 번호가 꼭 우량주는 아니므로 랜덤 혹은 최근 거래량 상위 로직이 좋으나, 여기선 리스트 순서대로 함)
    target_kr = kr_tickers[:scan_range]
    
    for i, ticker in enumerate(target_kr):
        res = analyze_stock(ticker, "KR", start_date, end_date)
        if res: results.append(res)
        progress_bar.progress((i + 1) / (scan_range * 2)) # 진행률 표시

    # 2. 미국 주식 스캔
    st.write("🇺🇸 나스닥 기술주 스캔 중...")
    try:
        # 나스닥 심볼 리스트 가져오기
        df_nasdaq = fdr.StockListing('NASDAQ')
        target_us = df_nasdaq['Symbol'].head(scan_range).tolist()
        
        for i, ticker in enumerate(target_us):
            res = analyze_stock(ticker, "US", start_date, end_date)
            if res: results.append(res)
            progress_bar.progress(0.5 + (i + 1) / (scan_range * 2))
    except:
        st.error("미국 주식 목록을 가져오는데 실패했습니다.")

    progress_bar.empty()

    # --- 결과 출력 ---
    if results:
        # 점수 높은 순으로 정렬
        df_res = pd.DataFrame(results)
        df_res = df_res.sort_values(by="점수", ascending=False).head(top_n)
        
        st.success(f"✅ 분석 완료! 상위 {len(df_res)}개 종목을 발견했습니다.")
        
        # 카드 형태로 보여주기
        for idx, row in df_res.iterrows():
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.subheader(f"{row['종목명']} ({row['코드']})")
                    st.write(f"가격: **{row['현재가']}** ({row['등락률']})")
                    st.caption(f"포착 이유: {row['특이사항']}")
                with col2:
                    st.markdown(f"### [🔗뉴스확인]({row['뉴스']})") # 버튼처럼 동작
                    st.write(f"매력도: {row['점수']}점")
                st.divider()
    else:
        st.warning("조건에 맞는 종목을 찾지 못했습니다. 스캔 범위를 늘려보세요.")
    
    st.caption(f"소요 시간: {time.time() - start_time:.1f}초")

