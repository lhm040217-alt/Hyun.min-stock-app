import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd

# --- 페이지 설정 ---
st.set_page_config(page_title="Tenbagger V32 (Final)", layout="wide")
st.title("🔗 텐배거 V32 (최종 완성본)")
st.markdown("""
**"요청하신 모든 기능을 탑재했습니다."**
1.  **매집주 집중:** 안전한 바닥권(0~4%) 종목을 **[💎매집VIP]**로 추천합니다.
2.  **족보 연결:** 테마 대장이 누구인지 **[관련 대장주]** 칸에 보여줍니다.
3.  **우주/테마:** **[🚀우주/항공]** 등 핵심 테마와 급등주 트렌드를 모두 잡습니다.
""")

# --- 테마 키워드 사전 (우주/로켓 포함) ---
THEME_KEYWORDS = {
    "🚀우주/항공": ["Space", "Satellite", "Rocket", "Aerospace", "우주", "위성", "로켓", "항공", "UAM"],
    "🤖AI/로봇": ["AI", "Artificial Intelligence", "Robot", "인공지능", "로봇", "Neural", "Deep Learning"],
    "🔋2차전지": ["Battery", "Lithium", "Cathode", "배터리", "리튬", "양극재", "음극재", "전기차", "EV"],
    "💾반도체": ["Semiconductor", "Chip", "Foundry", "반도체", "HBM", "DRAM", "Memory", "System"],
    "🧬바이오": ["Bio", "Drug", "Pharma", "Cancer", "바이오", "신약", "제약", "임상", "Cell"],
    "☁️플랫폼": ["Platform", "Game", "Metaverse", "Cloud", "게임", "메타버스", "소프트웨어", "SaaS"],
    "🛡️방산/에너지": ["Energy", "Defense", "Solar", "Wind", "방산", "에너지", "태양광", "Nuclear"],
    "💄소비/화장품": ["Cosmetic", "Food", "Retail", "화장품", "식품", "유통", "K-Beauty"],
}

# --- 코스닥 내장 리스트 (서버 차단 방지) ---
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

# --- 설정 패널 ---
st.sidebar.header("🛠 설정")
market_type = st.sidebar.radio("시장", ["나스닥 (NASDAQ)", "코스닥 (KOSDAQ)"])

@st.cache_data
def load_data(m_type):
    if "나스닥" in m_type:
        try: return fdr.StockListing('NASDAQ'), "FULL"
        except: return pd.DataFrame(), "ERROR"
    else:
        data = [{'Code': code, 'Name': f"종목_{code}"} for code in KOSDAQ_EMERGENCY_LIST]
        return pd.DataFrame(data), "BUILTIN"

try:
    full_list, list_type = load_data(market_type)
    total_len = len(full_list)
    
    if list_type == "FULL":
        # [검증] 무제한 범위 입력 가능
        c1, c2 = st.sidebar.columns(2)
        start_idx = c1.number_input("시작", 0, total_len-1, 0)
        end_idx = c2.number_input("끝", 1, total_len, min(100, total_len))
    else:
        start_idx, end_idx = 0, total_len
except:
    st.error("로딩 실패")
    st.stop()

vip_cap_limit = st.sidebar.number_input("시총 상한(억/M달러)", value=5000)

# --- 분석 로직 ---
def analyze_stock_final(ticker, name, country):
    try:
        stock = yf.Ticker(ticker)
        
        # 1. 차트 데이터
        df = stock.history(period="3mo")
        if len(df) < 60: return None
        if df['Volume'].iloc[-1] == 0: return None

        close = df['Close']
        volume = df['Volume']
        curr_price = close.iloc[-1]

        # 2. 시총 필터
        try: mkt_cap = stock.fast_info['market_cap']
        except: mkt_cap = 0
            
        if country == "KR": mkt_cap_calc = mkt_cap / 100000000 
        else: mkt_cap_calc = mkt_cap / 1000000
            
        if mkt_cap_calc > vip_cap_limit: return None
        if mkt_cap_calc == 0: return None

        # 3. 기술적 지표
        vol_avg = volume.iloc[-20:-1].mean()
        vol_ratio = volume.iloc[-1] / vol_avg if vol_avg > 0 else 0
        price_change = (curr_price - close.iloc[-2]) / close.iloc[-2] * 100
        
        ma5 = close.rolling(5).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        std = close.rolling(20).std().iloc[-1]
        upper_band = ma20 + (2 * std)
        lower_band = ma20 - (2 * std)
        band_width = (upper_band - lower_band) / ma20 

        # 4. 테마 및 호재 분석
        theme_detected = "기타"
        hojae_tags = [] 
        
        try:
            info = stock.info
            
            summary = info.get('longBusinessSummary', '') + " " + info.get('industry', '')
            for theme, keywords in THEME_KEYWORDS.items():
                for kw in keywords:
                    if kw.lower() in summary.lower():
                        theme_detected = theme
                        break
                if theme_detected != "기타": break
            
            rev_growth = info.get('revenueGrowth', 0)
            profit_margin = info.get('profitMargins', 0)
            insider_hold = info.get('heldPercentInsiders', 0)
            
            if rev_growth > 0.3: hojae_tags.append("⚡고성장")
            if profit_margin > 0.15: hojae_tags.append("💰알짜")
            if insider_hold > 0.2: hojae_tags.append("🔒품절주")
            
            real_name = info.get('longName', name)
        except:
            real_name = name

        if band_width < 0.15: hojae_tags.append("💣폭발임박")
        if vol_ratio > 3.0: hojae_tags.append("🔥수급폭발")

        hojae_str = " ".join(hojae_tags) if hojae_tags else "-"

        # 5. 등급 판정
        grade = "FAIL"
        
        # [💎VIP] 안전형 매집: 4% 이하 눌림목 (가장 중요)
        if vol_ratio >= 2.0 and 0 <= price_change <= 4.0 and ma5 >= ma20:
            grade = "💎매집VIP"
        # [🔥주도주] 급등형: 시장 파악용
        elif price_change >= 10.0:
            grade = "🔥주도주(급등)"
        # [⚡응축] 대기형
        elif band_width <= 0.20 and ma5 >= ma20:
            grade = "⚡응축대기"
        # [📈전환] 추세형
        elif price_change > 0 and close.iloc[-1] > ma20 and vol_ratio > 1.5:
             grade = "📈추세전환"
        # [NORMAL] 데이터 수집용
        elif price_change > 0:
            grade = "NORMAL"

        if grade == "FAIL": return None

        return {
            "등급": grade,
            "테마": theme_detected,
            "호재": hojae_str,
            "이름": real_name,
            "현재가": f"{curr_price:,.0f}" if country=="KR" else f"${curr_price:.2f}",
            "등락률_수치": price_change,
            "등락률": f"{price_change:+.1f}%",
            "거래량": f"{vol_ratio:.1f}배",
            "시총": f"{mkt_cap_calc:.0f}억" if country=="KR" else f"${mkt_cap_calc:.1f}M",
            "관련_대장주": "-"
        }

    except:
        return None

