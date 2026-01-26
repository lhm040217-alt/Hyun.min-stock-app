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

# --- [수정됨] 엄격한 테마 키워드 ---
# 일반 명사(Energy, Defense) 삭제 -> 구체적 명사로 변경
THEME_KEYWORDS = {
    "🚀우주/방산": ["Spacecraft", "Satellite", "Rocket", "Missile", "Aerospace", "Defense System", "Weapon", "Warfare", "우주", "위성", "방산"],
    "🤖AI/로봇": ["Robotics", "Artificial Intelligence", "NPU", "Deep Learning", "Humanoid", "Autonomous", "로봇", "인공지능"],
    "🧬바이오/헬스": ["Biotech", "Pharma", "Therapeutics", "Clinical", "Genomic", "Oncology", "Drug", "Healthcare", "바이오", "신약", "임상"],
    "🔋2차전지/에너지": ["Lithium", "Cathode", "Anode", "Electric Vehicle", "EV Battery", "Solar Power", "Renewable Energy", "Wind Power", "Energy Storage", "배터리", "리튬", "양극재"],
    "💾반도체": ["Semiconductor", "Foundry", "HBM", "Memory Chip", "Fabless", "Wafer", "Processors", "반도체", "팹리스"],
    "💎자원/광물": ["Mining", "Precious Metal", "Mineral Resource", "Rare Earth", "Copper", "Gold Mine", "광물", "자원", "채굴"],
    "☁️SW/플랫폼": ["SaaS", "Cybersecurity", "Cloud Computing", "Data Center", "Software", "IT Services", "플랫폼", "보안", "클라우드"],
    "🏦금융/은행": ["Banking", "Insurance", "Investment Services", "Financial Services", "Bancorp", "Asset Management", "지주", "은행", "금융"],
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
    
    st.sidebar.markdown("---")
    squeeze_threshold = st.sidebar.slider("응축 강도 (낮을수록 폭발 임박)", 5, 20, 10)
    st.sidebar.caption("볼린저 밴드 폭(%)입니다. 10% 이하면 정말 꽉 눌린 상태입니다.")
    
    theme_options = list(THEME_KEYWORDS.keys()) + ["기타"]
    selected_themes = st.sidebar.multiselect("테마 필터", theme_options, default=[])

except Exception as e:
    st.error(f"오류: {e}")
    st.stop()

# --- 분석 로직 (수정됨: 엄격한 키워드 매칭) ---
def analyze_stock_v48(ticker, name, country, squeeze_limit, cap_limit):
    try:
        stock = yf.Ticker(ticker)
        
        # 1. 차트 데이터
        df = stock.history(period="3mo")
        if len(df) < 20: return None
        if df['Volume'].iloc[-1] == 0: return None

        curr_price = df['Close'].iloc[-1]
        
        # 볼린저 밴드 계산
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['STD'] = df['Close'].rolling(window=20).std()
        df['Upper'] = df['MA20'] + (df['STD'] * 2)
        df['Lower'] = df['MA20'] - (df['STD'] * 2)
        
        bandwidth = (df['Upper'].iloc[-1] - df['Lower'].iloc[-1]) / df['MA20'].iloc[-1] * 100
        
        if bandwidth > squeeze_limit: return None
        if curr_price < df['MA20'].iloc[-1]: return None
        
        prev_close = df['Close'].iloc[-2]
        change_pct = (curr_price - prev_close) / prev_close * 100
        if change_pct > 5.0: return None 
        
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
        
        # [수정됨] 테마 분석 로직 (섹터 필터링 추가)
        theme_detected = "기타"
        
        # 기업 정보 수집 (섹터 + 산업 + 설명)
        sec = info.get('sector', '').lower()
        ind = info.get('industry', '').lower()
        summ = info.get('longBusinessSummary', '').lower()
        
        full_text = f"{sec} {ind} {summ}"
        
        for theme, keywords in THEME_KEYWORDS.items():
            # [안전장치] 섹터가 맞지 않으면 특정 테마는 스킵
            # 1. 헬스케어/바이오 섹터인데 '방산' 테마 검사 중이면 건너뜀 (Immune Defense 오탐지 방지)
            if "healthcare" in sec and "방산" in theme:
                continue
            
            # 2. 소비재(음식/식당) 섹터인데 '에너지' 테마 검사 중이면 건너뜀 (Wendy's 오탐지 방지)
            if ("consumer" in sec or "restaurant" in ind) and "에너지" in theme:
                continue
                
            for kw in keywords:
                if kw.lower() in full_text:
                    theme_detected = theme
                    break
            if theme_detected != "기타": break
            
        final_grade = "💣폭발대기"
        vol_avg = df['Volume'].iloc[-20:-1].mean()
        vol_now = df['Volume'].iloc[-1]
        
        reasons = [f"밴드폭{bandwidth:.1f}%"]
        if vol_now < vol_avg * 0.7:
            final_grade = "🎯스나이퍼픽"
            reasons.append("🤫거래량급감")
            
        mini_chart_data = df['Close'].tail(30).tolist()
        target_price = df['Upper'].iloc[-1] * 1.1 
        stop_price = df['Lower'].iloc[-1] * 0.98 
        
        if country == "KR":
            target_str = f"{target_price:,.0f}"
            stop_str = f"{stop_price:,.0f}"
        else:
            target_str = f"${target_price:.2f}"
            stop_str = f"${stop_price:.2f}"

        return {
            "등급": final_grade,
            "테마": theme_detected,
            "이름": info.get('longName', name),
            "현재가": f"{curr_price:,.0f}" if country=="KR" else f"${curr_price:.2f}",
            "흐름": mini_chart_data,
            "특이사항": " ".join(reasons),
            "🎯목표가": target_str,
            "🛡️손절가": stop_str,
            "뉴스링크": news_url,
            "정렬용": bandwidth 
        }

    except:
        return None

# --- 실행 ---
if "scan_results_v48" not in st.session_state:
    st.session_state.scan_results_v48 = None

if st.button(f"🔫 V48 폭발 징후 포착 ({start_idx}~{end_idx})"):
    
    target_slice = full_list.iloc[start_idx:end_idx]
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    specific_theme_mode = len(selected_themes) > 0
    theme_label = ", ".join(selected_themes) if specific_theme_mode else "전체"
    
    st.info(f"조건: 밴드폭 {squeeze_threshold}% 이하 + 20일선 지지 | 테마: {theme_label}")
    
    for i, row in enumerate(target_slice.iterrows()):
        idx, data = row
        if "나스닥" in market_type:
            ticker = data['Symbol']
            name = data['Name']
            country = "US"
        else:
            ticker = data['Code']
            market = data.get('Market', 'KOSDAQ')
            if market == 'KOSPI': ticker += ".KS"
            elif market == 'KOSDAQ': ticker += ".KQ"
            else: 
                if ticker.isdigit(): ticker += ".KQ"
            name = data['Name']
            country = "KR"
            
        status_text.text(f"🔫 조준 중... [{i+1}/{len(target_slice)}]: {name}")
        
        time.sleep(0.01)
        
        res = analyze_stock_v48(ticker, name, country, squeeze_threshold, vip_cap_limit)
        
        if res:
            if specific_theme_mode:
                if res['테마'] in selected_themes:
                    results.append(res)
            else:
                results.append(res)
        
        progress_bar.progress((i + 1) / len(target_slice))

    status_text.empty()
    progress_bar.empty()
    
    if results:
        df = pd.DataFrame(results)
        df = df.sort_values("정렬용")
        
        st.session_state.scan_results_v48 = df
        st.success(f"🔫 포착 완료! {len(results)}개의 응축 종목을 찾았습니다.")
    else:
        st.warning("조건에 맞는 종목이 없습니다. (응축 강도를 조금 높여보세요.)")

if st.session_state.scan_results_v48 is not None:
    df_show = st.session_state.scan_results_v48
    
    st.dataframe(
        df_show[["등급", "테마", "이름", "현재가", "흐름", "특이사항", "🎯목표가", "🛡️손절가", "뉴스링크"]],
        column_config={
            "흐름": st.column_config.LineChartColumn("최근 흐름"),
            "뉴스링크": st.column_config.LinkColumn("팩트체크", display_text="👉뉴스확인")
        },
        use_container_width=True,
        height=800
    )
