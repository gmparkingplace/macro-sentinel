"""
Macro Sentinel - Data Fetcher v4
FRED API + yfinance + Fear & Greed + CBOE Skew + 경제 캘린더 + 히스토리 누적
"""

import os
import json
import datetime
import yfinance as yf
import requests

FRED_API_KEY = os.environ.get("FRED_API_KEY")
TODAY        = datetime.date.today().isoformat()
OUTPUT_PATH  = "data/market_data.json"
HISTORY_PATH = "data/history.json"

# ─────────────────────────────────────────
# 경제 캘린더 (2026년 하드코딩 + 자동 필터)
# ─────────────────────────────────────────
ECONOMIC_CALENDAR = [
    # ── FOMC (2026) ──────────────────────
    {"date": "2026-01-28", "event": "FOMC 금리 결정",       "category": "fed",    "impact": "high"},
    {"date": "2026-01-29", "event": "FOMC 기자회견",         "category": "fed",    "impact": "high"},
    {"date": "2026-03-18", "event": "FOMC 금리 결정",       "category": "fed",    "impact": "high"},
    {"date": "2026-03-19", "event": "FOMC 기자회견",         "category": "fed",    "impact": "high"},
    {"date": "2026-05-06", "event": "FOMC 금리 결정",       "category": "fed",    "impact": "high"},
    {"date": "2026-05-07", "event": "FOMC 기자회견",         "category": "fed",    "impact": "high"},
    {"date": "2026-06-17", "event": "FOMC 금리 결정",       "category": "fed",    "impact": "high"},
    {"date": "2026-06-18", "event": "FOMC 기자회견",         "category": "fed",    "impact": "high"},
    {"date": "2026-07-29", "event": "FOMC 금리 결정",       "category": "fed",    "impact": "high"},
    {"date": "2026-07-30", "event": "FOMC 기자회견",         "category": "fed",    "impact": "high"},
    {"date": "2026-09-16", "event": "FOMC 금리 결정",       "category": "fed",    "impact": "high"},
    {"date": "2026-09-17", "event": "FOMC 기자회견",         "category": "fed",    "impact": "high"},
    {"date": "2026-11-04", "event": "FOMC 금리 결정",       "category": "fed",    "impact": "high"},
    {"date": "2026-11-05", "event": "FOMC 기자회견",         "category": "fed",    "impact": "high"},
    {"date": "2026-12-16", "event": "FOMC 금리 결정",       "category": "fed",    "impact": "high"},
    {"date": "2026-12-17", "event": "FOMC 기자회견",         "category": "fed",    "impact": "high"},

    # ── CPI (2026, 매월 중순) ─────────────
    {"date": "2026-01-14", "event": "CPI 발표 (12월)",      "category": "cpi",    "impact": "high"},
    {"date": "2026-02-11", "event": "CPI 발표 (1월)",       "category": "cpi",    "impact": "high"},
    {"date": "2026-03-11", "event": "CPI 발표 (2월)",       "category": "cpi",    "impact": "high"},
    {"date": "2026-04-10", "event": "CPI 발표 (3월)",       "category": "cpi",    "impact": "high"},
    {"date": "2026-05-13", "event": "CPI 발표 (4월)",       "category": "cpi",    "impact": "high"},
    {"date": "2026-06-10", "event": "CPI 발표 (5월)",       "category": "cpi",    "impact": "high"},
    {"date": "2026-07-14", "event": "CPI 발표 (6월)",       "category": "cpi",    "impact": "high"},
    {"date": "2026-08-12", "event": "CPI 발표 (7월)",       "category": "cpi",    "impact": "high"},
    {"date": "2026-09-11", "event": "CPI 발표 (8월)",       "category": "cpi",    "impact": "high"},
    {"date": "2026-10-13", "event": "CPI 발표 (9월)",       "category": "cpi",    "impact": "high"},
    {"date": "2026-11-12", "event": "CPI 발표 (10월)",      "category": "cpi",    "impact": "high"},
    {"date": "2026-12-10", "event": "CPI 발표 (11월)",      "category": "cpi",    "impact": "high"},

    # ── PCE (매월 말) ─────────────────────
    {"date": "2026-01-30", "event": "PCE 발표 (12월)",      "category": "pce",    "impact": "high"},
    {"date": "2026-02-27", "event": "PCE 발표 (1월)",       "category": "pce",    "impact": "high"},
    {"date": "2026-03-27", "event": "PCE 발표 (2월)",       "category": "pce",    "impact": "high"},
    {"date": "2026-04-30", "event": "PCE 발표 (3월)",       "category": "pce",    "impact": "high"},
    {"date": "2026-05-29", "event": "PCE 발표 (4월)",       "category": "pce",    "impact": "high"},
    {"date": "2026-06-26", "event": "PCE 발표 (5월)",       "category": "pce",    "impact": "high"},
    {"date": "2026-07-31", "event": "PCE 발표 (6월)",       "category": "pce",    "impact": "high"},
    {"date": "2026-08-28", "event": "PCE 발표 (7월)",       "category": "pce",    "impact": "high"},
    {"date": "2026-09-25", "event": "PCE 발표 (8월)",       "category": "pce",    "impact": "high"},
    {"date": "2026-10-30", "event": "PCE 발표 (9월)",       "category": "pce",    "impact": "high"},
    {"date": "2026-11-25", "event": "PCE 발표 (10월)",      "category": "pce",    "impact": "high"},
    {"date": "2026-12-23", "event": "PCE 발표 (11월)",      "category": "pce",    "impact": "high"},

    # ── 고용보고서 (매월 첫째 금요일) ──────
    {"date": "2026-01-09", "event": "고용보고서 (12월)",    "category": "jobs",   "impact": "high"},
    {"date": "2026-02-06", "event": "고용보고서 (1월)",     "category": "jobs",   "impact": "high"},
    {"date": "2026-03-06", "event": "고용보고서 (2월)",     "category": "jobs",   "impact": "high"},
    {"date": "2026-04-03", "event": "고용보고서 (3월)",     "category": "jobs",   "impact": "high"},
    {"date": "2026-05-08", "event": "고용보고서 (4월)",     "category": "jobs",   "impact": "high"},
    {"date": "2026-06-05", "event": "고용보고서 (5월)",     "category": "jobs",   "impact": "high"},
    {"date": "2026-07-10", "event": "고용보고서 (6월)",     "category": "jobs",   "impact": "high"},
    {"date": "2026-08-07", "event": "고용보고서 (7월)",     "category": "jobs",   "impact": "high"},
    {"date": "2026-09-04", "event": "고용보고서 (8월)",     "category": "jobs",   "impact": "high"},
    {"date": "2026-10-02", "event": "고용보고서 (9월)",     "category": "jobs",   "impact": "high"},
    {"date": "2026-11-06", "event": "고용보고서 (10월)",    "category": "jobs",   "impact": "high"},
    {"date": "2026-12-04", "event": "고용보고서 (11월)",    "category": "jobs",   "impact": "high"},

    # ── GDP (분기별) ──────────────────────
    {"date": "2026-01-30", "event": "GDP 속보치 (Q4 2025)", "category": "gdp",    "impact": "high"},
    {"date": "2026-04-29", "event": "GDP 속보치 (Q1 2026)", "category": "gdp",    "impact": "high"},
    {"date": "2026-07-30", "event": "GDP 속보치 (Q2 2026)", "category": "gdp",    "impact": "high"},
    {"date": "2026-10-29", "event": "GDP 속보치 (Q3 2026)", "category": "gdp",    "impact": "high"},
]

