"""
Macro Sentinel - Report Generator
수집된 데이터 → 규칙 기반 스코어 계산 → Gemini로 텍스트 분석 → report.json 저장
"""

import os
import json
import datetime
import google.generativeai as genai

# ─────────────────────────────────────────
# 설정
# ─────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DATA_PATH   = "data/market_data.json"
REPORT_PATH = "data/report.json"
TODAY = datetime.date.today().isoformat()

genai.configure(api_key=GEMINI_API_KEY)

# ─────────────────────────────────────────
# 규칙 기반 스코어 계산
# ─────────────────────────────────────────
def score(value, thresholds):
    """
    thresholds = [(upper_bound, color), ...]
    예: VIX → [(18, "green"), (25, "yellow"), (999, "red")]
    """
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

    # VIX: 낮을수록 좋음
    scores["vix"] = score(vix, [(18, "green"), (25, "yellow"), (999, "red")])

    # 2s10s: 정상화(양수)일수록 좋음
    if s2s10 is None:
        scores["curve"] = "gray"
    elif s2s10 >= 0.1:
        scores["curve"] = "green"
    elif s2s10 >= -0.2:
        scores["curve"] = "yellow"
    else:
        scores["curve"] = "red"

    # HY 크레딧 스프레드: 낮을수록 좋음 (단위: %)
    scores["hy_spread"] = score(hy, [(4.0, "green"), (5.5, "yellow"), (999, "red")])

    # 10Y 금리: 너무 높으면 주식 비우호
    scores["rates"] = score(us10y, [(4.2, "green"), (4.7, "yellow"), (999, "red")])

    # DXY: 낮을수록 이머징·주식에 우호
    scores["dxy"] = score(dxy, [(102, "green"), (106, "yellow"), (999, "red")])

    # TIPS 실질금리: 낮을수록 주식 밸류에이션 우호
    scores["tips"] = score(tips, [(1.5, "green"), (2.2, "yellow"), (999, "red")])

    # 섹터 로테이션: Tech+Financials 4주 상대강도
    tech_chg = d["sectors"]["tech"]["change_pct"]
    fin_chg  = d["sectors"]["financials"]["change_pct"]
    if tech_chg is not None and fin_chg is not None:
        avg_risk_on = (tech_chg + fin_chg) / 2
        scores["sector"] = "green" if avg_risk_on > 0 else ("yellow" if avg_risk_on > -1 else "red")
    else:
        scores["sector"] = "gray"

    # 종합 판정
    color_score = {"green": 2, "yellow": 1, "red": 0, "gray": 1}
    total = sum(color_score[v] for v in scores.values())
    max_score = len(scores) * 2
    ratio = total / max_score

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
    """데이터 요약을 Gemini에 전달해서 한국어 분석 텍스트 생성"""

    prompt = f"""
당신은 매크로 투자 분석가입니다. 아래 시장 데이터를 바탕으로 한국어로 분석 리포트를 작성하세요.

## 오늘 시장 데이터 ({TODAY})

### 지수
- S&P 500: {d['indices']['sp500']['close']} ({d['indices']['sp500']['change_pct']:+.2f}%)
- Nasdaq 100: {d['indices']['nasdaq100']['close']} ({d['indices']['nasdaq100']['change_pct']:+.2f}%)
- Russell 2000: {d['indices']['russell']['close']} ({d['indices']['russell']['change_pct']:+.2f}%)
- VIX: {d['indices']['vix']['close']}

### 금리 & 스프레드
- 2Y 국채: {d['rates']['us2y']['value']}%
- 10Y 국채: {d['rates']['us10y']['value']}%
- 2s10s 스프레드: {d['spreads']['us2s10s']['value']}%
- HY 크레딧 스프레드: {d['spreads']['hy_spread']['value']}%
- TIPS 10Y (실질금리): {d['rates']['tips10y']['value']}%

### 달러 & 환율
- DXY: {d['fx']['dxy']['close']}
- USD/KRW: {d['fx']['usdkrw']['close']}
- USD/JPY: {d['fx']['usdjpy']['close']}

### 원자재
- WTI Oil: {d['commodities']['wti']['close']}
- Gold: {d['commodities']['gold']['close']}

### 규칙 기반 스코어
- VIX 환경: {scores['vix']}
- 금리 곡선: {scores['curve']}
- HY 스프레드: {scores['hy_spread']}
- 금리 수준: {scores['rates']}
- 달러: {scores['dxy']}
- 실질금리: {scores['tips']}
- 섹터 로테이션: {scores['sector']}
- 종합 판정: {scores['verdict']}

## 작성 지시사항
반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.

{{
  "section0_summary": "현재 시장 좌표 요약 (3줄 이내)",
  "section1_fed": "Fed·금리·유동성 환경 분석 (4줄 이내)",
  "section2_flow": "글로벌 자금흐름·달러 분석 (3줄 이내)",
  "section3_sector": "섹터 로테이션 및 Risk-On/Off 판독 (3줄 이내)",
  "section4_risk": "현재 주요 지정학·정책 리스크 (3줄 이내)",
  "bull_case": "강세 논거 2가지 (짧게)",
  "bear_case": "약세 논거 2가지 (짧게)",
  "verdict_reason": "최종 판정 근거 (2줄)",
  "entry_triggers": ["진입 트리거 조건 1", "진입 트리거 조건 2", "진입 트리거 조건 3"],
  "key_events": [
    {{"date": "날짜", "event": "이벤트명", "impact": "예상 영향"}},
    {{"date": "날짜", "event": "이벤트명", "impact": "예상 영향"}}
  ]
}}
"""

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()
        # JSON 펜스 제거
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        print(f"Gemini 오류: {e}")
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