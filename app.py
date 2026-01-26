import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
import time
import numpy as np
from datetime import datetime, timedelta

# --- 페이지 설정 ---
st.set_page_config(page_title="Tenbagger V43 (The Final)", layout="wide")
st.title("👑 텐배거 V43 (The Final)")
st.markdown("""
**"시장 파악부터 종목 발굴, 결과 저장까지."**
1.  **🚦 시장 신호등:** 오늘이 매수해도 되는 날인지 지수를 먼저 체크합니다.
2.  **📉 미니 차트:** 표 안에서 최근 1달간의 주가 흐름을 바로 확인합니다.
3.  **💾 엑셀 저장:** 소중한 발굴 리스트를 파일로 저장하세요.
""")

# --- [기능 1] 시장 신호등 로직 ---
def check_market_status(market_type):
    try:
        # 코스피(KS11) 또는 나스닥(IXIC) 지수 확인
        symbol = "IXIC" if "나스닥" in market_type else "KS11"
        df = fdr.DataReader(symbol, start=(datetime.now() - timedelta(days=60)))
        
        curr_idx = df['Close'].iloc[-1]
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        
        # 20일 이동평균선 위에 있으면 상승장(안전), 아래면 하락장(주의)
        if curr_idx > ma20:
            return "🟢", "상승 추세 (매수 가능 구간)", f"지수가 20일선 위에 있습니다. ({symbol})"
        else:
            return "🔴", "하락/조정 추세 (매수 주의)", f"지수가 20일선 아래입니다. 비중을 줄이세요. ({symbol})"
    except:
        return "⚪", "시장 데이터 수신 불가", "지수 데이터를 가져오지 못했습니다."

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
    "🚀우주/방산": ["Space", "Satellite", "Rocket", "Defense", "Weapon", "Aerospace", "우주", "위성", "방산", "전쟁", "Aviation"],
    "🤖AI/로봇": ["AI", "Robot", "Artificial Intelligence", "NPU", "Deep Learning", "로봇", "인공지능", "휴머노이드", "Automation"],
    "🧬바이오/헬스": ["Bio", "Drug", "Pharma", "Cancer", "Therapeutics", "Clinical", "Genomic", "바이오", "신약", "임상", "비만", "알츠하이머"],
    "🔋2차전지/에너지": ["Battery", "Lithium", "Cathode", "EV", "Energy", "Solar", "배터리", "리튬", "양극재", "전고체", "ESS"],
    "💾반도체": ["Semiconductor", "Chip", "Foundry", "HBM", "Memory", "반도체", "팹리스", "유리기판", "DRAM"],
    "💎자원/광물": ["Mining", "Metals", "Gold", "Silver", "Mineral", "Rare Earth", "Polymetallic", "Antimony", "광물", "자원", "구리", "해저"],
    "☁️SW/플랫폼": ["Software", "SaaS", "Platform", "Cloud", "Cyber", "Data", "Security", "플랫폼", "보안", "웹툰", "게임"],
    "🏦금융/은행": ["Bank", "Financial", "Capital", "Insurance", "Invest", "Holding", "Bancorp", "Finance", "지주"],
}

# --- 설정 패널 ---
st.sidebar.header("🛠 설정 (V43 The Final)")
market_type = st.sidebar.radio("시장", ["나스닥 (NASDAQ)", "코스닥/코스피 (KRX)"])

# [기능 1] 시장 신호등 표시
icon, status, desc = check_market_status(market_type)
st.info(f"🚦 **오늘의 시장 신호: {icon} {status}**\n\n*{desc}*")

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
    with st.spinner("거래소 데이터 로딩 중..."):
        full_list, list_status = load_data(market_type)
        total_len = len(full_list)
        
    if list_status == "EMERGENCY":
        st.warning("⚠️ 비상용 리스트 모드")
        start_idx, end_idx = 0, total_len
    else:
        c1, c2 = st.sidebar.columns(2)
        start_idx = c1.number_input("시작 번호", 0, total_len-1, 0)
        end_idx = c2.number_input("끝 번호", 1, total_len, min(100, total_len))
        
    vip_cap_limit = st.sidebar.number_input("시총 상한(억/M달러)", value=30000)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 핀포인트 테마")
    theme_options = list(THEME_KEYWORDS.keys()) + ["기타"]
    selected_themes = st.sidebar.multiselect("테마 선택 (비워두면 전체)", theme_options, default=[])
    
    st.sidebar.markdown("---")
    strict_mode = st.sidebar.checkbox("🔒 엄격한 기준 (매출20% + 신고가)", value=True)