def get_upcoming_events(days_ahead=42):
    """오늘부터 days_ahead일 이내 예정 이벤트 반환 (최대 10개)"""
    today = datetime.date.today()
    cutoff = today + datetime.timedelta(days=days_ahead)
    upcoming = []
    for ev in ECONOMIC_CALENDAR:
        ev_date = datetime.date.fromisoformat(ev["date"])
        if today <= ev_date <= cutoff:
            upcoming.append(ev)
    upcoming.sort(key=lambda x: x["date"])
    return upcoming[:10]

# ─────────────────────────────────────────
# 히스토리 누적
# ─────────────────────────────────────────
def update_history(data, scores):
    """history.json에 오늘 스냅샷을 추가 (최근 60일 유지)"""
    try:
        if os.path.exists(HISTORY_PATH):
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                history = json.load(f)
        else:
            history = []

        # 오늘 날짜가 이미 있으면 업데이트, 없으면 추가
        snapshot = {
            "date":      TODAY,
            "verdict":   scores.get("verdict", "WAIT"),
            "vix":       data["indices"]["vix"]["close"],
            "sp500":     data["indices"]["sp500"]["close"],
            "fg_score":  data["sentiment"]["fear_greed"]["score"],
            "skew":      data["sentiment"].get("skew", {}).get("close"),
            "hy_spread": data["spreads"]["hy_spread"]["value"],
            "us10y":     data["rates"]["us10y"]["value"],
            "wti":       data["commodities"]["wti"]["close"],
            "ratio":     scores.get("ratio"),
        }

        # 같은 날짜 항목 제거 후 추가
        history = [h for h in history if h["date"] != TODAY]
        history.append(snapshot)

        # 날짜순 정렬 후 최근 60일만 유지
        history.sort(key=lambda x: x["date"])
        history = history[-60:]

        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        print(f"✅ 히스토리 업데이트 완료: {len(history)}일치 누적")
    except Exception as e:
        print(f"히스토리 업데이트 오류: {e}")

