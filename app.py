import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="Tenbagger Classifier V13", layout="wide")
st.title("💎 텐배거 분류기 V13 (VIP 식별 시스템)")
st.markdown("""
**"전수조사 + 등급 분류"**
전체 종목을 스캔하되, 피터 린치의 **'텐배거 조건(시총+거래량)'**을 만족하는 종목은 
**[VIP]**로 따로 분류하여 붉은색으로 강조합니다.
""")

# --- 사이드바: 설정 ---
st.sidebar.header("🛠 스캔 및 분류 설정")
market = st.sidebar.radio("분석할 시장", ["코스닥 (KOSDAQ)", "나스닥 (NASDAQ)"])

# 텐배거 기준값 설정
st.sidebar.subheader("💎 텐배거(VIP) 기준")
vip_cap_limit = st.sidebar.slider("시가총액 상한선 (VIP용)", 1000, 10000, 5000) 
st.sidebar.caption("단위: 억 원 (한국) / 백만 달러 (미국)")
st.sidebar.caption("※ 이 시총보다 작아야 10배 상승이 쉽습니다.")

# 데이터 로딩
@st.cache_data
def get_stock_list(market_name):
    if market_name == "코스닥 (KOSDAQ)":
        return fdr.StockListing('KOSDAQ')
    else:
        return fdr.StockListing('NASDAQ')

try:
    full_list = get_stock_list(market)
    st.sidebar.success(f"총 {len(full_list)}개 종목 로딩됨")
    
    # 범위 슬라이더 (전수조사용)
    start_idx, end_idx = st.sidebar.select_slider(
        "검사 구간 선택 (한 번에 300개 권장)",
        options=range(0, len(full_list) + 1, 50),
        value=(0, 200)
    )
    st.sidebar.info(f"현재 {start_idx}~{end_idx}번 구간 분석 중")
    
except:
    st.error("데이터 로딩 실패")
    st.stop()

# --- 분석 로직 ---
def analyze_stock_v13(ticker, name, country, market_cap):
    try:
        # 1. 데이터 다운로드 (최근 3개월)
        df = yf.download(ticker, period="3mo", progress=False)
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if len(df) < 20: return None

        close = df['Close']
        volume = df['Volume']
        curr_price = close.iloc[-1]
        
        # 2. 기초 필터 (거래량 0이거나 너무 비싼 주식 제외)
        if volume.iloc[-1] == 0: return None
        if country == "US" and curr_price > 300: return None # 미국 대형주 제외

        # 3. 핵심 지표 계산
        # 거래량 비율
        vol_avg = volume.iloc[-20:-1].mean()
        vol_ratio = volume.iloc[-1] / vol_avg if vol_avg > 0 else 0
        
        # 가격 변동 (1주)
        price_change = (curr_price - close.iloc[-5]) / close.iloc[-5] * 100
        
        # 신고가 여부
        is_high = curr_price >= close.max() * 0.95

        # 4. [등급 분류] 여기가 핵심입니다!
        stock_grade = "NORMAL" # 기본은 일반
        reasons = []

        # VIP 조건 (텐배거 후보): 시총 작음 + 거래량 폭발 + 상승세
        is_small_cap = False
        if market_cap > 0:
            if country == "KR" and market_cap <= (vip_cap_limit * 100000000): is_small_cap = True
            elif country == "US" and market_cap <= (vip_cap_limit * 1000000): is_small_cap = True
        
        # 판정 로직
        if is_small_cap and vol_ratio >= 3.0 and price_change >= 5.0:
            stock_grade = "VIP" # 💎 텐배거 후보
            reasons.append("★시총작음/거래량폭발")
        elif vol_ratio >= 2.0 and price_change >= 5.0:
            stock_grade = "HOT" # 🔥 일반 급등
            reasons.append("수급유입")
        elif price_change >= 10.0:
            stock_grade = "HOT"
            reasons.append("급등주")
            
        # 아무 등급도 아니면 탈락
        if stock_grade == "NORMAL": return None

        # 뉴스 링크
        if country == "KR":
            news_link = f"https://m.stock.naver.com/item/main.nhn?code={ticker}#/news/0"
            mkt_cap_str = f"{market_cap/100000000:.0f}억"
        else:
            news_link = f"https://finance.yahoo.com/quote/{ticker}/news"
            mkt_cap_str = f"${market_cap/1000000:.1f}M"

        return {
            "등급": stock_grade,
            "이름": name,
            "코드": ticker,
            "현재가": f"{curr_price:,.0f}" if country=="KR" else f"${curr_price:.2f}",
            "등락률": f"{price_change:.1f}%",
            "거래량": f"{vol_ratio:.1f}배",
            "시총": mkt_cap_str,
            "이유": ", ".join(reasons),
            "뉴스": news_link
        }

    except:
        return None

