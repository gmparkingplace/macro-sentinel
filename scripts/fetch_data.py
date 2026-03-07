"""
Macro Sentinel - Data Fetcher v2
FRED API + yfinance + Fear & Greed Index
"""

import os
import json
import datetime
import yfinance as yf
import requests

# ─────────────────────────────────────────
# 설정
# ─────────────────────────────────────────
FRED_API_KEY = os.environ.get("FRED_API_KEY")
TODAY = datetime.date.today().isoformat()
OUTPUT_PATH = "data/market_data.json"

def fred(series_id):
    """FRED API에서 최신값 가져오기"""
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

def yf_price(ticker):
    """yfinance로 종가 + 52주 위치 가져오기"""
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
    """섹터 ETF 4주 누적 등락률 계산"""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1mo")
        if hist.empty or len(hist) < 2:
            return {"close": None, "change_pct": None, "change_4w": None, "pct_52w": None}
        close     = round(float(hist["Close"].iloc[-1]), 2)
        prev      = round(float(hist["Close"].iloc[-2]), 2)
        start_4w  = round(float(hist["Close"].iloc[0]), 2)
        chg_1d    = round((close - prev) / prev * 100, 2)
        chg_4w    = round((close - start_4w) / start_4w * 100, 2)
        hist_1y   = t.history(period="1y")
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

def fetch_fear_greed(vix_value, hy_value):
    try:
        # None 또는 잘못된 타입 방어를 위해 명시적 float 형변환 추가
        vix = float(vix_value) if vix_value is not None else 20.0
        hy = float(hy_value) if hy_value is not None else 4.0

        vix_score = max(0, min(100, int((30 - vix) / 30 * 100)))
        hy_score  = max(0, min(100, int((6 - hy)  / 6  * 100)))
        
        score = int(vix_score * 0.6 + hy_score * 0.4)
        
        if score >= 75: rating = "Extreme Greed"
        elif score >= 55: rating = "Greed"
        elif score >= 45: rating = "Neutral"
        elif score >= 25: rating = "Fear"
        else: rating = "Extreme Fear"
        
        print(f"Fear & Greed 계산 완료: {score} ({rating})")
        return {"score": score, "rating": rating}
        
    except Exception as e:
        print(f"Fear & Greed 연산 오류: {e}")
        # 오류 발생 시 null 대신 중립(Neutral) 기본값 반환하여 프론트엔드 에러 방지
        return {"score": 50, "rating": "Neutral"}

# ─────────────────────────────────────────
# 메인 수집 로직
# ─────────────────────────────────────────
def fetch_all():
    print(f"[{TODAY}] 데이터 수집 시작...")
    data = {
        "date": TODAY,
        "indices": {}, "rates": {}, "spreads": {},
        "fx": {}, "commodities": {}, "liquidity": {},
        "sectors": {}, "macro": {}, "sentiment": {}
    }

    # ── 지수 ──────────────────────────────
    print("지수 수집 중...")
    data["indices"]["sp500"]     = yf_price("^GSPC")
    data["indices"]["nasdaq100"] = yf_price("^NDX")
    data["indices"]["russell"]   = yf_price("^RUT")
    data["indices"]["vix"]       = yf_price("^VIX")

    # ── 섹터 ETF (4주 누적 포함) ──────────
    print("섹터 ETF 수집 중...")
    sectors = {
        "XLK": "tech", "XLF": "financials", "XLE": "energy",
        "XLU": "utilities", "XLV": "healthcare", "XLY": "consumer_disc",
        "XLI": "industrials", "XLB": "materials"
    }
    for ticker, name in sectors.items():
        data["sectors"][name] = yf_sector_4w(ticker)

    # ── 금리 (FRED) ───────────────────────
    print("금리 수집 중...")
    data["rates"]["us2y"]    = fred("DGS2")
    data["rates"]["us10y"]   = fred("DGS10")
    data["rates"]["tips10y"] = fred("DFII10")

    # ── 스프레드 (FRED) ───────────────────
    print("스프레드 수집 중...")
    data["spreads"]["us2s10s"]  = fred("T10Y2Y")
    data["spreads"]["hy_spread"]= fred("BAMLH0A0HYM2")

    # ── 유동성 (FRED) ─────────────────────
    print("유동성 수집 중...")
    data["liquidity"]["fed_bs"] = fred("WALCL")
    data["liquidity"]["rrp"]    = fred("RRPONTSYD")
    data["liquidity"]["m2"]     = fred("M2SL")

    # ── 매크로 경제 지표 (FRED) ───────────
    print("매크로 지표 수집 중...")
    data["macro"]["cpi_yoy"]      = fred("CPIAUCSL")   # CPI (전년비 계산용)
    data["macro"]["core_cpi"]     = fred("CPILFESL")   # Core CPI
    data["macro"]["unemployment"] = fred("UNRATE")     # 실업률
    data["macro"]["pce"]          = fred("PCEPI")      # PCE
    data["macro"]["gdp_growth"]   = fred("A191RL1Q225SBEA")  # GDP 성장률

    # ── 환율 ──────────────────────────────
    print("환율 수집 중...")
    data["fx"]["dxy"]    = yf_price("DX-Y.NYB")
    data["fx"]["usdkrw"] = yf_price("KRW=X")
    data["fx"]["usdjpy"] = yf_price("JPY=X")
    data["fx"]["eurusd"] = yf_price("EURUSD=X")

    # ── 원자재 ────────────────────────────
    print("원자재 수집 중...")
    data["commodities"]["wti"]  = yf_price("CL=F")
    data["commodities"]["gold"] = yf_price("GC=F")

    # ── Fear & Greed ──────────────────────
    print("Fear & Greed 수집 중...")
    vix_val = data["indices"]["vix"]["close"]
    hy_val  = data["spreads"]["hy_spread"]["value"]
    data["sentiment"]["fear_greed"] = fetch_fear_greed(vix_val, hy_val)

    # ── 저장 ──────────────────────────────
    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ 데이터 저장 완료: {OUTPUT_PATH}")
    return data

if __name__ == "__main__":
    fetch_all()