# ─────────────────────────────────────────
# 기존 함수들
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
        valid = [o for o in obs if o["value"] != "."]
        if not valid:
            return {"value": None, "date": None}
        latest = valid[0]
        result = {"value": float(latest["value"]), "date": latest["date"]}
        # change_pct 계산 (전일 대비)
        if len(valid) >= 2:
            prev = float(valid[1]["value"])
            result["change_pct"] = round((result["value"] - prev) / prev * 100, 2) if prev != 0 else None
            result["prev_value"] = prev
        else:
            result["change_pct"] = None
            result["prev_value"] = None
        return result
    except Exception as e:
        print(f"FRED 오류 ({series_id}): {e}")
    return {"value": None, "date": None, "change_pct": None, "prev_value": None}

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

def fetch_fear_greed(vix_value, hy_value):
    try:
        vix = float(vix_value) if vix_value is not None else 20.0
        hy  = float(hy_value)  if hy_value  is not None else 4.0
        vix_score = max(0, min(100, int((30 - vix) / 30 * 100)))
        hy_score  = max(0, min(100, int((6  - hy)  / 6  * 100)))
        score = int(vix_score * 0.6 + hy_score * 0.4)
        if score >= 75:   rating = "Extreme Greed"
        elif score >= 55: rating = "Greed"
        elif score >= 45: rating = "Neutral"
        elif score >= 25: rating = "Fear"
        else:             rating = "Extreme Fear"
        print(f"Fear & Greed 계산 완료: {score} ({rating})")
        return {"score": score, "rating": rating}
    except Exception as e:
        print(f"Fear & Greed 연산 오류: {e}")
        return {"score": 50, "rating": "Neutral"}

