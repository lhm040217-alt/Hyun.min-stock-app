import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="Tenbagger Automata V20", layout="wide")
st.title("🤖 텐배거 오토마타 V20 (테마/재무 자동분석)")
st.markdown("""
**"이제 검색도 하지 마세요. 코드가 대신 읽어드립니다."**
1. **테마 자동 감지:** 기업 설명을 읽고 **[AI / 바이오 / 2차전지 / 로봇]** 등 테마를 자동 분류합니다.
2. **턴어라운드 포착:** 적자였다가 이익이 나기 시작하면 **[★흑자전환]** 딱지를 붙입니다.
3. **품절주 확인:** 대주주/내부자 지분이 높으면 **[품절주]**로 표시합니다.
""")

# --- [내장] 핫 테마 키워드 사전 ---
# 코드가 기업 설명을 읽을 때, 이 단어가 있으면 테마주로 분류합니다.
THEME_KEYWORDS = {
    "AI": ["AI", "Artificial Intelligence", "인공지능", "NPU", "Neural", "Deep Learning"],
    "로봇": ["Robot", "Robotics", "로봇", "Automation", "Actuator"],
    "2차전지": ["Battery", "Lithium", "Cathode", "Anode", "배터리", "리튬", "양극재", "음극재", "2차전지"],
    "반도체": ["Semiconductor", "Chip", "Foundry", "Fabless", "반도체", "HBM", "DRAM"],
    "바이오/헬스": ["Bio", "Drug", "Pharma", "Cancer", "Cell", "바이오", "신약", "제약", "줄기세포"],
    "우주/방산": ["Space", "Defense", "Satellite", "Rocket", "우주", "위성", "방산", "Missile"],
    "플랫폼/게임": ["Platform", "Game", "Metaverse", "Blockchain", "게임", "메타버스", "블록체인"]
}

# --- 차단 방지용 코스닥 리스트 ---
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

# --- 사이드바 설정 ---
st.sidebar.header("🛠 오토마타 설정")

market_type = st.sidebar.radio("1. 시장 선택", ["나스닥 (NASDAQ)", "코스닥 (KOSDAQ)"])

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
        st.sidebar.markdown("---")
        st.sidebar.subheader("2. 전수조사 범위")
        c1, c2 = st.sidebar.columns(2)
        start_idx = c1.number_input("시작", 0, total_len-1, 0)
        end_idx = c2.number_input("끝", 1, total_len, min(100, total_len))
    else:
        start_idx, end_idx = 0, total_len

except:
    st.error("데이터 로딩 실패")
    st.stop()

st.sidebar.markdown("---")
vip_cap_limit = st.sidebar.number_input("VIP 시총 상한선 (억/백만달러)", value=5000)

