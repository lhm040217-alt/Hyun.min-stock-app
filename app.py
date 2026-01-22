import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="Tenbagger Masterpiece V15", layout="wide")
st.title("👑 텐배거 마스터피스 V15 (Final)")
st.markdown("""
**"모든 조건을 만족하는 최종 버전"**
1. **범위 무제한:** 0번부터 3000번까지 원하는 만큼 전수조사
2. **텐배거 식별:** 시가총액이 작고 거래량이 터진 종목을 **[VIP]**로 붉게 표시
3. **재무 분석:** 매출성장률, 영업이익률까지 꼼꼼하게 표기
""")

# --- 사이드바: 설정 ---
st.sidebar.header("🛠 스캔 설정")

# 1. 시장 선택
market_type = st.sidebar.radio(
    "1. 분석할 시장",
    ["코스닥 (KOSDAQ) - 한국", "나스닥 (NASDAQ) - 미국", "S&P500 - 미국"]
)

# 2. 데이터 로딩
@st.cache_data
def load_stock_list(m_type):
    if "코스닥" in m_type:
        return fdr.StockListing('KOSDAQ')
    elif "나스닥" in m_type:
        return fdr.StockListing('NASDAQ')
    else:
        return fdr.StockListing('S&P500')

try:
    full_list = load_stock_list(market_type)
    total_count = len(full_list)
    st.sidebar.success(f"✅ 총 {total_count}개 종목 대기 중")
except Exception as e:
    st.error(f"목록 로딩 실패: {e}")
    st.stop()

# 3. 범위 설정 (숫자 입력)
st.sidebar.markdown("---")
st.sidebar.subheader("2. 검사 범위 입력")
st.sidebar.caption("시간이 걸려도 꼼꼼히 봅니다. (한 번에 1000개 입력 가능)")

col_start, col_end = st.sidebar.columns(2)
start_idx = col_start.number_input("시작 번호", min_value=0, max_value=total_count-1, value=0)
end_idx = col_end.number_input("끝 번호", min_value=1, max_value=total_count, value=min(200, total_count)) 

# 4. VIP 기준 설정
st.sidebar.markdown("---")
st.sidebar.subheader("3. 텐배거(VIP) 기준")
vip_cap_limit = st.sidebar.number_input("VIP 시총 상한선 (억/백만달러)", value=5000)
vip_vol_ratio = st.sidebar.slider("거래량 급증 기준 (배)", 2.0, 10.0, 3.0)

# --- 분석 핵심 로직 ---
def analyze_stock_master(ticker, name, country):
    try:
        # 1. Ticker 객체 생성 (재무 데이터용)
        stock = yf.Ticker(ticker)
        
        # 2. 가격/거래량 데이터 (최근 60일)
        df = stock.history(period="60d")
        
        if len(df) < 20: return None

        close = df['Close']
        volume = df['Volume']
        curr_price = close.iloc[-1]
        
        # 거래량 0 제외
        if volume.iloc[-1] == 0: return None

        # 3. 기술적 지표 계산
        vol_avg = volume.iloc[-20:-1].mean()
        if vol_avg == 0: return None
        vol_ratio = volume.iloc[-1] / vol_avg
        
        price_change = (curr_price - close.iloc[-5]) / close.iloc[-5] * 100
        
        # 4. 재무/정보 데이터 가져오기 (시간 소요됨 - 사용자가 원한 기능)
        # info가 가끔 에러나므로 예외처리 필수
        try:
            info = stock.info
            mkt_cap = info.get('marketCap', 0)
            rev_growth = info.get('revenueGrowth', 0) # 매출성장률
            profit_margin = info.get('profitMargins', 0) # 순이익률
        except:
            mkt_cap = 0
            rev_growth = 0
            profit_margin = 0

        # 5. 등급 판정
        grade = "FAIL"
        reasons = []

        # 단위 변환
        if country == "KR":
            mkt_cap_calc = mkt_cap / 100000000 # 억 원
        else:
            mkt_cap_calc = mkt_cap / 1000000 # 백만 달러

        # 조건 체크
        is_small_cap = (mkt_cap_calc > 0) and (mkt_cap_calc <= vip_cap_limit)
        is_vol_explode = vol_ratio >= vip_vol_ratio
        is_rising = price_change >= 5.0 # 최소한 5%는 올랐어야 함

        # 💎 VIP 조건: 시총 작음 + 거래량 폭발 + 상승세
        if is_small_cap and is_vol_explode and is_rising:
            grade = "VIP"
            reasons.append("★시총가벼움")
            reasons.append(f"거래량폭발({vol_ratio:.1f}배)")
        
        # 🔥 HOT 조건: 시총 상관없이 거래량 터짐 OR 급등
        elif (vol_ratio >= 2.0 and price_change >= 5.0) or (price_change >= 10.0):
            grade = "HOT"
            reasons.append("급등세")
            
        if grade == "FAIL": return None

        # 뉴스 링크
        if country == "KR":
            code_pure = ticker.replace(".KQ", "").replace(".KS", "")
            news_link = f"https://m.stock.naver.com/item/main.nhn?code={code_pure}#/news/0"
            mkt_str = f"{mkt_cap_calc:.0f}억"
        else:
            news_link = f"https://finance.yahoo.com/quote/{ticker}/news"
            mkt_str = f"${mkt_cap_calc:.1f}M"
            
        # 재무 정보 포맷팅
        growth_str = f"{rev_growth*100:.1f}%" if rev_growth else "-"
        margin_str = f"{profit_margin*100:.1f}%" if profit_margin else "-"

        return {
            "등급": grade,
            "이름": name,
            "코드": ticker,
            "현재가": f"{curr_price:,.0f}" if country=="KR" else f"${curr_price:.2f}",
            "등락률": f"{price_change:.1f}%",
            "거래량": f"{vol_ratio:.1f}배",
            "시총": mkt_str,
            "성장률": growth_str,
            "이익률": margin_str,
            "이유": ", ".join(reasons),
            "뉴스": news_link
        }

    except:
        return None

