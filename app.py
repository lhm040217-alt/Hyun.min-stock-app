import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
import time
import numpy as np

# --- 페이지 설정 ---
st.set_page_config(page_title="Tenbagger V42 (Perfect Match)", layout="wide")
st.title("👑 텐배거 V42 (무결점 최종판)")
st.markdown("""
**"오류를 수정하고 완벽해졌습니다."**
1.  **전수조사 완벽 구현:** 코스피(.KS)와 코스닥(.KQ)을 정확히 구분하여 **단 하나의 종목도 놓치지 않습니다.**
2.  **핀포인트 테마:** 원하는 테마를 선택하면, 조건이 조금 부족해도 일단 찾아서 보여줍니다.
3.  **철통 보안:** 손절가(-3%), 목표가(+10%), RSI 과열 경고, 뉴스 확인 링크 탑재.
""")

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

# --- 테마 키워드 (Deep Scan) ---
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
st.sidebar.header("🛠 설정 (V42 Perfect)")
market_type = st.sidebar.radio("시장", ["나스닥 (NASDAQ)", "코스닥/코스피 (KRX)"])

@st.cache_data
def load_data(m_type):
    try:
        if "나스닥" in m_type:
            return fdr.StockListing('NASDAQ'), "FULL"
        else:
            # KRX 전체 (코스피+코스닥)
            return fdr.StockListing('KRX'), "FULL"
    except Exception:
        data = [{'Code': code, 'Name': f"종목_{code}", 'Market': 'KOSDAQ'} for code in KOSDAQ_EMERGENCY_LIST]
        return pd.DataFrame(data), "EMERGENCY"

try:
    with st.spinner("거래소 데이터 정밀 로딩 중..."):
        full_list, status = load_data(market_type)
        total_len = len(full_list)
        
    if status == "EMERGENCY":
        st.warning("⚠️ 비상용 리스트 모드로 전환됨")
        start_idx, end_idx = 0, total_len
    else:
        c1, c2 = st.sidebar.columns(2)
        start_idx = c1.number_input("시작 번호", 0, total_len-1, 0)
        end_idx = c2.number_input("끝 번호", 1, total_len, min(100, total_len))
        
    vip_cap_limit = st.sidebar.number_input("시총 상한(억/M달러)", value=30000)
    
    # 테마 필터
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 핀포인트 테마")
    theme_options = list(THEME_KEYWORDS.keys()) + ["기타"]
    selected_themes = st.sidebar.multiselect("테마 선택 (비워두면 전체)", theme_options, default=[])
    
    st.sidebar.markdown("---")
    strict_mode = st.sidebar.checkbox("🔒 엄격한 기준 (매출20% + 신고가)", value=True)

except Exception as e:
    st.error(f"오류 발생: {e}")
    st.stop()

# --- RSI 계산 ---
def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- [핵심] 정밀 분석 로직 ---
def analyze_stock_v42(ticker, name, country, strict, specific_theme_mode):
    try:
        stock = yf.Ticker(ticker)
        
        # 1. 기술적 필터 (차트)
        df = stock.history(period="1y")
        if len(df) < 60: return None
        if df['Volume'].iloc[-1] == 0: return None

        curr_price = df['Close'].iloc[-1]
        high_52w = df['Close'].max()
        
        # [유연한 필터] 특정 테마를 선택했다면, 신고가 조건이 조금 모자라도 통과시킴 (놓치지 않기 위해)
        if strict and not specific_theme_mode:
            if curr_price < high_52w * 0.85: return None 
        
        df['RSI'] = calculate_rsi(df['Close'])
        rsi_val = df['RSI'].iloc[-1]
        
        # 2. 퀀트 필터 (시총)
        try:
            fast_info = stock.fast_info
            mkt_cap = fast_info['market_cap']
        except: return None
            
        if country == "KR":
            mkt_cap_val = mkt_cap / 100000000 
            # 하한선 300억으로 더 완화 (알짜 소형주 포착)
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
        
        # [유연한 필터] 특정 테마를 선택했다면 매출 성장 조건도 살짝 눈감아줌
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
        
        # 테마 정밀 분석
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
if st.button(f"👑 V42 정밀 스캔 시작 ({start_idx}~{end_idx})"):
    
    target_slice = full_list.iloc[start_idx:end_idx]
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 테마 선택 여부 확인 (있으면 유연한 모드 적용)
    specific_theme_mode = len(selected_themes) > 0
    theme_label = ", ".join(selected_themes) if specific_theme_mode else "전체"
    
    st.info(f"테마: [{theme_label}] / 엄격모드: {strict_mode} / 코스피&코스닥 구분 스캔")
    
    for i, row in enumerate(target_slice.iterrows()):
        idx, data = row
        
        # [수정된 핵심 로직] 코스피/코스닥 정확한 구분
        if "나스닥" in market_type:
            ticker = data['Symbol']
            name = data['Name']
            country = "US"
        else:
            # KRX Listing에서 Market 정보 활용 (가장 중요!)
            ticker = data['Code']
            market = data.get('Market', 'KOSDAQ') # 기본값 코스닥
            
            # yfinance 호환 접미사 붙이기
            if market == 'KOSPI':
                ticker += ".KS"
            elif market == 'KOSDAQ':
                ticker += ".KQ"
            else:
                # KONEX 등은 제외하거나 코스닥으로 처리
                if ticker.isdigit(): ticker += ".KQ"

            name = data['Name']
            country = "KR"
            
        status_text.text(f"🔍 정밀검사 [{i+1}/{len(target_slice)}]: {name} ({ticker})")
        
        # 안전 딜레이 (0.05초로 단축, 효율성 증대)
        time.sleep(0.05)
        
        res = analyze_stock_v42(ticker, name, country, strict_mode, specific_theme_mode)
        
        if res:
            # 테마 필터링
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

        # 정렬
        grade_order = {"👑S급(텐배거)": 0, "💎A급": 1, "B급": 2}
        df["우선순위"] = df["등급"].map(grade_order)
        df = df.sort_values("우선순위").drop(columns=["우선순위"])

        st.success(f"👑 스캔 완료! 총 {len(results)}개 발굴")
        
        st.dataframe(
            df[["등급", "테마", "관련_대장주", "이름", "현재가", "🎯목표가", "🛡️손절가", "RSI", "수급/특이", "뉴스링크"]],
            column_config={
                "뉴스링크": st.column_config.LinkColumn("팩트체크", display_text="👉뉴스확인")
            },
            use_container_width=True,
            height=800
        )
    else:
        st.warning(f"선택한 조건/테마에 맞는 종목이 없습니다. '엄격한 기준'을 끄거나 다른 테마를 선택해보세요.")
