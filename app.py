import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd

# --- 페이지 설정 ---
st.set_page_config(page_title="Tenbagger V24 (Trend Caster)", layout="wide")
st.title("📊 텐배거 V24 (시장 트렌드 & 미래 예측)")
st.markdown("""
**"돈의 흐름을 읽어드립니다."**
1.  **현재 유행(Hot):** 지금 시장에서 가장 수익률이 좋은 섹터(테마)를 보여줍니다.
2.  **미래 유행(Next):** 세력이 몰래 매집 중인(VIP) 종목들이 **어떤 섹터에 몰려있는지** 분석합니다. (이게 핵심!)
3.  **모바일 최적화:** 깔끔한 표와 요약 리포트를 제공합니다.
""")

# --- [내장] 테마 키워드 사전 ---
THEME_KEYWORDS = {
    "AI/로봇": ["AI", "Artificial Intelligence", "Robot", "인공지능", "로봇", "Neural", "Deep Learning"],
    "2차전지": ["Battery", "Lithium", "Cathode", "배터리", "리튬", "양극재", "음극재", "전기차", "EV"],
    "반도체": ["Semiconductor", "Chip", "Foundry", "반도체", "HBM", "DRAM", "Memory", "System"],
    "바이오": ["Bio", "Drug", "Pharma", "Cancer", "바이오", "신약", "제약", "임상", "Cell"],
    "플랫폼/게임": ["Platform", "Game", "Metaverse", "Cloud", "게임", "메타버스", "소프트웨어", "SaaS"],
    "에너지/방산": ["Energy", "Defense", "Solar", "Wind", "방산", "에너지", "태양광", "Nuclear"],
    "화장품/소비": ["Cosmetic", "Food", "Retail", "화장품", "식품", "유통", "K-Beauty"],
}

# --- 코스닥 내장 리스트 ---
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

# --- 사이드바 ---
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
def analyze_stock_v24(ticker, name, country):
    try:
        stock = yf.Ticker(ticker)
        
        # 1. 차트 분석 (3개월)
        df = stock.history(period="3mo")
        if len(df) < 60: return None
        if df['Volume'].iloc[-1] == 0: return None

        close = df['Close']
        volume = df['Volume']
        curr_price = close.iloc[-1]

        # 2. 시가총액 필터
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
        
        # 볼린저/이평선
        ma5 = close.rolling(5).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        std = close.rolling(20).std().iloc[-1]
        upper_band = ma20 + (2 * std)
        lower_band = ma20 - (2 * std)
        band_width = (upper_band - lower_band) / ma20 

        # 4. [오토마타] 테마 분석
        theme_detected = "기타"
        try:
            info = stock.info
            summary = info.get('longBusinessSummary', '') + " " + info.get('industry', '') + " " + info.get('sector', '')
            
            for theme, keywords in THEME_KEYWORDS.items():
                for kw in keywords:
                    if kw.lower() in summary.lower():
                        theme_detected = theme
                        break
                if theme_detected != "기타": break
            
            real_name = info.get('longName', name)
        except:
            real_name = name

        # 5. 등급 판정
        grade = "FAIL"
        
        # VIP: 거래량 2배 + 가격 0~4% + 정배열
        if vol_ratio >= 2.0 and 0 <= price_change <= 4.0 and ma5 >= ma20:
            grade = "💎매집VIP"
        
        # READY: 밴드폭 좁음 + 정배열
        elif band_width <= 0.20 and ma5 >= ma20:
            grade = "⚡응축대기"

        # TURN: 추세 전환
        elif price_change > 0 and close.iloc[-1] > ma20 and vol_ratio > 1.5:
             grade = "📈추세전환"
        
        # (통계용) 일반 상승: 등급은 없어도 통계에는 잡히게
        elif price_change > 0:
            grade = "NORMAL"

        if grade == "FAIL": return None

        # 거래량 텍스트
        if vol_ratio >= 2.0: vol_str = f"폭발({vol_ratio:.1f}배)"
        else: vol_str = f"보통({vol_ratio:.1f}배)"

        return {
            "등급": grade,
            "테마": theme_detected,
            "이름": real_name,
            "현재가": f"{curr_price:,.0f}" if country=="KR" else f"${curr_price:.2f}",
            "등락률_수치": price_change,
            "등락률": f"{price_change:+.1f}%",
            "거래량": vol_str,
            "시총": f"{mkt_cap_calc:.0f}억" if country=="KR" else f"${mkt_cap_calc:.1f}M"
        }

    except:
        return None

