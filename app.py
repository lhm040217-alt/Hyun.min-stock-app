import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="Tenbagger V18 (Unlimited)", layout="wide")
st.title("👑 텐배거 마스터피스 V18 (진짜 무제한)")
st.markdown("""
**"제한을 풀었습니다."**
* **범위 직접 입력:** 슬라이더를 없애고, 시작~끝 번호를 직접 입력합니다. (예: 0 ~ 3000)
* **전수조사:** 중간에 멈추지 않고 입력한 범위 전체를 훑습니다.
* **데이터 수정:** 시총 0원 문제 해결, 대형주 자동 제외
""")

# --- [차단 방지용] 코스닥 내장 리스트 ---
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
st.sidebar.header("🛠 스캔 범위 설정")

# 1. 시장 선택
market_type = st.sidebar.radio(
    "1. 분석할 시장",
    ["나스닥 (NASDAQ) - 전수조사", "코스닥 (KOSDAQ) - 핵심내장"]
)

# 2. 데이터 로딩
@st.cache_data
def load_data(m_type):
    if "나스닥" in m_type:
        try:
            return fdr.StockListing('NASDAQ'), "FULL"
        except:
            return pd.DataFrame(), "ERROR"
    else:
        # 코스닥은 내장 리스트 사용
        data = [{'Code': code, 'Name': f"종목_{code}"} for code in KOSDAQ_EMERGENCY_LIST]
        return pd.DataFrame(data), "BUILTIN"

try:
    full_list, list_type = load_data(market_type)
    total_len = len(full_list)
    
    if list_type == "FULL":
        st.sidebar.success(f"✅ 나스닥 전체 {total_len}개 로딩 완료")
        
        # [핵심 수정] 슬라이더 제거 -> 숫자 입력칸 생성
        st.sidebar.markdown("---")
        st.sidebar.subheader(f"2. 검사 범위 입력 (0 ~ {total_len})")
        st.sidebar.caption("원하는 만큼 숫자를 입력하세요. 제한 없습니다.")
        
        col1, col2 = st.sidebar.columns(2)
        # 시작 번호 (기본 0)
        start_idx = col1.number_input("시작 번호", min_value=0, max_value=total_len-1, value=0)
        # 끝 번호 (기본 1000, 최대 5000까지 입력 가능하게 품)
        end_idx = col2.number_input("끝 번호", min_value=1, max_value=total_len, value=min(1000, total_len))
        
    else:
        st.sidebar.info(f"✅ 코스닥 핵심 {total_len}개 (내장 리스트)")
        start_idx, end_idx = 0, total_len

except Exception as e:
    st.error("데이터 로딩 실패")
    st.stop()

# 3. VIP 기준
st.sidebar.markdown("---")
vip_cap_limit = st.sidebar.number_input("VIP 시총 상한선 (억/백만달러)", value=5000)

# --- 분석 로직 ---
def analyze_stock_v18(ticker, name, country):
    try:
        stock = yf.Ticker(ticker)
        
        # 1. 차트 데이터 (60일)
        df = stock.history(period="60d")
        if len(df) < 20: return None
        if df['Volume'].iloc[-1] == 0: return None

        close = df['Close']
        volume = df['Volume']
        curr_price = close.iloc[-1]

        # 2. 시가총액 (Fast Info 사용 - 0원 문제 해결)
        try:
            mkt_cap = stock.fast_info['market_cap']
        except:
            mkt_cap = 0
            
        # 3. 대형주 필터링
        if country == "KR":
            mkt_cap_calc = mkt_cap / 100000000 
        else:
            mkt_cap_calc = mkt_cap / 1000000
            
        # 설정한 시총보다 크면 통과 (결과 제외)
        if mkt_cap_calc > vip_cap_limit: return None
        if mkt_cap_calc == 0: return None # 데이터 오류 제외

        # 4. 기술적 지표
        vol_avg = volume.iloc[-20:-1].mean()
        if vol_avg == 0: return None
        vol_ratio = volume.iloc[-1] / vol_avg
        price_change = (curr_price - close.iloc[-5]) / close.iloc[-5] * 100

        # 5. 재무 정보 (보조)
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

# --- 실행 버튼 ---
if st.button(f"🚀 {start_idx}번 ~ {end_idx}번 전수조사 시작"):
    
    # 슬라이싱 (무조건 입력한 만큼 다 가져옴)
    target_slice = full_list.iloc[start_idx:end_idx]
    
    vip_list = []
    hot_list = []
    
    st.info(f"총 {len(target_slice)}개 종목을 하나도 빠짐없이 검사합니다. (시간이 소요됩니다)")
    
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
            
        status_text.write(f"🔍 [{i+1}/{len(target_slice)}] 분석 중... {ticker}")
        
        res = analyze_stock_v18(ticker, name, country)
        
        if res:
            if res['등급'] == "VIP":
                vip_list.append(res)
            else:
                hot_list.append(res)
        
        progress_bar.progress((i + 1) / len(target_slice))

    status_text.empty()
    progress_bar.empty()
    
    # --- 결과 출력 ---
    st.success("분석 완료!")

    # VIP
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
        st.info("이 구간에 VIP 조건(시총작고+급등)을 만족하는 종목이 없습니다.")

    st.divider()

    # HOT
    st.markdown(f"### 🔥 일반 급등주 ({len(hot_list)}개)")
    if hot_list:
        df_hot = pd.DataFrame(hot_list)
        st.dataframe(
            df_hot[["이름", "코드", "현재가", "등락률", "거래량", "시총", "성장률", "이익률"]],
            use_container_width=True
        )
    else:
        st.write("발견된 종목 없음")