def fetch_skew(vix_value):
    try:
        t = yf.Ticker("^SKEW")
        hist = t.history(period="5d")
        if hist.empty:
            print("Skew 데이터 없음")
            return {"close": None, "change_pct": None, "signal": None,
                    "combo_signal": None, "combo_label": None}
        close = round(float(hist["Close"].iloc[-1]), 2)
        prev  = round(float(hist["Close"].iloc[-2]), 2) if len(hist) >= 2 else close
        chg   = round((close - prev) / prev * 100, 2)
        if close >= 150:   signal = "red"
        elif close >= 130: signal = "yellow"
        else:              signal = "green"
        vix = float(vix_value) if vix_value is not None else 20.0
        vix_high  = vix >= 22
        skew_high = close >= 130
        if vix_high and skew_high:
            combo_signal = "red";    combo_label = "총체적위기(VIX↑+Skew↑)"
        elif not vix_high and skew_high:
            combo_signal = "orange"; combo_label = "숨겨진경고(VIX↓+Skew↑)"
        elif vix_high and not skew_high:
            combo_signal = "yellow"; combo_label = "단기패닉(VIX↑+Skew↓)"
        else:
            combo_signal = "green";  combo_label = "안정(VIX↓+Skew↓)"
        print(f"Skew 수집 완료: {close} (신호: {signal}, 조합: {combo_label})")
        return {"close": close, "change_pct": chg, "signal": signal,
                "combo_signal": combo_signal, "combo_label": combo_label}
    except Exception as e:
        print(f"Skew 오류: {e}")
        return {"close": None, "change_pct": None, "signal": None,
                "combo_signal": None, "combo_label": None}

def fetch_news():
    """
    Reuters + MarketWatch RSS에서 헤드라인 + URL 수집
    반환: [{"title": "...", "url": "...", "source": "...", "published": "..."}, ...]
    """
    import xml.etree.ElementTree as ET

    feeds = [
        {"name": "Reuters",      "url": "https://feeds.reuters.com/reuters/businessNews"},
        {"name": "Reuters Mkts", "url": "https://feeds.reuters.com/reuters/UKmarkets"},
        {"name": "MarketWatch",  "url": "https://feeds.marketwatch.com/marketwatch/topstories"},
        {"name": "CNBC",         "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"},
    ]

    KEYWORDS = [
        "fed", "rate", "inflation", "cpi", "gdp", "recession", "market",
        "stocks", "nasdaq", "s&p", "treasury", "yield", "dollar", "oil",
        "tariff", "trade", "china", "economy", "jobs", "unemployment",
        "금리", "인플레", "경기", "주식", "시장"
    ]

    results = []
    seen_titles = set()

    for feed in feeds:
        try:
            r = requests.get(feed["url"], timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            root = ET.fromstring(r.content)
            items = root.findall(".//item")
            for item in items[:20]:
                title = (item.findtext("title") or "").strip()
                url   = (item.findtext("link") or "").strip()
                pub   = (item.findtext("pubDate") or "").strip()

                if not title or not url:
                    continue
                if title in seen_titles:
                    continue

                # 매크로 관련 키워드 필터
                title_lower = title.lower()
                if not any(kw in title_lower for kw in KEYWORDS):
                    continue

                seen_titles.add(title)
                results.append({
                    "title":     title,
                    "url":       url,
                    "source":    feed["name"],
                    "published": pub,
                })

                if len(results) >= 20:
                    break
        except Exception as e:
            print(f"뉴스 RSS 오류 ({feed['name']}): {e}")

        if len(results) >= 20:
            break

    print(f"뉴스 수집 완료: {len(results)}건 → 제목 번역 중...")

    # Groq으로 제목 일괄 번역
    try:
        from groq import Groq
        groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        titles_en = [r["title"] for r in results[:15]]
        titles_block = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles_en))
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a financial news translator. Translate each English headline to natural Korean. Return ONLY a numbered list in the same order, one line per headline. No extra text. CRITICAL: Never use Chinese characters (漢字) or Japanese characters. Use only pure Korean (한글) and Arabic numerals."},
                {"role": "user",   "content": titles_block}
            ],
            temperature=0.1,
            max_tokens=800,
        )
        lines = resp.choices[0].message.content.strip().split("\n")
        for i, line in enumerate(lines):
            if i >= len(results):
                break
            # "1. 번역문" 형태에서 번역문만 추출
            translated = line.strip()
            if translated and translated[0].isdigit():
                translated = translated.split(".", 1)[-1].strip()
            if translated:
                results[i]["title_ko"] = translated
    except Exception as e:
        print(f"번역 오류: {e}")

    # title_ko 없으면 원문 그대로, 한자 포함 시 원문으로 대체
    for r in results:
        if "title_ko" not in r or not r["title_ko"]:
            r["title_ko"] = r["title"]
        else:
            # 한자(CJK 통합 한자) 포함 여부 확인 → 포함 시 원문으로 대체
            import unicodedata
            has_kanji = any(
                unicodedata.category(c) == 'Lo' and '\u4e00' <= c <= '\u9fff'
                for c in r["title_ko"]
            )
            if has_kanji:
                print(f"한자 감지, 원문으로 대체: {r['title_ko'][:30]}...")
                r["title_ko"] = r["title"]

    print(f"번역 완료")
    return results[:15]



