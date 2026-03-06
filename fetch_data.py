"""
Macro Sentinel - Data Fetcher
FRED API + yfinance로 장 마감 후 데이터 수집
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
    """FRED API에서 최신값 1개 가져오기"""
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 5,  # 최근 5개 중 유효값 사용
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        obs = r.json().get("observations", [])
        # 빈값(".") 제외하고 첫 번째 유효값 반환
        for o in obs:
            if o["value"] != ".":
                return {"value": float(o["value"]), "date": o["date"]}
    except Exception as e:
        print(f"FRED 오류 ({series_id}): {e}")
    return {"value": None, "date": None}

def yf_price(ticker):
    """yfinance로 종가 가져오기"""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if hist.empty:
            return {"close": None, "prev_close": None, "change_pct": None}
        close = round(float(hist["Close"].iloc[-1]), 2)
        prev  = round(float(hist["Close"].iloc[-2]), 2) if len(hist) >= 2 else close
        chg   = round((close - prev) / prev * 100, 2)
        # 52주 위치 계산
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

# ─────────────────────────────────────────
# 메인 수집 로직
# ─────────────────────────────────────────
def fetch_all():
    print(f"[{TODAY}] 데이터 수집 시작...")
    data = {"date": TODAY, "indices": {}, "rates": {}, "spreads": {}, "fx": {}, "commodities": {}, "liquidity": {}}

    # ── 지수 ──────────────────────────────
    print("지수 수집 중...")
    data["indices"]["sp500"]    = yf_price("^GSPC")
    data["indices"]["nasdaq100"]= yf_price("^NDX")
    data["indices"]["russell"]  = yf_price("^RUT")
    data["indices"]["vix"]      = yf_price("^VIX")

    # ── 섹터 ETF ──────────────────────────
    print("섹터 ETF 수집 중...")
    sectors = {"XLK":"tech","XLF":"financials","XLE":"energy",
               "XLU":"utilities","XLV":"healthcare","XLY":"consumer_disc",
               "XLI":"industrials","XLB":"materials"}
    data["sectors"] = {}
    for ticker, name in sectors.items():
        data["sectors"][name] = yf_price(ticker)

    # ── 금리 (FRED) ───────────────────────
    print("금리 수집 중...")
    data["rates"]["us2y"]       = fred("DGS2")
    data["rates"]["us10y"]      = fred("DGS10")
    data["rates"]["tips10y"]    = fred("DFII10")   # 실질금리

    # ── 스프레드 (FRED) ───────────────────
    print("스프레드 수집 중...")
    data["spreads"]["us2s10s"]  = fred("T10Y2Y")   # 2s10s (bp)
    data["spreads"]["hy_spread"]= fred("BAMLH0A0HYM2")  # HY 크레딧 스프레드

    # ── 유동성 (FRED) ─────────────────────
    print("유동성 수집 중...")
    data["liquidity"]["fed_bs"] = fred("WALCL")    # Fed 대차대조표 (백만달러)
    data["liquidity"]["rrp"]    = fred("RRPONTSYD") # RRP 잔액

    # ── 환율 ──────────────────────────────
    print("환율 수집 중...")
    data["fx"]["dxy"]           = yf_price("DX-Y.NYB")
    data["fx"]["usdkrw"]        = yf_price("KRW=X")
    data["fx"]["usdjpy"]        = yf_price("JPY=X")
    data["fx"]["eurusd"]        = yf_price("EURUSD=X")

    # ── 원자재 ────────────────────────────
    print("원자재 수집 중...")
    data["commodities"]["wti"]  = yf_price("CL=F")
    data["commodities"]["gold"] = yf_price("GC=F")

    # ── 저장 ──────────────────────────────
    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ 데이터 저장 완료: {OUTPUT_PATH}")
    return data

if __name__ == "__main__":
    fetch_all()