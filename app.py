import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="Tenbagger Deep Dive V10", layout="wide")

st.title("🐢 텐배거 딥 다이브 V10 (정밀분석판)")
st.markdown("""
**"속도보다 깊이"**를 추구합니다. 
주가뿐만 아니라 **매출성장률, 영업이익률, 부채비율, ROE**를 전수 조사하여 
**'돈 잘 벌고 성장하는데 아직 싼 기업'**을 찾아냅니다.
""")

# --- 사이드바 설정 ---
st.sidebar.header("🛠 정밀 검사 설정")
scan_limit = st.sidebar.slider("분석할 종목 수 (많을수록 오래 걸림)", 30, 200, 50)
min_growth = st.sidebar.slider("최소 매출 성장률 (%)", 0, 50, 15)
max_debt = st.sidebar.slider("최대 부채 비율 (%)", 50, 500, 200)

# --- 한국 알짜 종목 리스트 (섹터별 대표 성장주 확장판) ---
KR_TARGETS = {
    # [반도체 소부장]
    "한미반도체": "042700.KS", "이수페타시스": "007660.KS", "HPSP": "403870.KQ",
    "리노공업": "058470.KQ", "가온칩스": "393500.KQ", "주성엔지니어링": "036930.KQ",
    "하나마이크론": "067310.KQ", "동진쎄미켐": "005290.KQ", "ISC": "095340.KQ",
    # [2차전지/소재]
    "에코프로비엠": "247540.KQ", "나노신소재": "121600.KQ", "대주전자재료": "078600.KQ",
    "윤성에프앤씨": "372170.KQ", "피엔티": "137400.KQ", "코스모신소재": "005070.KS",
    # [바이오/미용]
    "알테오젠": "196170.KQ", "클래시스": "214150.KQ", "휴젤": "145020.KQ",
    "파마리서치": "214450.KQ", "비올": "335890.KQ", "제이시스메디칼": "287410.KQ",
    "삼천당제약": "000250.KQ", "리가켐바이오": "141080.KQ",
    # [로봇/AI/SW]
    "레인보우로보틱스": "277810.KQ", "두산로보틱스": "454910.KS", "더존비즈온": "012510.KS",
    "한글과컴퓨터": "030520.KQ", "엠로": "058970.KQ"
}

# --- 데이터 포맷팅 ---
def format_value(val, unit, country):
    if val is None: return "-"
    if unit == "money":
        if country == "KR": return f"{val/100000000:.0f}억"
        else: return f"${val/1000000:.1f}M"
    if unit == "percent":
        return f"{val*100:.1f}%"
    return val

# --- 핵심: 딥 다이브 분석 함수 ---
def analyze_deep(name, ticker, country):
    try:
        # 1. 재무 데이터 가져오기 (시간 소요됨)
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # 데이터가 비어있으면 패스
        if not info: return None

        # 2. 핵심 지표 추출
        market_cap = info.get('marketCap', 0)      # 시가총액
        revenue_growth = info.get('revenueGrowth', 0) # 매출성장률 (YoY)
        profit_margins = info.get('profitMargins', 0) # 순이익률
        roe = info.get('returnOnEquity', 0)        # 자기자본이익률 (효율성)
        debt_to_equity = info.get('debtToEquity', 0) # 부채비율
        per = info.get('trailingPE', 0)            # 주가수익비율
        
        current_price = info.get('currentPrice', 0)
        target_price = info.get('targetMeanPrice', 0) # 증권사 목표가 평균

        # 3. 1차 필터링 (사용자 설정 기준)
        # 매출 성장이 너무 낮거나, 부채가 너무 많으면 탈락
        if revenue_growth < (min_growth / 100): return None
        if debt_to_equity > max_debt: return None
        if market_cap == 0: return None

        # 4. 차트 데이터 (최근 추세 확인용)
        hist = stock.history(period="1mo")
        if len(hist) < 5: return None
        
        price_change_1m = (hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0] * 100
        
        # 5. 점수 계산 (펀더멘털 점수)
        score = 0
        reasons = []

        # [성장성] 매출이 폭발적으로 느는가?
        if revenue_growth > 0.3: # 30% 이상 성장
            score += 30
            reasons.append("고성장(30%↑)")
        elif revenue_growth > 0.15:
            score += 15
            reasons.append("성장세")

        # [수익성] 돈을 잘 남기는가?
        if profit_margins > 0.2: # 마진율 20% 이상 (알짜)
            score += 20
            reasons.append("고마진(20%↑)")
        
        # [효율성] 자본 대비 돈을 잘 버는가? (ROE)
        if roe > 0.15:
            score += 20
            reasons.append("ROE우수")

        # [수급/추세] 주가가 오르고 있는가?
        if price_change_1m > 10:
            score += 15
            reasons.append("최근상승세")
            
        # [저평가] 목표가 대비 싼가?
        if target_price and current_price < target_price * 0.7:
            score += 15
            reasons.append("저평가(목표가대비)")

        # 뉴스 링크
        if country == "KR":
            code_only = ticker.split('.')[0]
            news_link = f"https://m.stock.naver.com/item/main.nhn?code={code_only}#/invest/financial"
        else:
            news_link = f"https://finance.yahoo.com/quote/{ticker}/financials"

        return {
            "종목명": name,
            "코드": ticker,
            "현재가": current_price,
            "점수": score,
            "시가총액": format_value(market_cap, "money", country),
            "매출성장률": format_value(revenue_growth, "percent", country),
            "영업이익률": format_value(profit_margins, "percent", country),
            "ROE": format_value(roe, "percent", country),
            "부채비율": f"{debt_to_equity:.0f}%" if debt_to_equity else "-",
            "PER": f"{per:.1f}배" if per else "-",
            "목표가": target_price if target_price else "-",
            "특이사항": ", ".join(reasons),
            "뉴스": news_link,
            "국가": country
        }

    except Exception as e:
        return None

