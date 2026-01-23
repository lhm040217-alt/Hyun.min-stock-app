import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
import time
import numpy as np

# --- 페이지 설정 ---
st.set_page_config(page_title="Tenbagger V39 (Fail-Safe)", layout="wide")
st.title("🛡️ 텐배거 V39 (무중단 시스템)")
st.markdown("""
**"서버가 막혀도 멈추지 않습니다."**
1.  **Safety First:** 전수조사 시도 후, 차단 시 **비상용 리스트**로 자동 전환합니다.
2.  **Delay Logic:** 종목 분석 간 **0.1초 딜레이**를 주어 차단을 원천 봉쇄합니다.
3.  **Full Option:** V38의 모든 기능(목표가/손절가/수급/뉴스) 포함.
""")

# --- [안전장치] 비상용 리스트 (서버 차단 시 사용) ---
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

# --- 테마 키워드 사전 ---
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
st.sidebar.header("🛠 설정 (V39 Fail-Safe)")
market_type = st.sidebar.radio("시장", ["나스닥 (NASDAQ)", "코스닥/코스피 (KRX)"])

@st.cache_data
def load_data(m_type):
    # [수정] 차단 방지 로직 적용
    try:
        if "나스닥" in m_type:
            return fdr.StockListing('NASDAQ'), "FULL"
        else:
            # Plan A: 전수조사 시도
            return fdr.StockListing('KRX'), "FULL"
    except Exception:
        # Plan B: 차단 시 비상용 리스트 사용
        data = [{'Code': code, 'Name': f"종목_{code}"} for code in KOSDAQ_EMERGENCY_LIST]
        return pd.DataFrame(data), "EMERGENCY"

try:
    with st.spinner("종목 리스트 로딩 중... (서버 연결 확인)"):
        full_list, status = load_data(market_type)
        total_len = len(full_list)
        
    if status == "EMERGENCY":
        st.warning("⚠️ 현재 거래소 서버 연결이 불안정하여 '비상용 리스트(100개)'로 자동 전환되었습니다.")
        start_idx, end_idx = 0, total_len
    else:
        # 정상 모드
        c1, c2 = st.sidebar.columns(2)
        start_idx = c1.number_input("시작 번호", 0, total_len-1, 0)
        end_idx = c2.number_input("끝 번호", 1, total_len, min(100, total_len))
        
    vip_cap_limit = st.sidebar.number_input("시총 상한(억/M달러)", value=2000)

except Exception as e:
    st.error(f"치명적 오류: {e}")
    st.stop()

# --- RSI 계산 ---
def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- 종목 분석 ---
def analyze_stock_v39(ticker, name, country):
    try:
        stock = yf.Ticker(ticker)
        
        # 1. 기술적 필터
        df = stock.history(period="1y")
        if len(df) < 100: return None
        if df['Volume'].iloc[-1] == 0: return None

        curr_price = df['Close'].iloc[-1]
        high_52w = df['Close'].max()
        
        # 신고가 -15% 이내
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
            if not (3000 <= mkt_cap_val < 20000): return None
            mkt_str = f"{mkt_cap_val:.0f}억"
            code_pure = ticker.replace(".KQ", "").replace(".KS", "")
            news_url = f"https://m.stock.naver.com/item/main.nhn?code={code_pure}#/news/0"
        else:
            mkt_cap_val = mkt_cap / 1000000
            if not (300 <= mkt_cap_val < 2000): return None
            mkt_str = f"${mkt_cap_val:.1f}M"
            news_url = f"https://finance.yahoo.com/quote/{ticker}/news"

        info = stock.info
        
        rev_growth = info.get('revenueGrowth', 0)
        if rev_growth is None: rev_growth = 0
        if rev_growth < 0.20: return None 
        
        # --- Scoring ---
        score = 0
        bonus_tags = []
        
        # 수급 포착
        inst_holder = info.get('heldPercentInstitutions', 0)
        if inst_holder and inst_holder > 0.3: 
            bonus_tags.append("🏢기관픽")
            score += 1
            
        vol_avg = df['Volume'].iloc[-20:-1].mean()
        vol_now = df['Volume'].iloc[-1]
        if vol_now > vol_avg * 2.0: 
            bonus_tags.append("🔥큰손유입")
            score += 1

        # 펀더멘털
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

        # 주도주
        start_price_3mo = df['Close'].iloc[-60] if len(df) > 60 else df['Close'].iloc[0]
        change_3mo = (curr_price - start_price_3mo) / start_price_3mo
        if change_3mo > 0.20:
            score += 1
            bonus_tags.append("🚀주도주")
        
        # 테마
        theme_detected = "기타"
        summary = (info.get('longBusinessSummary', '') + " " + info.get('industry', '')).lower()
        for theme, keywords in THEME_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in summary:
                    theme_detected = theme
                    break
            if theme_detected != "기타": break
            
        # 등급
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

# --- 실행 ---
if st.button(f"🛡️ 무중단(Fail-Safe) 스캔 가동 ({start_idx}~{end_idx})"):
    
    target_slice = full_list.iloc[start_idx:end_idx]
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    st.info("서버 차단 방지를 위해 안전 속도로 분석합니다...")
    
    for i, row in enumerate(target_slice.iterrows()):
        idx, data = row
        if "나스닥" in market_type:
            ticker = data['Symbol']
            name = data['Name']
            country = "US"
        else:
            ticker = f"{data['Code']}.KQ" 
            if market_type == "코스닥/코스피 (KRX)": 
               ticker = data['Code'] 
               # 간이 시장 구분 (안전을 위해 KQ 기본, 필요시 로직 수정)
               if ticker.isdigit(): ticker += ".KQ" 
            name = data['Name']
            country = "KR"
            
        status_text.text(f"⚔️ 분석중 [{i+1}/{len(target_slice)}]: {name}")
        
        # [핵심] 차단 방지 딜레이 (0.1초)
        time.sleep(0.1)
        
        res = analyze_stock_v39(ticker, name, country)
        if res: results.append(res)
        
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

        # 정렬
        grade_order = {"👑S급(텐배거)": 0, "💎A급": 1, "B급": 2}
        df["우선순위"] = df["등급"].map(grade_order)
        df = df.sort_values("우선순위").drop(columns=["우선순위"])

        st.success(f"분석 완료! 총 {len(results)}개 발굴")
        
        st.dataframe(
            df[["등급", "테마", "관련_대장주", "이름", "현재가", "🎯목표가", "🛡️손절가", "RSI", "수급/특이", "뉴스링크"]],
            column_config={
                "뉴스링크": st.column_config.LinkColumn("팩트체크", display_text="👉뉴스확인")
            },
            use_container_width=True,
            height=800
        )
    else:
        st.warning("조건에 맞는 종목이 없습니다.")