# --- 실행 버튼 ---
if st.button(f"📊 트렌드 & 종목 분석 ({start_idx}~{end_idx})"):
    
    target_slice = full_list.iloc[start_idx:end_idx]
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    st.info("시장 트렌드를 읽고 있습니다... (테마 분류 중)")
    
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
        
        res = analyze_stock_v24(ticker, name, country)
        if res: results.append(res)
        
        progress_bar.progress((i + 1) / len(target_slice))

    status_text.empty()
    progress_bar.empty()
    
    if results:
        df = pd.DataFrame(results)
        
        # --- [NEW] 시장 트렌드 리포트 (대시보드) ---
        st.markdown("## 📊 시장 기상도 (Market Trend)")
        
        col_trend1, col_trend2 = st.columns(2)
        
        # 1. 현재 유행 (Hot Trend) - 등락률 평균이 높은 테마
        with col_trend1:
            st.subheader("🔥 현재 유행 (수익률 Top)")
            try:
                # 테마별 평균 등락률 계산
                trend_now = df[df['테마'] != '기타'].groupby('테마')['등락률_수치'].mean().sort_values(ascending=False).head(3)
                if not trend_now.empty:
                    for theme, avg_change in trend_now.items():
                        st.write(f"**{theme}**: 평균 **{avg_change:+.1f}%** 상승 중")
                else:
                    st.write("뚜렷한 주도 테마가 없습니다.")
            except:
                st.write("데이터 부족")

        # 2. 미래 유행 (Next Trend) - VIP(매집) 신호가 가장 많은 테마
        with col_trend2:
            st.subheader("🤫 다음 유행 (매집 집중)")
            try:
                # VIP 등급인 애들만 필터링해서 테마 카운트
                vip_df = df[df['등급'] == '💎매집VIP']
                if not vip_df.empty:
                    trend_future = vip_df[vip_df['테마'] != '기타']['테마'].value_counts().head(3)
                    if not trend_future.empty:
                        for theme, count in trend_future.items():
                            st.write(f"**{theme}**: **{count}개** 종목 매집 포착! (주목)")
                    else:
                        st.write("특정 테마에 매집이 집중되지 않았습니다.")
                else:
                    st.write("아직 뚜렷한 매집 세력이 안 보입니다.")
            except:
                st.write("분석 불가")
                
        st.divider()

        # --- 종목 리스트 출력 (중요도 순) ---
        st.subheader("📋 발굴 종목 리스트")
        
        # 등급 필터 (NORMAL은 통계용이라 리스트에선 뺌)
        df_show = df[df['등급'] != 'NORMAL'].copy()
        
        if not df_show.empty:
            grade_order = {"💎매집VIP": 0, "⚡응축대기": 1, "📈추세전환": 2}
            df_show["우선순위"] = df_show["등급"].map(grade_order)
            df_show = df_show.sort_values("우선순위").drop(columns=["우선순위"])
            
            st.dataframe(
                df_show[["등급", "테마", "이름", "현재가", "등락률", "거래량", "시총"]],
                use_container_width=True,
                height=500
            )
        else:
            st.info("통계 데이터는 확보했으나, VIP/급등 기준을 충족하는 종목은 없습니다.")

    else:
        st.warning("분석할 데이터가 없습니다.")
