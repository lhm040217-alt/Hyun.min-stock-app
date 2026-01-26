import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
import time
import numpy as np
from datetime import datetime, timedelta

# --- 페이지 설정 ---
st.set_page_config(page_title="Tenbagger V46 (Control)", layout="wide")
st.title("🎛️ 텐배거 V46 (사용자 통제권 복구)")
st.markdown("""
**"제멋대로 판단하지 않고, 입력하신 그대로 수행합니다."**
1.  **시총 제한 해제:** 입력하신 시총 상한선(`vip_cap_limit`)을 100% 따릅니다.
2.  **엄격 모드 부활:** 체크하면 '실적+추세'를 보고, 끄면 '거래량'만 봅니다.
3.  **바닥권 포착:** 거래량 500% 폭발한 종목을 찾아냅니다.
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
            return "🔴", "조정장", f"지수가 20일선 아래입니다. ({symbol})"
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
st.sidebar.header("🛠 설정 (V46 Control)")
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
    
    # [수정] 시총 제한값 입력 (기본값 20억 달러/2조원, 하지만 변경 가능)
    vip_cap_limit = st.sidebar.number_input("시총 상한(억/M달러)", value=2000)
    
    st.sidebar.markdown("---")
    # [복구] 엄격 모드 체크박스 부활
    strict_mode = st.sidebar.checkbox("🔒 엄격 모드 (매출성장 + 20일선 위)", value=True)
    st.sidebar.caption("체크 해제 시: 적자 기업이나 역배열이라도 거래량 터지면 다 보여줍니다.")
    
    st.sidebar.markdown("---")
    theme_options = list(THEME_KEYWORDS.keys()) + ["기타"]
    selected_themes = st.sidebar.multiselect("테마 선택", theme_options, default=[])

except Exception as e:
    st.error(f"오류: {e}")
    st.stop()

# --- 분석 로직 ---
def analyze_stock_v46(ticker, name, country, strict, cap_limit):
    try:
        stock = yf.Ticker(ticker)
        
        # 1. 기술적 필터
        df = stock.history(period="1y")
        if len(df) < 60: return None
        if df['Volume'].iloc[-1] == 0: return None

        curr_price = df['Close'].iloc[-1]
        low_52w = df['Close'].min()
        
        # [조건 1] 이격도: 바닥 대비 3배 미만 (이건 바닥주 핵심이라 유지)
        if curr_price > low_52w * 3.0: return None 
        
        # [조건 2] 폭락주 필터 (안전장치)
        # 거래량 실린 장대음봉(-3% 이하)은 무조건 거름
        price_change_pct = (curr_price - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100
        if price_change_pct < -3.0: return None 
        
        # [조건 3] 거래량 폭발 (500% 이상)
        vol_avg = df['Volume'].iloc[-20:-1].mean()
        vol_now = df['Volume'].iloc[-1]
        if (vol_now * curr_price) < 100000000: return None # 잡주 필터
        
        ratio_vol = vol_now / vol_avg if vol_avg > 0 else 0
        if ratio_vol < 5.0: return None 
        
        # [엄격 모드 적용 구간 - 추세]
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        if strict:
            if curr_price < ma20: return None # 엄격: 역배열 칼같이 제외
        
        # 2. 퀀트 필터 (시총 연동 수정)
        try:
            fast_info = stock.fast_info
            mkt_cap = fast_info['market_cap']
        except: return None
            
        if country == "KR":
            mkt_cap_val = mkt_cap / 100000000 
            # [수정] 하한선 300억, 상한선은 cap_limit 변수 사용 (하드코딩 삭제)
            if not (300 <= mkt_cap_val <= cap_limit): return None
            mkt_str = f"{mkt_cap_val:.0f}억"
            code_pure = ticker.replace(".KQ", "").replace(".KS", "")
            news_url = f"https://m.stock.naver.com/item/main.nhn?code={code_pure}#/news/0"
        else:
            mkt_cap_val = mkt_cap / 1000000
            # [수정] 하한선 30M, 상한선은 cap_limit 변수 사용
            if not (30 <= mkt_cap_val <= cap_limit): return None
            mkt_str = f"${mkt_cap_val:.1f}M"
            news_url = f"https://finance.yahoo.com/quote/{ticker}/news"

        info = stock.info
        
        # [엄격 모드 적용 구간 - 실적]
        rev_growth = info.get('revenueGrowth', 0)
        if rev_growth is None: rev_growth = 0
        if strict:
            if rev_growth < 0: return None # 엄격: 매출 역성장 제외
        
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
        final_grade = "💎A급(세력포착)"
        bonus_tags = [f"⚡거래량{ratio_vol:.1f}배"]
        
        if ratio_vol >= 10.0:
            final_grade = "👑S급(매집폭발)"
            bonus_tags.append("🔥초강력수급")
            
        profit_margin = info.get('profitMargins', 0)
        if profit_margin > 0: bonus_tags.append("💰흑자")
        if rev_growth > 0.20: bonus_tags.append("🚀고성장")
            
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
if "scan_results_v46" not in st.session_state:
    st.session_state.scan_results_v46 = None

if st.button(f"🎛️ V46 사용자 맞춤 스캔 ({start_idx}~{end_idx})"):
    
    target_slice = full_list.iloc[start_idx:end_idx]
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    specific_theme_mode = len(selected_themes) > 0
    theme_label = ", ".join(selected_themes) if specific_theme_mode else "전체"
    
    # 설정값 확인 메시지
    strict_msg = "ON (매출성장+추세)" if strict_mode else "OFF (모두 허용)"
    st.info(f"설정값: 시총 {vip_cap_limit} 이하 | 엄격모드 {strict_msg} | 테마: {theme_label}")
    
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
            
        status_text.text(f"🔍 맞춤 분석 중... [{i+1}/{len(target_slice)}]: {name}")
        
        time.sleep(0.05)
        
        # [핵심] 입력된 cap_limit 값을 함수로 전달
        res = analyze_stock_v46(ticker, name, country, strict_mode, vip_cap_limit)
        
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
        
        st.session_state.scan_results_v46 = df
        st.success(f"🎛️ 완료! {len(results)}개 발굴. 설정하신 기준대로 뽑았습니다.")
    else:
        st.warning("조건에 맞는 종목이 없습니다. (시총 범위나 엄격 모드를 조절해보세요.)")

if st.session_state.scan_results_v46 is not None:
    df_show = st.session_state.scan_results_v46
    
    csv = df_show.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="💾 결과 엑셀로 저장",
        data=csv,
        file_name='tenbagger_control_list.csv',
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

