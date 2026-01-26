import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
import time
import numpy as np
from datetime import datetime, timedelta

# --- 페이지 설정 ---
st.set_page_config(page_title="Tenbagger V45 (Golden Bottom)", layout="wide")
st.title("🏆 텐배거 V45 (Golden Bottom)")
st.markdown("""
**"바닥에서 거래량 터진 '양봉'만 잡습니다."**
1.  **양봉 매집:** 거래량 500% 폭발 + 주가 상승/보합 (폭락주 제외)
2.  **추세 전환:** 20일선 돌파 확인 (지하 뚫는 종목 제외)
3.  **기본기:** 매출 성장이 멈춘(마이너스) 기업 제외
""")

# --- 시장 신호등 ---
def check_market_status(market_type):
    try:
        symbol = "IXIC" if "나스닥" in market_type else "KS11"
        df = fdr.DataReader(symbol, start=(datetime.now() - timedelta(days=60)))
        curr_idx = df['Close'].iloc[-1]
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        if curr_idx > ma20:
            return "🟢", "상승장", f"지수가 20일선 위에 있습니다. ({symbol})"
        else:
            return "🔴", "조정장", f"보수적으로 접근하세요. ({symbol})"
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
st.sidebar.header("🛠 설정 (V45 Final Fix)")
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
    with st.spinner("데이터 로딩 중..."):
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
    st.sidebar.info("💡 **V45 보완된 조건**")
    st.sidebar.write("1. **폭락주 제외:** 거래량 터진 하락(투매) 방지")
    st.sidebar.write("2. **추세:** 20일선 위에 있는 종목만")
    st.sidebar.write("3. **매출:** 성장률 마이너스 기업 제외")
    
    st.sidebar.markdown("---")
    theme_options = list(THEME_KEYWORDS.keys()) + ["기타"]
    selected_themes = st.sidebar.multiselect("테마 선택", theme_options, default=[])

except Exception as e:
    st.error(f"오류: {e}")
    st.stop()