def fetch_all():
    print(f"[{TODAY}] 데이터 수집 시작...")
    data = {
        "date": TODAY,
        "indices": {}, "rates": {}, "spreads": {},
        "fx": {}, "commodities": {}, "liquidity": {},
        "sectors": {}, "macro": {}, "sentiment": {},
        "calendar": [], "news": []
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
    data["spreads"]["us5s30s"]   = fred("T20Y5Y")      # 5s20y 장단기 스프레드 (5s30s 대체)
    data["spreads"]["hy_spread"] = fred("BAMLH0A0HYM2")
    data["spreads"]["fra_ois"]   = fred("OBFR")        # SOFR (달러 유동성 대리 지표)

    print("유동성 수집 중...")
    data["liquidity"]["fed_bs"] = fred("WALCL")
    data["liquidity"]["rrp"]    = fred("RRPONTSYD")
    data["liquidity"]["m2"]     = fred("M2SL")

    print("매크로 지표 수집 중...")
    data["macro"]["cpi_yoy"]      = fred("CPALTT01USM657N")  # CPI 전년비 % (OECD/FRED)
    data["macro"]["core_cpi"]     = fred("CPGRLE01USM657N")  # Core CPI 전년비 %
    data["macro"]["unemployment"] = fred("UNRATE")
    data["macro"]["pce"]          = fred("PCEPI")            # PCE 지수 (YoY는 별도 계산)
    data["macro"]["gdp_growth"]   = fred("A191RL1Q225SBEA")
    data["macro"]["ism_mfg"]      = fred("UMCSENT")          # 미시간대 소비자신뢰지수
    data["macro"]["ism_svc"]      = fred("CSCICP03USM665S")  # OECD 소비자신뢰지수

    print("환율 수집 중...")
    data["fx"]["dxy"]    = fred("DTWEXBGS")  # Trade Weighted USD Index (FRED)
    data["fx"]["usdkrw"] = yf_price("KRW=X")
    data["fx"]["usdjpy"] = yf_price("JPY=X")
    data["fx"]["eurusd"] = yf_price("EURUSD=X")

    print("원자재 수집 중...")
    data["commodities"]["wti"]    = yf_price("CL=F")
    data["commodities"]["gold"]   = yf_price("GC=F")
    data["commodities"]["copper"] = yf_price("HG=F")  # 구리 (경기 선행)

    print("Fear & Greed 수집 중...")
    vix_val = data["indices"]["vix"]["close"]
    hy_val  = data["spreads"]["hy_spread"]["value"]
    data["sentiment"]["fear_greed"] = fetch_fear_greed(vix_val, hy_val)

    print("Skew Index 수집 중...")
    data["sentiment"]["skew"] = fetch_skew(vix_val)

    print("경제 캘린더 생성 중...")
    data["calendar"] = get_upcoming_events(days_ahead=42)
    print(f"  향후 42일 이내 이벤트: {len(data['calendar'])}개")

    print("뉴스 헤드라인 수집 중...")
    data["news"] = fetch_news()

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 데이터 저장 완료: {OUTPUT_PATH}")

    return data

def update_history_from_report():
    """generate_report.py 실행 후 호출 — report.json에서 스코어 읽어 히스토리 업데이트"""
    try:
        with open("data/market_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        with open("data/report.json", "r", encoding="utf-8") as f:
            report = json.load(f)
        update_history(data, report.get("scores", {}))
    except Exception as e:
        print(f"히스토리 업데이트 실패: {e}")

if __name__ == "__main__":
    fetch_all()
