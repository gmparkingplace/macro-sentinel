"""
Macro Sentinel - Report Generator v3
google-genai 패키지 사용 (google.generativeai 대체)
"""

import os
import re
import json
import datetime
from google import genai

# ─────────────────────────────────────────
# 설정
# ─────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DATA_PATH   = "data/market_data.json"
REPORT_PATH = "data/report.json"
TODAY = datetime.date.today().isoformat()

client = genai.Client(api_key=GEMINI_API_KEY)

# ─────────────────────────────────────────
# 규칙 기반 스코어 계산
# ─────────────────────────────────────────
def score(value, thresholds):
    if value is None:
        return "gray"
    for bound, color in thresholds:
        if value <= bound:
            return color
    return "red"

def calc_scores(d):
    scores = {}
    vix   = d["indices"]["vix"]["close"]
    s2s10 = d["spreads"]["us2s10s"]["value"]
    hy    = d["spreads"]["hy_spread"]["value"]
    us10y = d["rates"]["us10y"]["value"]
    dxy   = d["fx"]["dxy"]["close"]
    tips  = d["rates"]["tips10y"]["value"]

    scores["vix"]       = score(vix,   [(18, "green"), (25, "yellow"), (999, "red")])
    scores["hy_spread"] = score(hy,    [(4.0, "green"), (5.5, "yellow"), (999, "red")])
    scores["rates"]     = score(us10y, [(4.2, "green"), (4.7, "yellow"), (999, "red")])
    scores["dxy"]       = score(dxy,   [(102, "green"), (106, "yellow"), (999, "red")])
    scores["tips"]      = score(tips,  [(1.5, "green"), (2.2, "yellow"), (999, "red")])

    if s2s10 is None:
        scores["curve"] = "gray"
    elif s2s10 >= 0.1:
        scores["curve"] = "green"
    elif s2s10 >= -0.2:
        scores["curve"] = "yellow"
    else:
        scores["curve"] = "red"

    tech_chg = d["sectors"]["tech"]["change_pct"]
    fin_chg  = d["sectors"]["financials"]["change_pct"]
    if tech_chg is not None and fin_chg is not None:
        avg = (tech_chg + fin_chg) / 2
        scores["sector"] = "green" if avg > 0 else ("yellow" if avg > -1 else "red")
    else:
        scores["sector"] = "gray"

    color_score = {"green": 2, "yellow": 1, "red": 0, "gray": 1}
    total = sum(color_score[v] for v in scores.values())
    ratio = total / (len(scores) * 2)

    if ratio >= 0.65:
        scores["overall"] = "green"
        scores["verdict"] = "NOW"
    elif ratio >= 0.40:
        scores["overall"] = "yellow"
        scores["verdict"] = "WAIT"
    else:
        scores["overall"] = "red"
        scores["verdict"] = "AVOID"

    return scores

# ─────────────────────────────────────────
# Gemini 텍스트 분석
# ─────────────────────────────────────────
def gemini_analysis(d, scores):
    prompt = f"""당신은 매크로 투자 분석가입니다. 아래 시장 데이터를 바탕으로 한국어로 분석하세요.

오늘 날짜: {TODAY}
S&P 500: {d['indices']['sp500']['close']} ({d['indices']['sp500']['change_pct']:+.2f}%)
Nasdaq 100: {d['indices']['nasdaq100']['close']} ({d['indices']['nasdaq100']['change_pct']:+.2f}%)
Russell 2000: {d['indices']['russell']['close']} ({d['indices']['russell']['change_pct']:+.2f}%)
VIX: {d['indices']['vix']['close']}
2Y 국채: {d['rates']['us2y']['value']}%
10Y 국채: {d['rates']['us10y']['value']}%
2s10s 스프레드: {d['spreads']['us2s10s']['value']}%
HY 크레딧 스프레드: {d['spreads']['hy_spread']['value']}%
TIPS 실질금리: {d['rates']['tips10y']['value']}%
DXY: {d['fx']['dxy']['close']}
USD/KRW: {d['fx']['usdkrw']['close']}
WTI Oil: {d['commodities']['wti']['close']}
Gold: {d['commodities']['gold']['close']}
종합 판정: {scores['verdict']}

아래 JSON만 출력하세요. 마크다운 없이 JSON만:

{{"section0_summary":"시장 좌표 요약 2-3줄","section1_fed":"Fed 금리 유동성 분석 3줄","section2_flow":"달러 자금흐름 분석 2줄","section3_sector":"섹터 로테이션 판독 2줄","section4_risk":"주요 리스크 2줄","bull_case":"강세 논거 2가지","bear_case":"약세 논거 2가지","verdict_reason":"최종 판정 근거 2줄","entry_triggers":["트리거1","트리거2","트리거3"],"key_events":[{{"date":"날짜","event":"이벤트","impact":"영향"}},{{"date":"날짜","event":"이벤트","impact":"영향"}}]}}"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        text = response.text.strip()
        print(f"Gemini 응답 앞 300자: {text[:300]}")

        # JSON 펜스 제거
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        return json.loads(text)

    except json.JSONDecodeError as e:
        print(f"JSON 파싱 오류: {e}")
        print(f"실패 텍스트: {text[:500]}")
        return _fallback()
    except Exception as e:
        print(f"Gemini 오류: {e}")
        return _fallback()

def _fallback():
    return {
        "section0_summary": "분석 생성 실패 — 데이터를 직접 확인하세요.",
        "section1_fed": "-", "section2_flow": "-",
        "section3_sector": "-", "section4_risk": "-",
        "bull_case": "-", "bear_case": "-",
        "verdict_reason": "AI 분석 실패. 스코어 기반 판정만 유효.",
        "entry_triggers": [], "key_events": []
    }

# ─────────────────────────────────────────
# 메인
# ─────────────────────────────────────────
def generate():
    print(f"[{TODAY}] 리포트 생성 시작...")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        d = json.load(f)

    print("스코어 계산 중...")
    scores = calc_scores(d)
    print(f"종합 판정: {scores['verdict']}")

    print("Gemini 분석 중...")
    analysis = gemini_analysis(d, scores)

    report = {
        "date": TODAY,
        "data": d,
        "scores": scores,
        "analysis": analysis,
        "verdict": scores["verdict"]
    }

    os.makedirs("data", exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"✅ 리포트 저장 완료: {REPORT_PATH}")
    print(f"최종 판정: {scores['verdict']}")

if __name__ == "__main__":
    generate()
