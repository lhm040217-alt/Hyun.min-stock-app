import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta

# --- 페이지 설정 ---
st.set_page_config(page_title="Tenbagger Hunter V7", layout="wide")
st.title("🚀 텐배거 헌터 V7 (Unlimited US)")
st.caption("미국 주식 가격 제한 해제 / 거래량 & 모멘텀 집중 분석")

# --- 사이드바 설정 ---
st.sidebar.header("사냥 설정")
scan_days = st.sidebar.slider("분석 기간 (일)", 20, 60, 40)
us_scan_count = st.sidebar.slider("미국 스캔 개수 (속도 조절)", 50, 300, 100) 
# 설명: 가격 제한 없이 나스닥 상위 종목부터 훑습니다.

# --- [1] 한국 코스닥 '끼' 있는 종목 리스트 (변동성 위주) ---
KR_SPICY_STOCKS = {
    # [AI / 온디바이스 / 로봇]
    "제주반도체": "080220.KQ", "가온칩스": "393500.KQ", "오픈엣지테크놀로지": "394280.KQ",
    "퀄리타스반도체": "432720.KQ", "칩스앤미디어": "094360.KQ", "고영": "098460.KQ",
    "레인보우로보틱스": "277810.KQ", "이랜시스": "264850.KQ", "에스피지": "058610.KQ",
    
    # [바이오 / 신약]
    "알테오젠": "196170.KQ", "HLB": "028300.KQ", "레고켐바이오": "141080.KQ",
    "삼천당제약": "000250.KQ", "에이비엘바이오": "298380.KQ", "지아이이노베이션": "358570.KQ",

    # [에너지 / 소재 / 기타 급등]
    "금양": "001570.KS", "캠시에스": "050110.KQ", "이수페타시스": "007660.KS",
    "제이앤티씨": "204270.KQ", "대주전자재료": "078600.KQ", "윤성에프앤씨": "372170.KQ"
}

# --- 분석 함수 ---
def analyze_stock(name, ticker, country):
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=scan_days)
        
        # 데이터 받기 (yf 사용)
        df = yf.download(ticker, start=start_date, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if len(df) < 15: return None

        close = df['Close']
        volume = df['Volume']
        curr_price = close.iloc[-1]

        # [변경점] 미국 주식 가격 제한 삭제함. (비싸도 OK)

        # 조건 1: 거래량 분석 (평소보다 2배 이상인가?)
        vol_recent = volume.iloc[-1]
        vol_avg = volume.iloc[-20:-1].mean()
        
        if vol_avg == 0: return None
        vol_ratio = vol_recent / vol_avg
        
        # 조건 2: 단기 추세 (5일 전보다 올랐는가?)
        price_change = (curr_price - close.iloc[-5]) / close.iloc[-5] * 100
        
        score = 0
        reasons = []

        # 채점 기준 (가격 상관없이 '힘'을 본다)
        if vol_ratio >= 3.0: 
            score += 40
            reasons.append(f"거래량폭발({vol_ratio:.1f}배)")
        elif vol_ratio >= 1.5:
            score += 20
            reasons.append("수급유입")
            
        if price_change >= 10.0:
            score += 40
            reasons.append(f"급등중({price_change:.1f}%)")
        elif price_change >= 5.0:
            score += 20
            reasons.append("상승세")
            
        # 정배열 (장기 상승 추세)
        ma20 = close.rolling(window=20).mean().iloc[-1]
        if curr_price > ma20:
            score += 20
            reasons.append("추세좋음")

        if score < 40: return None # 기준 미달 탈락

        # 뉴스 링크
        if country == "KR":
            pure_code = ticker.split('.')[0]
            news_link = f"https://m.stock.naver.com/item/main.nhn?code={pure_code}#/news/0"
        else:
            news_link = f"https://finance.yahoo.com/quote/{ticker}/news"

        return {
            "이름": name,
            "코드": ticker,
            "현재가": f"{curr_price:,.0f}" if country=="KR" else f"${curr_price:.2f}",
            "점수": score,
            "이유": ", ".join(reasons),
            "뉴스": news_link
        }
    except:
        return None

# --- 메인 실행 ---
if st.button("🔥 글로벌 텐배거 발굴 시작"):
    results = []
    bar = st.progress(0)
    
    # 1. 한국 주식 (엄선된 종목)
    st.write("🇰🇷 한국 급등 유망주 스캔 중...")
    for i, (name, ticker) in enumerate(KR_SPICY_STOCKS.items()):
        res = analyze_stock(name, ticker, "KR")
        if res: results.append(res)
        bar.progress((i + 1) / 100)

    # 2. 미국 주식 (가격 제한 없이 나스닥 스캔)
    st.write(f"🇺🇸 나스닥 상위 {us_scan_count}개 종목 정밀 분석 중...")
    try:
        # 나스닥 리스트 가져오기
        nasdaq_list = fdr.StockListing('NASDAQ')
        # 거래량 많은 순서 등으로 정렬하면 좋지만, 여기선 리스트 순서대로 스캔 (랜덤성 위해 sample 사용 가능)
        candidates = nasdaq_list.head(us_scan_count)
        
        for i, row in candidates.iterrows():
            ticker = row['Symbol']
            res = analyze_stock(ticker, ticker, "US")
            if res: results.append(res)
            
            # 진행바 업데이트
            prog = 0.3 + (i / us_scan_count * 0.7)
            if prog > 1.0: prog = 1.0
            bar.progress(prog)
            
    except Exception as e:
        st.error(f"미국 데이터 스캔 중 오류: {e}")

    bar.empty()

    # 결과 보여주기
    if results:
        df_res = pd.DataFrame(results).sort_values(by="점수", ascending=False)
        st.success(f"💎 총 {len(df_res)}개의 강력한 신호 포착!")
        
        for _, row in df_res.iterrows():
            with st.container():
                c1, c2 = st.columns([3, 1])
                c1.subheader(f"{row['이름']} ({row['코드']})")
                c1.write(f"💰 {row['현재가']} | {row['이유']}")
                c2.metric("점수", f"{row['점수']}점")
                c2.markdown(f"[⚡뉴스확인]({row['뉴스']})")
                st.divider()
    else:
        st.warning("현재 급등 조건을 만족하는 종목이 없습니다.")
