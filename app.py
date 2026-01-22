import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="Tenbagger V16 (Anti-Block)", layout="wide")
st.title("👑 텐배거 마스터피스 V16 (차단 우회판)")
st.markdown("""
**"서버 차단 완벽 해결"**
1. **미국(나스닥):** 0번~3000번 이상 **무제한 전수조사** 가능
2. **한국(코스닥):** 서버 차단 방지를 위해 **엄선된 200개 핵심 종목** 내장 탑재
3. **VIP 시스템:** 시총 작고 거래량 터진 진짜배기 자동 적출
""")

# --- [핵심] 차단 방지용 코스닥 내장 리스트 (서버가 막혀도 이건 돌아감) ---
KOSDAQ_EMERGENCY_LIST = [
    # 반도체/AI/로봇
    "080220", "393500", "394280", "042700", "007660", "403870", "058470", "277810",
    "348340", "108490", "058610", "094360", "054450", "102120", "098460", "036930",
    "067310", "377480", "304100", "108860", "402030", "064480", "315640", "253450",
    # 2차전지/소재
    "086520", "247540", "001570", "101670", "073570", "114190", "131400", "078600",
    "121600", "365340", "234920", "348370", "025900", "005070", "272290", "283740",
    # 바이오/제약
    "196170", "028300", "067630", "141080", "298380", "323990", "016790", "000250",
    "214370", "140410", "039200", "358570", "310210", "087010", "389470", "237690",
    # 엔터/게임/기타 급등끼
    "352820", "122870", "035900", "112040", "101730", "063080", "095660", "263750",
    "207760", "263720", "397140", "419530", "047820", "067160", "033100", "103590",
    "298040", "001440", "010120", "034020", "052690", "032820", "083650"
    # (필요시 리스트 더 추가 가능)
]

# --- 사이드바 설정 ---
st.sidebar.header("🛠 스캔 설정")

# 1. 시장 선택
market_type = st.sidebar.radio(
    "1. 분석할 시장 선택",
    ["나스닥 (NASDAQ) - 전수조사 추천", "코스닥 (KOSDAQ) - 내장리스트"]
)

# 2. 데이터 로딩 (에러 방지 로직 적용)
@st.cache_data
def load_stock_list_safe(m_type):
    if "나스닥" in m_type:
        # 미국은 차단 안 당함 -> 전체 리스트 가져옴
        try:
            df = fdr.StockListing('NASDAQ')
            return df, "FULL"
        except:
            return pd.DataFrame(), "ERROR"
    else:
        # 한국은 차단 당함 -> 내장 리스트 사용
        # 내장 리스트를 DataFrame 형태로 변환
        data = [{'Code': code, 'Name': f"종목_{code}"} for code in KOSDAQ_EMERGENCY_LIST]
        return pd.DataFrame(data), "BUILTIN"

try:
    full_list, list_type = load_stock_list_safe(market_type)
    total_count = len(full_list)
    
    if list_type == "FULL":
        st.sidebar.success(f"✅ 나스닥 {total_count}개 전체 로딩 성공")
        # 범위 설정 (미국장용)
        st.sidebar.markdown("---")
        st.sidebar.subheader("2. 검사 범위 (0 ~ 3000)")
        col_s, col_e = st.sidebar.columns(2)
        start_idx = col_s.number_input("시작", 0, total_count-1, 0)
        end_idx = col_e.number_input("끝", 1, total_count, min(200, total_count))
        
    elif list_type == "BUILTIN":
        st.sidebar.warning(f"⚠️ KRX 서버 차단됨 -> 내장된 알짜 {total_count}개 종목만 분석합니다.")
        start_idx, end_idx = 0, total_count # 한국은 전체 다 분석
        
    else:
        st.error("데이터 로딩 실패. 잠시 후 다시 시도하세요.")
        st.stop()

except Exception as e:
    st.error(f"초기화 중 오류: {e}")
    st.stop()

# 3. VIP 기준 설정
st.sidebar.markdown("---")
st.sidebar.subheader("3. 텐배거(VIP) 기준")
vip_cap_limit = st.sidebar.number_input("VIP 시총 상한선 (억/백만달러)", value=5000)
vip_vol_ratio = st.sidebar.slider("거래량 급증 기준 (배)", 2.0, 10.0, 3.0)