# --- 분석 로직 ---
def analyze_stock_v45(ticker, name, country, specific_theme_mode):
    try:
        stock = yf.Ticker(ticker)
        
        # 1. 기술적 필터
        df = stock.history(period="1y")
        if len(df) < 60: return None
        if df['Volume'].iloc[-1] == 0: return None

        curr_price = df['Close'].iloc[-1]
        low_52w = df['Close'].min()
        
        # [조건 1] 위치 제한: 바닥 대비 3배(300%) 미만
        if curr_price > low_52w * 3.0: return None 
        
        # [조건 2 - 핵심 보완] 폭락주 필터
        # 거래량이 터졌는데 가격이 -3% 이상 빠졌으면 '투매'로 간주하고 버림
        price_change_pct = (curr_price - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100
        if price_change_pct < -3.0: return None 
        
        # [조건 3 - 핵심 보완] 추세 확인 (20일선)
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        if curr_price < ma20: return None # 20일선 아래(역배열)는 아직 위험함
        
        # [조건 4] 거래량 폭발 (500% 이상)
        vol_avg = df['Volume'].iloc[-20:-1].mean()
        vol_now = df['Volume'].iloc[-1]
        if (vol_now * curr_price) < 100000000: return None # 잡주 제외
        
        ratio_vol = vol_now / vol_avg if vol_avg > 0 else 0
        if ratio_vol < 5.0: return None # 5배 미만이면 탈락
        
        # 2. 퀀트 필터
        try:
            fast_info = stock.fast_info
            mkt_cap = fast_info['market_cap']
        except: return None
            
        if country == "KR":
            mkt_cap_val = mkt_cap / 100000000 
            if not (300 <= mkt_cap_val <= 20000): return None
            mkt_str = f"{mkt_cap_val:.0f}억"
            code_pure = ticker.replace(".KQ", "").replace(".KS", "")
            news_url = f"https://m.stock.naver.com/item/main.nhn?code={code_pure}#/news/0"
        else:
            mkt_cap_val = mkt_cap / 1000000
            if not (30 <= mkt_cap_val <= 2000): return None
            mkt_str = f"${mkt_cap_val:.1f}M"
            news_url = f"https://finance.yahoo.com/quote/{ticker}/news"

        info = stock.info
        
        # [조건 5 - 최소 자격] 매출 역성장 기업 제외
        rev_growth = info.get('revenueGrowth', 0)
        if rev_growth is None: rev_growth = 0
        if rev_growth < 0: return None # 회사가 쪼그라드는 중이면 제외
        
        # 테마 분석
        theme_detected = "기타"
        summary = (info.get('longBusinessSummary', '') + " " + info.get('industry', '')).lower()
        for theme, keywords in THEME_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in summary:
                    theme_detected = theme
                    break
            if theme_detected != "기타": break
            
        # 등급 부여
        profit_margin = info.get('profitMargins', 0)
        
        final_grade = "💎A급(세력포착)"
        bonus_tags = [f"⚡거래량{ratio_vol:.1f}배"]
        
        if ratio_vol >= 10.0:
            final_grade = "👑S급(매집폭발)"
            bonus_tags.append("🔥초강력수급")
            
        if profit_margin > 0:
            bonus_tags.append("💰흑자")
        if rev_growth > 0.20:
            bonus_tags.append("🚀고성장")
            
        mini_chart_data = df['Close'].tail(30).tolist()
        target_price = curr_price * 1.20 
        stop_price = curr_price * 0.95   
        
        if country == "KR":
            target_str = f"{target_price:,.0f}"
            stop_str = f"{stop_price:,.0f}"
        else:
            target_str = f"${target_price:.2f}"
            stop_str = f"${stop_price:.2f}"

        pos_from_low = (curr_price - low_52w) / low_52w * 100

        return {
            "등급": final_grade,
            "테마": theme_detected,
            "이름": info.get('longName', name),
            "현재가": f"{curr_price:,.0f}" if country=="KR" else f"${curr_price:.2f}",
            "흐름": mini_chart_data,
            "위치": f"바닥+{pos_from_low:.1f}%",
            "🎯목표가": target_str,
            "🛡️손절가": stop_str,
            "특이사항": " ".join(bonus_tags),
            "뉴스링크": news_url,
            "등락률_수치": pos_from_low
        }

    except:
        return None

# --- 실행 및 결과 저장 ---
if "scan_results_v45" not in st.session_state:
    st.session_state.scan_results_v45 = None

if st.button(f"🏆 V45 골든 바텀 스캔 ({start_idx}~{end_idx})"):
    
    target_slice = full_list.iloc[start_idx:end_idx]
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    specific_theme_mode = len(selected_themes) > 0
    theme_label = ", ".join(selected_themes) if specific_theme_mode else "전체"
    
    st.info(f"조건: 2조↓ + 20일선 위 + 거래량 500%↑ (투매 제외) / 테마: {theme_label}")
    
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
            
        status_text.text(f"🔍 스캔중 [{i+1}/{len(target_slice)}]: {name}")
        
        time.sleep(0.05)
        
        res = analyze_stock_v45(ticker, name, country, specific_theme_mode)
        
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
        
        grade_order = {"👑S급(매집폭발)": 0, "💎A급(세력포착)": 1}
        df["우선순위"] = df["등급"].map(grade_order).fillna(2)
        df = df.sort_values("우선순위").drop(columns=["우선순위"])
        
        st.session_state.scan_results_v45 = df
        st.success(f"🏆 발굴 완료! {len(results)}개의 '진짜' 바닥주를 찾았습니다.")
    else:
        st.warning("조건에 맞는 종목이 없습니다. (폭락주 필터링됨)")

if st.session_state.scan_results_v45 is not None:
    df_show = st.session_state.scan_results_v45
    
    csv = df_show.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="💾 결과 엑셀로 저장",
        data=csv,
        file_name='tenbagger_golden_bottom.csv',
        mime='text/csv',
    )
    
    st.dataframe(
        df_show[["등급", "테마", "이름", "현재가", "흐름", "위치", "특이사항", "🎯목표가", "🛡️손절가", "뉴스링크"]],
        column_config={
            "흐름": st.column_config.LineChartColumn("최근 30일 추세"),
            "뉴스링크": st.column_config.LinkColumn("팩트체크", display_text="👉뉴스확인")
        },
        use_container_width=True,
        height=800
    )