# --- 실행 ---
if st.button(f"🔍 전체 분석 및 족보 연결 ({start_idx}~{end_idx})"):
    
    target_slice = full_list.iloc[start_idx:end_idx]
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    st.info("개별 종목 분석 및 테마별 대장주 연결 중...")
    
    for i, row in enumerate(target_slice.iterrows()):
        idx, data = row
        if "나스닥" in market_type:
            ticker = data['Symbol']
            name = data['Name']
            country = "US"
        else:
            ticker = f"{data['Code']}.KQ"
            name = data['Name']
            country = "KR"
            
        status_text.text(f"분석중.. {ticker}")
        
        res = analyze_stock_final(ticker, name, country)
        if res: results.append(res)
        
        progress_bar.progress((i + 1) / len(target_slice))

    status_text.empty()
    progress_bar.empty()
    
    if results:
        df = pd.DataFrame(results)
        
        # --- [검증] 대장주 - 후발주 매핑 로직 ---
        theme_leaders = {}
        valid_df = df[df['테마'] != '기타']
        
        # 1. 각 테마별 대장(가장 많이 오른 놈) 찾기
        for theme in valid_df['테마'].unique():
            theme_subset = valid_df[valid_df['테마'] == theme]
            if not theme_subset.empty:
                leader = theme_subset.loc[theme_subset['등락률_수치'].idxmax()]
                if leader['등락률_수치'] > 5.0: # 5% 이상 올라야 대장 취급
                    theme_leaders[theme] = {
                        "name": leader['이름'],
                        "change": leader['등락률_수치']
                    }
        
        # 2. 족보 연결
        for index, row in df.iterrows():
            theme = row['테마']
            if theme in theme_leaders:
                leader_info = theme_leaders[theme]
                
                if row['이름'] == leader_info['name']:
                    df.at[index, '관련_대장주'] = "👑본인(대장)"
                    if df.at[index, '등급'] == 'NORMAL':
                         df.at[index, '등급'] = "🔥주도주(급등)"
                else:
                    df.at[index, '관련_대장주'] = f"{leader_info['name']} (+{leader_info['change']:.1f}%)"
                    if row['등급'] == 'NORMAL': 
                        df.at[index, '등급'] = "🔗후발주"

        # --- 출력 ---
        
        # 1. 트렌드 대시보드
        st.markdown("## 📊 오늘 시장의 주도 테마 TOP 3")
        if theme_leaders:
            cols = st.columns(3)
            # 가장 핫한 대장주 순으로 정렬
            sorted_themes = sorted(theme_leaders.items(), key=lambda x: x[1]['change'], reverse=True)[:3]
            for idx, (t, info) in enumerate(sorted_themes):
                with cols[idx]:
                    st.metric(f"🔥 {t} 대장", info['name'], f"+{info['change']:.1f}%")
        else:
            st.info("확실한 대장주가 보이지 않습니다.")
            
        st.divider()

        # 2. 최종 리스트 (모바일 최적화 표)
        st.subheader("📋 전체 발굴 리스트")
        
        df_show = df[df['등급'] != 'NORMAL'].copy()
        
        if not df_show.empty:
            # 정렬: 매집 -> 주도 -> 후발 -> 응축 -> 전환
            grade_order = {"💎매집VIP": 0, "🔥주도주(급등)": 1, "🔗후발주": 2, "⚡응축대기": 3, "📈추세전환": 4}
            df_show["우선순위"] = df_show["등급"].map(grade_order).fillna(5)
            df_show = df_show.sort_values("우선순위").drop(columns=["우선순위"])
            
            st.dataframe(
                df_show[["등급", "테마", "관련_대장주", "이름", "현재가", "등락률", "호재"]],
                use_container_width=True,
                height=600
            )
            st.caption("※ **[🔗후발주]**는 같은 테마 대장주가 급등할 때 따라갈 가능성이 높습니다.")
        else:
            st.warning("조건에 맞는 종목이 없습니다.")

    else:
        st.warning("데이터 없음")