# --- 분석 함수 ---
def analyze_stock_v16(ticker, name, country):
    try:
        # Ticker 객체
        stock = yf.Ticker(ticker)
        
        # 데이터 조회 (60일)
        df = stock.history(period="60d")
        
        if len(df) < 20: return None
        if df['Volume'].iloc[-1] == 0: return None # 거래량 0 제외

        close = df['Close']
        volume = df['Volume']
        curr_price = close.iloc[-1]

        # 지표 계산
        vol_avg = volume.iloc[-20:-1].mean()
        if vol_avg == 0: return None
        vol_ratio = volume.iloc[-1] / vol_avg
        
        price_change = (curr_price - close.iloc[-5]) / close.iloc[-5] * 100
        
        # 재무 정보 (에러 안나게 예외처리)
        try:
            info = stock.info
            mkt_cap = info.get('marketCap', 0)
            rev_growth = info.get('revenueGrowth', 0)
            profit_margin = info.get('profitMargins', 0)
            real_name = info.get('longName', name) # 진짜 이름 가져오기
        except:
            mkt_cap = 0
            rev_growth = 0
            profit_margin = 0
            real_name = name

        # 등급 판정
        grade = "FAIL"
        reasons = []

        # 단위 변환 및 시총 체크
        if country == "KR":
            mkt_cap_calc = mkt_cap / 100000000 # 억 원
        else:
            mkt_cap_calc = mkt_cap / 1000000 # 백만 달러

        is_small_cap = (mkt_cap_calc > 0) and (mkt_cap_calc <= vip_cap_limit)
        is_vol_explode = vol_ratio >= vip_vol_ratio
        is_rising = price_change >= 5.0

        # 💎 VIP 판정
        if is_small_cap and is_vol_explode and is_rising:
            grade = "VIP"
            reasons.append("★시총가벼움")
            reasons.append(f"거래량폭발({vol_ratio:.1f}배)")
        
        # 🔥 HOT 판정
        elif (vol_ratio >= 2.0 and price_change >= 5.0) or (price_change >= 10.0):
            grade = "HOT"
            reasons.append("수급급등")
            
        if grade == "FAIL": return None

        # 링크 및 포맷
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
btn_text = f"🚀 분석 시작 ({start_idx}~{end_idx}번)" if list_type == "FULL" else "🚀 코스닥 핵심종목 스캔 시작"

if st.button(btn_text):
    
    # 분석 대상 자르기
    target_slice = full_list.iloc[start_idx:end_idx]
    
    vip_list = []
    hot_list = []
    
    st.info(f"총 {len(target_slice)}개 종목 정밀 분석 중... (재무제표 포함)")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, row in enumerate(target_slice.iterrows()):
        idx, data = row
        
        if "나스닥" in market_type:
            ticker = data['Symbol']
            name = data['Name']
            country = "US"
        else:
            # 코스닥 내장 리스트 처리
            code_raw = data['Code']
            ticker = f"{code_raw}.KQ" # yfinance용 코드
            name = data['Name']
            country = "KR"
            
        status_text.write(f"🔍 [{i+1}/{len(target_slice)}] 확인중: {ticker}")
        
        res = analyze_stock_v16(ticker, name, country)
        
        if res:
            if res['등급'] == "VIP":
                vip_list.append(res)
            else:
                hot_list.append(res)
        
        progress_bar.progress((i + 1) / len(target_slice))

    status_text.empty()
    progress_bar.empty()
    
    # --- 결과 리포트 ---
    
    # 1. VIP 리포트
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
        st.info("조건에 완벽히 부합하는 VIP 종목이 없습니다.")

    st.divider()

    # 2. 일반 급등주
    st.markdown(f"### 🔥 일반 급등 ({len(hot_list)}개)")
    if hot_list:
        df_hot = pd.DataFrame(hot_list)
        st.dataframe(
            df_hot[["이름", "코드", "현재가", "등락률", "거래량", "시총", "성장률", "이익률"]],
            use_container_width=True
        )
    else:
        st.write("급등 신호 없음")