# --- 실행 버튼 ---
if st.button(f"🚀 {start_idx}~{end_idx}번 구간 정밀 스캔 (재무포함)"):
    
    target_slice = full_list.iloc[start_idx:end_idx]
    
    vip_list = []
    hot_list = []
    
    st.info(f"선택한 {len(target_slice)}개 종목의 재무제표와 차트를 정밀 분석합니다. 잠시만 기다려주세요.")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, row in enumerate(target_slice.iterrows()):
        idx, data = row
        
        # 국가별 코드 처리
        if "코스닥" in market_type:
            name = data['Name']
            ticker = data['Code']
            if not ticker.endswith(".KQ"): ticker = f"{ticker}.KQ"
            country = "KR"
        elif "나스닥" in market_type:
            name = data['Name']
            ticker = data['Symbol']
            country = "US"
        else:
            name = data['Name']
            ticker = data['Symbol']
            country = "US"

        status_text.write(f"🔍 [{i+1}/{len(target_slice)}] 분석중: {name}")
        
        res = analyze_stock_master(ticker, name, country)
        
        if res:
            if res['등급'] == "VIP":
                vip_list.append(res)
            else:
                hot_list.append(res)
        
        progress_bar.progress((i + 1) / len(target_slice))

    status_text.empty()
    progress_bar.empty()
    
    # --- 결과 출력 ---
    
    # 1. 💎 VIP 리포트 (텐배거 후보)
    st.markdown(f"## 💎 텐배거 VIP 후보 ({len(vip_list)}개)")
    st.caption("조건: 시가총액 이하 & 거래량 폭발 & 상승세")
    
    if vip_list:
        for item in vip_list:
            # 붉은색 박스로 강력하게 표시
            with st.error(f"💎 {item['이름']} ({item['코드']})"):
                c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 1])
                c1.write(f"💰 **{item['현재가']}** ({item['등락률']})")
                c1.write(f"⚖️ 시총: **{item['시총']}**")
                c2.write(f"🔥 거래량: **{item['거래량']}**")
                c2.write(f"💡 이유: {item['이유']}")
                c3.markdown("**재무지표**")
                c3.write(f"📈 성장률: {item['성장률']}")
                c3.write(f"💰 이익률: {item['이익률']}")
                c4.markdown(f"[⚡뉴스]({item['뉴스']})")
    else:
        st.info("이 구간에 완벽한 VIP 조건 종목은 없습니다.")

    st.markdown("---")

    # 2. 🔥 일반 급등주 리포트
    st.markdown(f"### 🔥 일반 급등 포착 ({len(hot_list)}개)")
    if hot_list:
        # 데이터프레임으로 깔끔하게 정리
        df_hot = pd.DataFrame(hot_list)
        st.dataframe(
            df_hot[["이름", "현재가", "등락률", "거래량", "시총", "성장률", "이익률", "이유"]],
            use_container_width=True
        )
    else:
        st.write("급등 신호가 없습니다.")