except Exception as e:
    st.error(f"오류: {e}")
    st.stop()

# --- RSI 계산 ---
def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- 분석 로직 ---
def analyze_stock_v43(ticker, name, country, strict, specific_theme_mode):
    try:
        stock = yf.Ticker(ticker)
        
        # 1. 기술적 필터 & 차트 데이터
        df = stock.history(period="1y")
        if len(df) < 60: return None
        if df['Volume'].iloc[-1] == 0: return None

        curr_price = df['Close'].iloc[-1]
        high_52w = df['Close'].max()
        
        # [기능 2] 미니 차트용 데이터 (최근 30일)
        mini_chart_data = df['Close'].tail(30).tolist()
        
        if strict and not specific_theme_mode:
            if curr_price < high_52w * 0.85: return None 
        
        df['RSI'] = calculate_rsi(df['Close'])
        rsi_val = df['RSI'].iloc[-1]
        
        # 2. 퀀트 필터
        try:
            fast_info = stock.fast_info
            mkt_cap = fast_info['market_cap']
        except: return None
            
        if country == "KR":
            mkt_cap_val = mkt_cap / 100000000 
            if not (300 <= mkt_cap_val <= vip_cap_limit): return None
            mkt_str = f"{mkt_cap_val:.0f}억"
            code_pure = ticker.replace(".KQ", "").replace(".KS", "")
            news_url = f"https://m.stock.naver.com/item/main.nhn?code={code_pure}#/news/0"
        else:
            mkt_cap_val = mkt_cap / 1000000
            if not (30 <= mkt_cap_val <= vip_cap_limit): return None
            mkt_str = f"${mkt_cap_val:.1f}M"
            news_url = f"https://finance.yahoo.com/quote/{ticker}/news"

        info = stock.info
        rev_growth = info.get('revenueGrowth', 0)
        if rev_growth is None: rev_growth = 0
        if strict and not specific_theme_mode and rev_growth < 0.20: return None 
        
        # --- Scoring ---
        score = 0
        bonus_tags = []
        
        inst_holder = info.get('heldPercentInstitutions', 0)
        if inst_holder and inst_holder > 0.3: 
            bonus_tags.append("🏢기관픽")
            score += 1
            
        vol_avg = df['Volume'].iloc[-20:-1].mean()
        vol_now = df['Volume'].iloc[-1]
        if vol_now > vol_avg * 2.0: 
            bonus_tags.append("🔥큰손유입")
            score += 1

        profit_margin = info.get('profitMargins', 0)
        if profit_margin > 0.15: 
            score += 1
            bonus_tags.append("💰고마진")
            
        insider = info.get('heldPercentInsiders', 0)
        if insider and insider > 0.10: 
            score += 1
            bonus_tags.append(f"🔒오너({insider*100:.0f}%)")
        
        peg_ratio = info.get('pegRatio', None)
        if peg_ratio and 0 < peg_ratio < 1.0:
            score += 1
            bonus_tags.append("💎저평가")

        start_price_3mo = df['Close'].iloc[-60] if len(df) > 60 else df['Close'].iloc[0]
        change_3mo = (curr_price - start_price_3mo) / start_price_3mo
        if change_3mo > 0.20:
            score += 1
            bonus_tags.append("🚀주도주")
        
        theme_detected = "기타"
        summary = (info.get('longBusinessSummary', '') + " " + info.get('industry', '')).lower()
        for theme, keywords in THEME_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in summary:
                    theme_detected = theme
                    break
            if theme_detected != "기타": break
            
        final_grade = "B급"
        if score >= 4: final_grade = "👑S급(텐배거)"
        elif score >= 2: final_grade = "💎A급"
        
        real_name = info.get('longName', name)
        
        if rsi_val > 75: rsi_status = "⚠️과열"
        elif rsi_val < 40: rsi_status = "❄️침체"
        else: rsi_status = "✅적정"

        target_price = curr_price * 1.10
        stop_price = curr_price * 0.97
        
        if country == "KR":
            target_str = f"{target_price:,.0f}"
            stop_str = f"{stop_price:,.0f}"
        else:
            target_str = f"${target_price:.2f}"
            stop_str = f"${stop_price:.2f}"

        return {
            "등급": final_grade,
            "테마": theme_detected,
            "이름": real_name,
            "현재가": f"{curr_price:,.0f}" if country=="KR" else f"${curr_price:.2f}",
            "흐름": mini_chart_data, # 차트 데이터
            "🎯목표가": target_str,
            "🛡️손절가": stop_str,
            "매출성장": f"+{rev_growth*100:.1f}%",
            "RSI": rsi_status,
            "수급/특이": " ".join(bonus_tags),
            "뉴스링크": news_url,
            "등락률_수치": change_3mo * 100
        }

    except:
        return None

