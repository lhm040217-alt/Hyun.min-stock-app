import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="Tenbagger V19 (Live)", layout="wide")
st.title("👑 텐배거 V19 (생존신호 확인용)")
st.markdown("""
**"멈춘 게 아닙니다. 일하는 중입니다."**
* **실시간 로그:** 현재 분석 중인 종목을 화면에 표시합니다.
* **전수조사:** 입력한 범위(0~3000 등)를 끝까지 파헤칩니다.
* **기능 포함:** VIP 분류, 재무제표, 대형주 제외 모두 포함.
""")

# --- 데이터 로딩 (내장 리스트 + 나스닥) ---
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
st.sidebar.header("🛠 설정 패널")

market_type = st.sidebar.radio(
    "1. 분석할 시장",
    ["나스닥 (NASDAQ)", "코스닥 (KOSDAQ)"]
)

# 데이터 로딩
@st.cache_data
def load_data(m_type):
    if "나스닥" in m_type:
        try:
            return fdr.StockListing('NASDAQ'), "FULL"
        except:
            return pd.DataFrame(), "ERROR"
    else:
        data = [{'Code': code, 'Name': f"종목_{code}"} for code in KOSDAQ_EMERGENCY_LIST]
        return pd.DataFrame(data), "BUILTIN"

try:
    full_list, list_type = load_data(market_type)
    total_len = len(full_list)
    
    if list_type == "FULL":
        st.sidebar.success(f"✅ 목록 로딩 완료: {total_len}개")
        st.sidebar.markdown("---")
        st.sidebar.subheader("2. 검사 범위 입력 (제한 없음)")
        
        c1, c2 = st.sidebar.columns(2)
        start_idx = c1.number_input("시작 번호", 0, total_len-1, 0)
        end_idx = c2.number_input("끝 번호", 1, total_len, min(100, total_len)) 
        # (테스트를 위해 기본값은 100으로 뒀으나, 3000 입력하면 3000개 다 돌아갑니다)
        
    else:
        st.sidebar.info(f"✅ 코스닥 내장 리스트: {total_len}개")
        start_idx, end_idx = 0, total_len

except Exception:
    st.error("데이터 로딩 중 치명적 오류")
    st.stop()

st.sidebar.markdown("---")
vip_cap_limit = st.sidebar.number_input("VIP 시총 상한선 (억/백만달러)", value=5000)

# --- 분석 로직 ---
def analyze_stock_v19(ticker, name, country):
    try:
        stock = yf.Ticker(ticker)
        
        # 1. 차트 (60일)
        df = stock.history(period="60d")
        if len(df) < 20: return None
        if df['Volume'].iloc[-1] == 0: return None

        close = df['Close']
        volume = df['Volume']
        curr_price = close.iloc[-1]

        # 2. 시가총액
        try:
            mkt_cap = stock.fast_info['market_cap']
        except:
            mkt_cap = 0
            
        # 3. 대형주 필터
        if country == "KR":
            mkt_cap_calc = mkt_cap / 100000000 
        else:
            mkt_cap_calc = mkt_cap / 1000000
            
        if mkt_cap_calc > vip_cap_limit: return None
        if mkt_cap_calc == 0: return None

        # 4. 기술적 지표
        vol_avg = volume.iloc[-20:-1].mean()
        if vol_avg == 0: return None
        vol_ratio = volume.iloc[-1] / vol_avg
        price_change = (curr_price - close.iloc[-5]) / close.iloc[-5] * 100

        # 5. 재무 정보 (성장률 등)
        try:
            info = stock.info
            rev_growth = info.get('revenueGrowth', 0)
            profit_margin = info.get('profitMargins', 0)
            real_name = info.get('longName', name)
        except:
            rev_growth = 0
            profit_margin = 0
            real_name = name

        # 6. 등급 판정
        grade = "FAIL"
        reasons = []
        
        is_vol_explode = vol_ratio >= 3.0
        is_rising = price_change >= 5.0

        if is_vol_explode and is_rising:
            grade = "VIP"
            reasons.append(f"★거래량폭발({vol_ratio:.1f}배)")
        elif (vol_ratio >= 2.0 and price_change >= 3.0) or (price_change >= 10.0):
            grade = "HOT"
            reasons.append("급등세")
            
        if grade == "FAIL": return None

        # 출력 포맷
        if country == "KR":
            code_pure = ticker.replace(".KQ", "").replace(".KS", "")
            news_link = f"https://m.stock.naver.com/item/main.nhn?code={code_pure}#/news/0"
            mkt_str = f"{mkt_cap_calc:.0f}억"
        else:
            news_link = f"https://finance.yahoo.com/quote/{ticker}/news"
            mkt_str = f"${mkt_cap_calc:.1f}M"
            
        growth_str = f"{rev_growth*100:.1f}%" if rev_growth else "-"
        margin_str = f"{profit_margin*100:.1f}%" if profit_margin else "-"

        return {
            "등급": grade,
            "이름": real_name,
            "코드": ticker,
            "현재가": f"{curr_price:,.0f}" if country=="KR" else f"${curr_price:.2f}",
            "등락률": f"{price_change:.1f}%",
            "거래량": f"{vol_ratio:.1f}배",
            "시총": mkt_str,
            "성장률": growth_str,
            "이익률": margin_str,
            "이유": ", ".join(reasons),
            "뉴스": news_link
        }
    except:
        return None

# --- 실행 버튼 및 로그창 ---
if st.button(f"🚀 {start_idx}번 ~ {end_idx}번 분석 시작"):
    
    target_slice = full_list.iloc[start_idx:end_idx]
    total_target = len(target_slice)
    
    vip_list = []
    hot_list = []
    
    # 여기가 생존신호 보내는 곳
    st.info(f"총 {total_target}개 종목 스캔을 시작합니다. 화면이 움직이는지 확인하세요.")
    
    progress_bar = st.progress(0)
    status_text = st.empty() # 실시간 로그창
    
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
            
        # [중요] 실시간으로 무슨 종목 보는지 찍어줌
        status_text.text(f"[{i+1}/{total_target}] 검색중... {ticker} ({name})")
        
        res = analyze_stock_v19(ticker, name, country)
        
        if res:
            if res['등급'] == "VIP":
                vip_list.append(res)
            else:
                hot_list.append(res)
        
        progress_bar.progress((i + 1) / total_target)

    status_text.success("분석이 끝났습니다! 결과를 확인하세요.")
    progress_bar.empty()
    
    # --- 결과 출력 ---
    st.markdown(f"## 💎 텐배거 VIP 후보 ({len(vip_list)}개)")
    if vip_list:
        for item in vip_list:
            with st.error(f"💎 {item['이름']} ({item['코드']})"):
                c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 1])
                c1.write(f"💰 {item['현재가']} ({item['등락률']})")
                c1.write(f"⚖️ {item['시총']}")
                c2.write(f"🔥 {item['거래량']}")
                c2.caption(item['이유'])
                c3.write(f"성장: {item['성장률']}")
                c3.write(f"이익: {item['이익률']}")
                c4.markdown(f"[⚡뉴스]({item['뉴스']})")
    else:
        st.info("조건에 맞는 VIP 종목이 없습니다.")

    st.divider()

    st.markdown(f"### 🔥 일반 급등주 ({len(hot_list)}개)")
    if hot_list:
        df_hot = pd.DataFrame(hot_list)
        st.dataframe(
            df_hot[["이름", "코드", "현재가", "등락률", "거래량", "시총", "성장률", "이익률"]],
            use_container_width=True
        )
    else:
        st.write("발견된 급등주 없음")
