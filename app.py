import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
import time
import numpy as np
from datetime import datetime, timedelta

# --- 페이지 설정 ---
st.set_page_config(page_title="Tenbagger V48 (Sniper)", layout="wide")
st.title("🔫 텐배거 V48 (The Sniper)")
st.markdown("""
**"이미 오른 건 안 삽니다. 오르기 직전, 잔뜩 웅크린 놈을 잡습니다."**
1.  **스퀴즈(Squeeze):** 볼린저 밴드가 좁아진 종목 (에너지 응축).
2.  **지지(Support):** 20일선 위에 안착한 종목.
3.  **타이밍:** 남들이 지루해할 때 미리 들어가서 급등을 기다립니다.
""")

# --- 시장 신호등 ---
def check_market_status(market_type):
    try:
        symbol = "IXIC" if "나스닥" in market_type else "KS11"
        df = fdr.DataReader(symbol, start=(datetime.now() - timedelta(days=60)))
        curr_idx = df['Close'].iloc[-1]
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        if curr_idx > ma20:
            return "🟢", "상승장", "지수가 20일선 위에 있습니다. 스나이핑 적기!"
        else:
            return "🔴", "조정장", "지수가 약합니다. 손절가를 짧게 잡으세요."
    except:
        return "⚪", "데이터 없음", "확인 불가"

# --- 비상용 리스트 ---
KOSDAQ_EMERGENCY_LIST = [
    "080220", "393500", "394280", "042700", "007660", "403870", "058470", "277810",
    "348340", "108490", "058610", "094360", "054450", "102120", "098460", "036930",
    "067310", "377480", "304100", "108860", "402030", "064480", "315640", "253450",
    "086520", "247540", "001570", "101670", "073570", "114190", "131400", "078600",
    "121600", "365340", "234920", "348370", "025900", "005070", "272290", "283740",
    "196170", "028300", "067630", "141080", "298380", "323990", "016790", "000250",
    "214370", "140410", "039200", "358570", "310210", "087010", "389470", "237690",
    "352820", "122870", "035900", "112040", "101730", "063080", "095660", "263750",
    "207760", "263720", "397140", "419530", "047820", "067160", "033100", "103590",
    "298040", "001440", "010120", "034020", "052690", "032820", "083650"
]

# --- 테마 키워드 ---
THEME_KEYWORDS = {
    "🚀우주/방산": ["Space", "Satellite", "Rocket", "Defense", "Weapon", "Aerospace", "우주", "위성", "방산", "전쟁"],
    "🤖AI/로봇": ["AI", "Robot", "Artificial Intelligence", "NPU", "Deep Learning", "로봇", "인공지능", "휴머노이드"],
    "🧬바이오/헬스": ["Bio", "Drug", "Pharma", "Cancer", "Therapeutics", "Clinical", "Genomic", "바이오", "신약", "임상", "비만"],
    "🔋2차전지/에너지": ["Battery", "Lithium", "Cathode", "EV", "Energy", "Solar", "배터리", "리튬", "양극재", "전고체"],
    "💾반도체": ["Semiconductor", "Chip", "Foundry", "HBM", "Memory", "반도체", "팹리스", "유리기판"],
    "💎자원/광물": ["Mining", "Metals", "Gold", "Silver", "Mineral", "Rare Earth", "Polymetallic", "Antimony", "광물", "자원", "구리"],
    "☁️SW/플랫폼": ["Software", "SaaS", "Platform", "Cloud", "Cyber", "Data", "Security", "플랫폼", "보안", "웹툰"],
    "🏦금융/은행": ["Bank", "Financial", "Capital", "Insurance", "Invest", "Holding", "Bancorp", "Finance", "지주"],
}

# --- 설정 패널 ---
st.sidebar.header("🛠 설정 (V48 Sniper)")
market_type = st.sidebar.radio("시장", ["나스닥 (NASDAQ)", "코스닥/코스피 (KRX)"])

icon, status, desc = check_market_status(market_type)
st.info(f"🚦 **시장 신호: {icon} {status}**\n\n*{desc}*")

@st.cache_data
def load_data(m_type):
    try:
        if "나스닥" in m_type:
            return fdr.StockListing('NASDAQ'), "FULL"
        else:
            return fdr.StockListing('KRX'), "FULL"
    except Exception:
        data = [{'Code': code, 'Name': f"종목_{code}", 'Market': 'KOSDAQ'} for code in KOSDAQ_EMERGENCY_LIST]
        return pd.DataFrame(data), "EMERGENCY"