# --- 실행 버튼 ---
if st.button(f"🚀 {start_idx}~{end_idx} 구간 정밀 분류 시작"):
    
    target_list = full_list.iloc[start_idx:end_idx]
    
    vip_results = [] # 텐배거 후보
    hot_results = [] # 일반 급등주
    
    bar = st.progress(0)
    status = st.empty()
    
    for i, row in enumerate(target_list.iterrows()):
        _, data = row
        
        if market == "코스닥 (KOSDAQ)":
            name = data['Name']
            ticker = data['Code']
            # FDR 데이터프레임에 Marcap(시가총액)이 있는지 확인
            mkt_cap = data['Marcap'] if 'Marcap' in data else 0
            
            if not ticker.endswith(".KQ"): ticker = f"{ticker}.KQ"
            country = "KR"
        else:
            name = data['Name']
            ticker = data['Symbol']
            # 나스닥은 FDR 리스트에 시총 정보가 없을 수 있음 (0으로 처리 후 yf에서 받으면 느리니 일단 패스)
            mkt_cap = 0 
            country = "US"
            
        status.write(f"판독 중: {name}")
        
        res = analyze_stock_v13(ticker, name, country, mkt_cap)
        
        if res:
            if res['등급'] == "VIP":
                vip_results.append(res)
            else:
                hot_results.append(res)
                
        bar.progress((i + 1) / len(target_list))
        
    bar.empty()
    status.empty()

    # --- 결과 출력 (분리해서 보여줌) ---
    
    # 1. 💎 VIP 섹션 (가장 중요)
    st.markdown("## 💎 텐배거 VIP 후보 (집중 관찰)")
    st.info("조건: 시가총액이 작고(가볍고), 거래량이 3배 이상 터진 '폭등 전조' 종목")
    
    if vip_results:
        for row in vip_results:
            # 붉은색 박스로 강조 (error 메시지 활용)
            with st.error(f"💎 {row['이름']} ({row['코드']})"):
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.write(f"💰 가격: **{row['현재가']}** ({row['등락률']})")
                c1.write(f"📊 시총: **{row['시총']}** (가벼움!)")
                c2.write(f"🔥 거래량: 평소의 **{row['거래량']}**")
                c2.write(f"💡 이유: {row['이유']}")
                c3.markdown(f"[⚡뉴스확인]({row['뉴스']})")
    else:
        st.write("이 구간에는 '완벽한 텐배거 조건'을 갖춘 종목이 없습니다.")

    st.divider()

    # 2. 🔥 일반 급등주 섹션
    st.markdown("### 🔥 급등 신호 발생 (일반)")
    st.caption("시총이 조금 크거나, 조건이 약간 부족하지만 상승세인 종목들")
    
    if hot_results:
        df_hot = pd.DataFrame(hot_results)
        # 테이블로 깔끔하게 보여주기
        st.dataframe(
            df_hot[["이름", "현재가", "등락률", "거래량", "시총", "이유"]],
            use_container_width=True
        )
    else:
        st.write("급등 신호 종목이 없습니다.")