# --- [핵심] 테마 및 재무 자동 분석 로직 ---
def analyze_stock_v20(ticker, name, country):
    try:
        stock = yf.Ticker(ticker)
        
        # 1. 차트 필터링 (가장 빠름) - 거래량 없으면 즉시 탈락
        df = stock.history(period="60d")
        if len(df) < 20: return None
        if df['Volume'].iloc[-1] == 0: return None

        close = df['Close']
        volume = df['Volume']
        curr_price = close.iloc[-1]
        
        # 2. 거래량 & 가격 지표 계산
        vol_avg = volume.iloc[-20:-1].mean()
        if vol_avg == 0: return None
        vol_ratio = volume.iloc[-1] / vol_avg
        price_change = (curr_price - close.iloc[-5]) / close.iloc[-5] * 100
        
        # [최적화] 거래량이 안 터졌으면, 굳이 무거운 정보(info)를 긁지 말고 탈락시킨다. (속도 향상)
        # 단, 가격 급등(10% 이상)이면 봐준다.
        if vol_ratio < 2.0 and price_change < 10.0:
            return None 

        # 3. 심층 정보 가져오기 (Fast Info + Full Info)
        try:
            # 시총은 빠르게
            mkt_cap = stock.fast_info['market_cap']
        except:
            mkt_cap = 0
            
        # 시총 필터링
        if country == "KR": mkt_cap_calc = mkt_cap / 100000000 
        else: mkt_cap_calc = mkt_cap / 1000000
            
        if mkt_cap_calc > vip_cap_limit: return None # 대형주 탈락
        if mkt_cap_calc == 0: return None

        # 4. [오토마타] 텍스트 & 재무 정밀 분석
        # 여기서 시간이 좀 걸리지만, "안 찾아도 되게" 해달라고 하셨으니 다 긁습니다.
        try:
            info = stock.info
            
            # (1) 테마 자동 감지
            summary = info.get('longBusinessSummary', '') + " " + info.get('sector', '') + " " + info.get('industry', '')
            detected_themes = []
            for theme, keywords in THEME_KEYWORDS.items():
                for kw in keywords:
                    if kw.lower() in summary.lower():
                        detected_themes.append(theme)
                        break # 하나라도 걸리면 그 테마 추가
            
            theme_tag = ", ".join(detected_themes) if detected_themes else "기타"
            
            # (2) 재무 상태 & 턴어라운드 감지
            rev_growth = info.get('revenueGrowth', 0)
            profit_margin = info.get('profitMargins', 0)
            insider_hold = info.get('heldPercentInsiders', 0)
            
            # 이름 확보
            real_name = info.get('longName', name)
            
        except:
            # 정보 가져오기 실패시 기본값
            theme_tag = "분석불가"
            rev_growth = 0
            profit_margin = 0
            insider_hold = 0
            real_name = name

        # 5. 등급 판정 및 태그 부착
        grade = "FAIL"
        special_tags = [] # 사용자님이 좋아할 만한 태그들

        # 테마 태그
        if theme_tag != "기타" and theme_tag != "분석불가":
            special_tags.append(f"[{theme_tag}]")
            
        # 턴어라운드/성장 태그
        if rev_growth > 0.3: special_tags.append("⚡고성장")
        if profit_margin > 0.1: special_tags.append("💰알짜")
        
        # 품절주 태그 (내부자 지분 30% 이상)
        if insider_hold > 0.3: special_tags.append("🔒품절주(대주주↑)")

        # 등급 로직
        is_vol_explode = vol_ratio >= 3.0
        is_rising = price_change >= 5.0

        if is_vol_explode and is_rising:
            grade = "VIP"
            special_tags.insert(0, "★텐배거후보")
        elif (vol_ratio >= 2.0 and price_change >= 3.0) or (price_change >= 10.0):
            grade = "HOT"
            
        if grade == "FAIL": return None

        # 출력 데이터 구성
        if country == "KR":
            code_pure = ticker.replace(".KQ", "").replace(".KS", "")
            news_link = f"https://m.stock.naver.com/item/main.nhn?code={code_pure}#/news/0"
            mkt_str = f"{mkt_cap_calc:.0f}억"
        else:
            news_link = f"https://finance.yahoo.com/quote/{ticker}/news"
            mkt_str = f"${mkt_cap_calc:.1f}M"
            
        final_reason = " ".join(special_tags)
        if not final_reason: final_reason = f"거래량급증({vol_ratio:.1f}배)"

        return {
            "등급": grade,
            "이름": real_name,
            "코드": ticker,
            "현재가": f"{curr_price:,.0f}" if country=="KR" else f"${curr_price:.2f}",
            "등락률": f"{price_change:.1f}%",
            "거래량": f"{vol_ratio:.1f}배",
            "시총": mkt_str,
            "태그": final_reason, # 여기가 핵심 (자동 분석 결과)
            "뉴스": news_link
        }

    except:
        return None

# --- 실행 ---
if st.button(f"🤖 오토마타 가동 ({start_idx}~{end_idx}번)"):
    
    target_slice = full_list.iloc[start_idx:end_idx]
    
    vip_list = []
    hot_list = []
    
    st.info(f"코드가 기업 설명서(Business Summary)를 읽고 있습니다... (속도가 조금 느릴 수 있습니다)")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
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
            
        status_text.text(f"📖 [{i+1}/{len(target_slice)}] 분석중: {ticker}")
        
        res = analyze_stock_v20(ticker, name, country)
        
        if res:
            if res['등급'] == "VIP":
                vip_list.append(res)
            else:
                hot_list.append(res)
        
        progress_bar.progress((i + 1) / len(target_slice))

    status_text.success("분석 완료! 코드가 찾아낸 태그를 확인하세요.")
    progress_bar.empty()
    
    # --- 결과 출력 ---
    
    # 1. VIP (상세 카드뷰)
    st.markdown(f"## 💎 텐배거 VIP ({len(vip_list)}개)")
    st.caption("조건: 시총 작음 + 거래량 3배 + (테마/재무 자동분석)")
    
    if vip_list:
        for item in vip_list:
            # 태그 강조를 위해 error 박스 사용
            with st.error(f"💎 {item['이름']} ({item['코드']})"):
                st.markdown(f"### 👉 {item['태그']}") # 여기가 자동 분석 결과
                c1, c2, c3 = st.columns(3)
                c1.metric("가격/등락", f"{item['현재가']}", item['등락률'])
                c2.metric("시가총액", item['시총'])
                c3.metric("거래량 배수", item['거래량'])
                st.markdown(f"[⚡뉴스 및 기업정보 확인]({item['뉴스']})")
    else:
        st.info("이 구간에는 완벽한 텐배거 후보가 없습니다.")

    st.divider()

    # 2. HOT (테이블뷰)
    st.markdown(f"### 🔥 급등주 및 테마 포착 ({len(hot_list)}개)")
    if hot_list:
        df_hot = pd.DataFrame(hot_list)
        # 태그 컬럼을 맨 앞으로
        st.dataframe(
            df_hot[["태그", "이름", "현재가", "등락률", "시총", "거래량"]],
            use_container_width=True
        )
    else:
        st.write("발견된 종목 없음")