try:
    with st.spinner("종목 리스트 로딩..."):
        full_list, list_status = load_data(market_type)
        total_len = len(full_list)
        
    if list_status == "EMERGENCY":
        st.warning("⚠️ 비상용 리스트 모드")
        start_idx, end_idx = 0, total_len
    else:
        c1, c2 = st.sidebar.columns(2)
        start_idx = c1.number_input("시작 번호", 0, total_len-1, 0)
        end_idx = c2.number_input("끝 번호", 1, total_len, min(100, total_len))
    
    st.sidebar.markdown("---")
    vip_cap_limit = st.sidebar.number_input("시총 상한(억/M달러)", value=30000)
    
    # [NEW] 응축 강도 설정
    st.sidebar.markdown("---")
    squeeze_threshold = st.sidebar.slider("응축 강도 (낮을수록 폭발 임박)", 5, 20, 10)
    st.sidebar.caption("볼린저 밴드 폭(%)입니다. 10% 이하면 정말 꽉 눌린 상태입니다.")
    
    theme_options = list(THEME_KEYWORDS.keys()) + ["기타"]
    selected_themes = st.sidebar.multiselect("테마 필터", theme_options, default=[])

except Exception as e:
    st.error(f"오류: {e}")
    st.stop()

# --- 분석 로직 (볼린저 밴드 스퀴즈) ---
def analyze_stock_v48(ticker, name, country, squeeze_limit, cap_limit):
    try:
        stock = yf.Ticker(ticker)
        
        # 1. 차트 데이터 (최근 3개월, 볼린저밴드 계산용)
        df = stock.history(period="3mo")
        if len(df) < 20: return None
        if df['Volume'].iloc[-1] == 0: return None

        curr_price = df['Close'].iloc[-1]
        
        # === [핵심 알고리즘: 볼린저 밴드 계산] ===
        # 20일 이동평균
        df['MA20'] = df['Close'].rolling(window=20).mean()
        # 표준편차
        df['STD'] = df['Close'].rolling(window=20).std()
        # 상단/하단 밴드
        df['Upper'] = df['MA20'] + (df['STD'] * 2)
        df['Lower'] = df['MA20'] - (df['STD'] * 2)
        
        # [Bandwidth] 밴드폭 계산: (상단 - 하단) / 중심선 * 100
        # 이 값이 작을수록 에너지가 응축된 것임
        bandwidth = (df['Upper'].iloc[-1] - df['Lower'].iloc[-1]) / df['MA20'].iloc[-1] * 100
        
        # [조건 1] 응축 확인 (설정한 % 이하인가?)
        # 예: bandwidth가 8%라면, 주가가 위아래 8% 안에서만 놀고 있다는 뜻 (극도로 조용함)
        if bandwidth > squeeze_limit: return None
        
        # [조건 2] 추세 확인 (20일선 위에 있는가?)
        # 20일선 밑에서 횡보하는 건 '하락 횡보'일 수 있어서 위험. 위에서 버티는 놈이 찐임.
        if curr_price < df['MA20'].iloc[-1]: return None
        
        # [조건 3] 이미 터진 놈 제외
        # 오늘 이미 5% 이상 급등해버렸으면 '선취매'가 아님.
        prev_close = df['Close'].iloc[-2]
        change_pct = (curr_price - prev_close) / prev_close * 100
        if change_pct > 5.0: return None # 이미 출발한 차는 보냄
        
        # 2. 퀀트 필터 (시총)
        try:
            fast_info = stock.fast_info
            mkt_cap = fast_info['market_cap']
        except: mkt_cap = 0
            
        if country == "KR":
            mkt_cap_val = mkt_cap / 100000000 
            if not (300 <= mkt_cap_val <= cap_limit): return None
            mkt_str = f"{mkt_cap_val:.0f}억"
            code_pure = ticker.replace(".KQ", "").replace(".KS", "")
            news_url = f"https://m.stock.naver.com/item/main.nhn?code={code_pure}#/news/0"
        else:
            mkt_cap_val = mkt_cap / 1000000
            if not (30 <= mkt_cap_val <= cap_limit): return None
            mkt_str = f"${mkt_cap_val:.1f}M"
            news_url = f"https://finance.yahoo.com/quote/{ticker}/news"

        info = stock.info
        
        # 테마 분석
        theme_detected = "기타"
        summary = (info.get('longBusinessSummary', '') + " " + info.get('industry', '')).lower()
        for theme, keywords in THEME_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in summary:
                    theme_detected = theme
                    break
            if theme_detected != "기타": break