# --- 실행 및 결과 저장(Session State) ---
if "scan_results" not in st.session_state:
    st.session_state.scan_results = None

if st.button(f"👑 V43 최종 스캔 시작 ({start_idx}~{end_idx})"):
    
    target_slice = full_list.iloc[start_idx:end_idx]
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    specific_theme_mode = len(selected_themes) > 0
    theme_label = ", ".join(selected_themes) if specific_theme_mode else "전체"
    
    st.info(f"테마: [{theme_label}] / 시장 체크 완료")
    
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
        
        res = analyze_stock_v43(ticker, name, country, strict_mode, specific_theme_mode)
        
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
        
        # 대장주 매핑
        theme_leaders = {}
        valid_df = df[df['테마'] != '기타']
        for theme in valid_df['테마'].unique():
            subset = valid_df[valid_df['테마'] == theme]
            if not subset.empty:
                leader = subset.loc[subset['등락률_수치'].idxmax()]
                if leader['등락률_수치'] > 5.0:
                    theme_leaders[theme] = leader['이름']
        
        df['관련_대장주'] = "-"
        for index, row in df.iterrows():
            t = row['테마']
            if t in theme_leaders:
                if row['이름'] == theme_leaders[t]: df.at[index, '관련_대장주'] = "👑대장"
                else: df.at[index, '관련_대장주'] = theme_leaders[t]

        grade_order = {"👑S급(텐배거)": 0, "💎A급": 1, "B급": 2}
        df["우선순위"] = df["등급"].map(grade_order)
        df = df.sort_values("우선순위").drop(columns=["우선순위"])
        
        # 결과 세션 저장
        st.session_state.scan_results = df
        st.success(f"👑 발굴 완료! {len(results)}개 종목이 저장되었습니다.")
    else:
        st.warning("조건에 맞는 종목이 없습니다.")

# --- 결과 출력 및 엑셀 다운로드 (저장된 데이터 표시) ---
if st.session_state.scan_results is not None:
    df_show = st.session_state.scan_results
    
    # [기능 3] 엑셀 다운로드 버튼
    csv = df_show.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="💾 결과 엑셀로 저장하기",
        data=csv,
        file_name='tenbagger_list.csv',
        mime='text/csv',
    )
    
    # [기능 2] 미니 차트 포함 테이블 출력
    st.dataframe(
        df_show[["등급", "테마", "관련_대장주", "이름", "현재가", "흐름", "🎯목표가", "🛡️손절가", "RSI", "수급/특이", "뉴스링크"]],
        column_config={
            "흐름": st.column_config.LineChartColumn(
                "최근 30일 추세", width="medium", y_min=0, y_max=None
            ),
            "뉴스링크": st.column_config.LinkColumn("팩트체크", display_text="👉뉴스확인")
        },
        use_container_width=True,
        height=800
    )