# --- 메인 실행 ---
if st.button("🐢 정밀 분석 시작 (시간이 걸립니다)"):
    results = []
    
    # 1. 한국 주식 분석
    st.info(f"🇰🇷 한국 유망주 {len(KR_TARGETS)}개 재무제표 뜯어보는 중...")
    bar_kr = st.progress(0)
    for i, (name, ticker) in enumerate(KR_TARGETS.items()):
        data = analyze_deep(name, ticker, "KR")
        if data: results.append(data)
        bar_kr.progress((i + 1) / len(KR_TARGETS))
    bar_kr.empty()

    # 2. 미국 주식 분석 (나스닥 상위)
    st.info(f"🇺🇸 나스닥/S&P500 상위 {scan_limit}개 종목 정밀 검사 중... (약 {scan_limit*1.5}초 소요)")
    bar_us = st.progress(0)
    
    try:
        # 미국 리스트 가져오기 (S&P500 + NASDAQ 섞어서)
        us_tickers = fdr.StockListing('NASDAQ').head(scan_limit)['Symbol'].tolist()
        
        for i, ticker in enumerate(us_tickers):
            data = analyze_deep(ticker, ticker, "US")
            if data: results.append(data)
            bar_us.progress((i + 1) / len(us_tickers))
            
    except Exception as e:
        st.error(f"미국 데이터 로딩 중 에러: {e}")
        
    bar_us.empty()

    # --- 결과 리포트 출력 ---
    if results:
        df = pd.DataFrame(results)
        df = df.sort_values(by="점수", ascending=False)
        
        st.success(f"✅ 분석 완료! 총 {len(df)}개의 알짜 기업을 찾았습니다.")

        # 1. 엑셀 스타일 요약표
        st.subheader("📊 재무제표 기반 랭킹 (Top 20)")
        
        # 보여줄 컬럼만 선택
        display_cols = ["종목명", "현재가", "점수", "시가총액", "매출성장률", "영업이익률", "ROE", "부채비율", "특이사항"]
        st.dataframe(
            df[display_cols].head(20).style.background_gradient(subset=["점수"], cmap="YlGn"),
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("---")

        # 2. 상세 리포트 (확장형)
        st.subheader("📑 종목별 상세 리포트")
        
        for i, row in df.head(10).iterrows(): # 상위 10개만 디테일하게
            with st.expander(f"🏆 {row['종목명']} ({row['점수']}점) - 자세히 보기"):
                c1, c2, c3 = st.columns(3)
                
                with c1:
                    st.markdown("**💰 가격 & 가치**")
                    st.write(f"현재가: **{row['현재가']:,.0f}**" if row['국가']=="KR" else f"현재가: **${row['현재가']:.2f}**")
                    st.write(f"시가총액: {row['시가총액']}")
                    st.write(f"PER (주가수익비율): {row['PER']}")
                    st.write(f"증권사 목표가: {row['목표가']}")
                
                with c2:
                    st.markdown("**📈 성장성 & 수익성**")
                    # 색상 강조
                    growth_color = "green" if "30%" in str(row['매출성장률']) else "black"
                    st.markdown(f"매출성장률: :{growth_color}[{row['매출성장률']}]")
                    st.write(f"영업이익률: {row['영업이익률']}")
                    st.write(f"ROE (자기자본이익률): {row['ROE']}")
                
                with c3:
                    st.markdown("**🛡️ 재무 건전성**")
                    debt_color = "red" if int(row['부채비율'].replace('%','')) > 200 else "blue"
                    st.markdown(f"부채비율: :{debt_color}[{row['부채비율']}]")
                    st.markdown(f"[🔗 네이버/야후 재무정보 확인]({row['뉴스']})")
                    st.info(f"💡 핵심 포인트: {row['특이사항']}")

    else:
        st.warning("설정하신 조건(성장률 등)이 너무 까다로워서 통과한 기업이 없습니다. 사이드바에서 조건을 조금 낮춰보세요.")
