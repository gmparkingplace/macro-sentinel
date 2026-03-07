"""
Macro Sentinel - Data Fetcher v3
FRED API + yfinance + Fear&Greed(자체계산) + RSS 뉴스
"""

import os
import json
import datetime
import yfinance as yf
import requests

FRED_API_KEY = os.environ.get("FRED_API_KEY")
TODAY = datetime.date.today().isoformat()
OUTPUT_PATH = "data/market_data.json"

# ─────────────────────────────────────────
# FRED
# ─────────────────────────────────────────
def fred(series_id):
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 5,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        obs = r.json().get("observations", [])
        for o in obs:
            if o["value"] != ".":
                return {"value": float(o["value"]), "date": o["date"]}
    except Exception as e:
        print(f"FRED 오류 ({series_id}): {e}")
    return {"value": None, "date": None}

# ─────────────────────────────────────────
# yfinance
# ─────────────────────────────────────────
def yf_price(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if hist.empty:
            return {"close": None, "prev_close": None, "change_pct": None, "pct_52w": None}
        close = round(float(hist["Close"].iloc[-1]), 2)
        prev  = round(float(hist["Close"].iloc[-2]), 2) if len(hist) >= 2 else close
        chg   = round((close - prev) / prev * 100, 2)
        hist_1y = t.history(period="1y")
        if not hist_1y.empty:
            high_52 = float(hist_1y["High"].max())
            low_52  = float(hist_1y["Low"].min())
            pct_52  = round((close - low_52) / (high_52 - low_52) * 100, 1) if high_52 != low_52 else 50
        else:
            pct_52 = None
        return {"close": close, "prev_close": prev, "change_pct": chg, "pct_52w": pct_52}
    except Exception as e:
        print(f"yfinance 오류 ({ticker}): {e}")
        return {"close": None, "prev_close": None, "change_pct": None, "pct_52w": None}

def yf_sector_4w(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1mo")
        if hist.empty or len(hist) < 2:
            return {"close": None, "change_pct": None, "change_4w": None, "pct_52w": None}
        close    = round(float(hist["Close"].iloc[-1]), 2)
        prev     = round(float(hist["Close"].iloc[-2]), 2)
        start_4w = round(float(hist["Close"].iloc[0]), 2)
        chg_1d   = round((close - prev) / prev * 100, 2)
        chg_4w   = round((close - start_4w) / start_4w * 100, 2)
        hist_1y  = t.history(period="1y")
        if not hist_1y.empty:
            high_52 = float(hist_1y["High"].max())
            low_52  = float(hist_1y["Low"].min())
            pct_52  = round((close - low_52) / (high_52 - low_52) * 100, 1) if high_52 != low_52 else 50
        else:
            pct_52 = None
        return {"close": close, "change_pct": chg_1d, "change_4w": chg_4w, "pct_52w": pct_52}
    except Exception as e:
        print(f"섹터 4주 오류 ({ticker}): {e}")
        return {"close": None, "change_pct": None, "change_4w": None, "pct_52w": None}

# ─────────────────────────────────────────
# Fear & Greed — VIX + HY 자체계산 (CNN API 대체)
# ─────────────────────────────────────────
def fetch_fear_greed(vix_value=None, hy_value=None):
    """
    VIX 60% + HY 스프레드 40% 가중 자체계산
    외부 API 의존 없이 안정적으로 동작
    """
    try:
        # VIX 직접 가져오기 (인자로 없으면)
        if vix_value is None:
            vix_hist = yf.Ticker("^VIX").history(period="5d")
            vix_value = float(vix_hist["Close"].iloc[-1]) if not vix_hist.empty else None

        # HY 직접 가져오기 (인자로 없으면)
        if hy_value is None:
            hy_data = fred("BAMLH0A0HYM2")
            hy_value = hy_data["value"]

        if vix_value is None:
            return {"score": None, "rating": None}

        # VIX → 점수 (VIX 10=100점, VIX 40=0점)
        vix_score = max(0.0, min(100.0, 100.0 - (vix_value - 10.0) * (100.0 / 30.0)))

        # HY 스프레드 → 점수 (2%=100점, 10%=0점)
        if hy_value is not None:
            hy_score = max(0.0, min(100.0, 100.0 - (hy_value - 2.0) * (100.0 / 8.0)))
        else:
            hy_score = vix_score  # HY 없으면 VIX만 사용

        score = round(vix_score * 0.6 + hy_score * 0.4, 1)

        if score >= 75:   rating = "Extreme Greed"
        elif score >= 55: rating = "Greed"
        elif score >= 45: rating = "Neutral"
        elif score >= 25: rating = "Fear"
        else:             rating = "Extreme Fear"

        print(f"Fear & Greed 계산값: {score} ({rating})  |  VIX={vix_value:.1f}, HY={hy_value}")
        return {"score": score, "rating": rating}

    except Exception as e:
        print(f"Fear & Greed 오류: {e}")
        return {"score": None, "rating": None}

# ─────────────────────────────────────────
# 뉴스 헤드라인 (RSS)
# ─────────────────────────────────────────
def fetch_news_headlines():
    """Reuters / MarketWatch RSS 헤드라인 수집"""
    headlines = []
    feeds = [
        ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
        ("MarketWatch Top", "https://feeds.marketwatch.com/marketwatch/topstories"),
        ("Reuters Markets",  "https://feeds.reuters.com/reuters/UKmarkets"),
    ]
    for source, url in feeds:
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            # 간단한 XML 파싱 (feedparser 없이)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(r.content)
            items = root.findall(".//item")
            for item in items[:4]:
                title_el = item.find("title")
                if title_el is not None and title_el.text:
                    headlines.append(f"[{source}] {title_el.text.strip()}")
        except Exception as e:
            print(f"뉴스 오류 ({source}): {e}")

    result = headlines[:12]
    print(f"수집된 헤드라인: {len(result)}개")
    return result

# ─────────────────────────────────────────
# 메인
# ─────────────────────────────────────────
def fetch_all():
    print(f"[{TODAY}] 데이터 수집 시작...")
    data = {
        "date": TODAY,
        "indices": {}, "rates": {}, "spreads": {},
        "fx": {}, "commodities": {}, "liquidity": {},
        "sectors": {}, "macro": {}, "sentiment": {},
        "news": []
    }

    print("지수 수집 중...")
    data["indices"]["sp500"]     = yf_price("^GSPC")
    data["indices"]["nasdaq100"] = yf_price("^NDX")
    data["indices"]["russell"]   = yf_price("^RUT")
    data["indices"]["vix"]       = yf_price("^VIX")

    print("섹터 ETF 수집 중...")
    sectors = {
        "XLK": "tech", "XLF": "financials", "XLE": "energy",
        "XLU": "utilities", "XLV": "healthcare", "XLY": "consumer_disc",
        "XLI": "industrials", "XLB": "materials"
    }
    for ticker, name in sectors.items():
        data["sectors"][name] = yf_sector_4w(ticker)

    print("금리 수집 중...")
    data["rates"]["us2y"]    = fred("DGS2")
    data["rates"]["us10y"]   = fred("DGS10")
    data["rates"]["tips10y"] = fred("DFII10")

    print("스프레드 수집 중...")
    data["spreads"]["us2s10s"]   = fred("T10Y2Y")
    data["spreads"]["hy_spread"] = fred("BAMLH0A0HYM2")

    print("유동성 수집 중...")
    data["liquidity"]["fed_bs"] = fred("WALCL")
    data["liquidity"]["rrp"]    = fred("RRPONTSYD")
    data["liquidity"]["m2"]     = fred("M2SL")

    print("매크로 지표 수집 중...")
    data["macro"]["cpi_yoy"]      = fred("CPIAUCSL")
    data["macro"]["core_cpi"]     = fred("CPILFESL")
    data["macro"]["unemployment"] = fred("UNRATE")
    data["macro"]["pce"]          = fred("PCEPI")
    data["macro"]["gdp_growth"]   = fred("A191RL1Q225SBEA")

    print("환율 수집 중...")
    data["fx"]["dxy"]    = yf_price("DX-Y.NYB")
    data["fx"]["usdkrw"] = yf_price("KRW=X")
    data["fx"]["usdjpy"] = yf_price("JPY=X")
    data["fx"]["eurusd"] = yf_price("EURUSD=X")

    print("원자재 수집 중...")
    data["commodities"]["wti"]  = yf_price("CL=F")
    data["commodities"]["gold"] = yf_price("GC=F")

    # Fear & Greed: 이미 수집한 VIX + HY 재활용
    print("Fear & Greed 계산 중...")
    vix_val = data["indices"]["vix"]["close"]
    hy_val  = data["spreads"]["hy_spread"]["value"]
    data["sentiment"]["fear_greed"] = fetch_fear_greed(vix_val, hy_val)

    print("뉴스 헤드라인 수집 중...")
    data["news"] = fetch_news_headlines()

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ 데이터 저장 완료: {OUTPUT_PATH}")
    return data

if __name__ == "__main__":
    fetch_all()
