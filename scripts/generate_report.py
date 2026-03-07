"""
Macro Sentinel - Report Generator v5
4주 섹터 누적 + 시나리오 분석 + 강화된 프롬프트
"""

import os
import re
import json
import datetime
from groq import Groq

# ─────────────────────────────────────────
# 설정
# ─────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
DATA_PATH    = "data/market_data.json"
REPORT_PATH  = "data/report.json"
TODAY = datetime.date.today().isoformat()

client = Groq(api_key=GROQ_API_KEY)

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
    fg    = d["sentiment"]["fear_greed"]["score"]
    unemp = d["macro"]["unemployment"]["value"]

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

    # 섹터 로테이션: 4주 누적 기준으로 변경
    tech_4w = d["sectors"]["tech"].get("change_4w")
    fin_4w  = d["sectors"]["financials"].get("change_4w")
    if tech_4w is not None and fin_4w is not None:
        avg_4w = (tech_4w + fin_4w) / 2
        scores["sector"] = "green" if avg_4w > 2 else ("yellow" if avg_4w > -2 else "red")
    else:
        scores["sector"] = "gray"

    # Fear & Greed
    if fg is not None:
        scores["sentiment"] = "green" if fg < 40 else ("yellow" if fg < 60 else "red")
    else:
        scores["sentiment"] = "gray"

    # 실업률
    if unemp is not None:
        scores["unemployment"] = "green" if unemp < 4.5 else ("yellow" if unemp < 5.5 else "red")
    else:
        scores["unemployment"] = "gray"

    # 종합 판정
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
# Groq 분석
# ─────────────────────────────────────────
def groq_analysis(d, scores):
    # 섹터 4주 등락 문자열 생성
    sector_lines = ""
    for name, v in d["sectors"].items():
        chg_1d = v.get("change_pct")
        chg_4w = v.get("change_4w")
        sector_lines += f"  - {name.upper()}: 1일 {chg_1d:+.2f}% / 4주 {chg_4w:+.2f}%\n" if chg_1d and chg_4w else f"  - {name.upper()}: 데이터 없음\n"

    fg = d["sentiment"]["fear_greed"]
    fg_str = f"{fg['score']} ({fg['rating']})" if fg["score"] else "데이터 없음"

    prompt = f"""당신은 월스트리트 수석 매크로 전략가입니다. 아래 데이터를 바탕으로 심층 분석을 제공하세요.

━━━ 시장 데이터 ({TODAY}) ━━━

[지수]
- S&P 500: {d['indices']['sp500']['close']} ({d['indices']['sp500']['change_pct']:+.2f}%) | 52주 위치: {d['indices']['sp500']['pct_52w']}%
- Nasdaq 100: {d['indices']['nasdaq100']['close']} ({d['indices']['nasdaq100']['change_pct']:+.2f}%)
- Russell 2000: {d['indices']['russell']['close']} ({d['indices']['russell']['change_pct']:+.2f}%)
- VIX: {d['indices']['vix']['close']} → {scores['vix'].upper()}

[금리 & 스프레드]
- 2Y: {d['rates']['us2y']['value']}% | 10Y: {d['rates']['us10y']['value']}% | 2s10s: {d['spreads']['us2s10s']['value']}%
- TIPS 실질금리: {d['rates']['tips10y']['value']}%
- HY 크레딧 스프레드: {d['spreads']['hy_spread']['value']}%

[매크로 경제]
- Core CPI: {d['macro']['core_cpi']['value']} (최근 발표: {d['macro']['core_cpi']['date']})
- 실업률: {d['macro']['unemployment']['value']}% (최근: {d['macro']['unemployment']['date']})
- GDP 성장률: {d['macro']['gdp_growth']['value']}%
- PCE: {d['macro']['pce']['value']}

[달러 & 환율]
- DXY: {d['fx']['dxy']['close']} ({d['fx']['dxy']['change_pct']:+.2f}%) → {scores['dxy'].upper()}
- USD/KRW: {d['fx']['usdkrw']['close']}
- USD/JPY: {d['fx']['usdjpy']['close']}

[원자재]
- WTI: ${d['commodities']['wti']['close']} | Gold: ${d['commodities']['gold']['close']}

[섹터 로테이션 (1일 / 4주 누적)]
{sector_lines}
[시장 심리]
- Fear & Greed Index: {fg_str} → {scores['sentiment'].upper()}

[유동성]
- Fed 대차대조표: ${d['liquidity']['fed_bs']['value']:,.0f}M
- RRP 잔액: ${d['liquidity']['rrp']['value']}B

[규칙 기반 스코어]
VIX:{scores['vix']} | 금리곡선:{scores['curve']} | HY:{scores['hy_spread']} | 금리:{scores['rates']} | DXY:{scores['dxy']} | TIPS:{scores['tips']} | 섹터:{scores['sector']} | 심리:{scores['sentiment']} | 고용:{scores['unemployment']}
종합판정: {scores['verdict']}

━━━ 분석 지시사항 ━━━
반드시 아래 JSON만 출력하세요. 마크다운 없이 순수 JSON만:

{{"section0_summary":"현재 시장 좌표: 어떤 국면인지 핵심만 3줄로. 수치 포함.","section1_fed":"Fed 금리 유동성 분석: 현재 통화정책 스탠스, 금리곡선 시사점, 실질금리가 밸류에이션에 미치는 영향 4줄.","section2_flow":"달러 자금흐름: DXY 방향과 원인, 글로벌 자금이 어디로 향하는지 3줄.","section3_sector":"섹터 로테이션: 4주 누적 기준으로 어떤 섹터가 강하고 약한지, Risk-On/Off 신호 3줄.","section4_risk":"주요 리스크: 시장이 아직 반영 못한 꼬리 리스크 포함 3줄.","bull_case":"강세 논거 2가지: 구체적 수치와 함께 서술","bear_case":"약세 논거 2가지: 구체적 수치와 함께 서술","verdict_reason":"판정 근거: {scores['verdict']} 판정의 핵심 이유 2줄. 구체적 수치 필수.","scenario_bull":"강세 시나리오: 어떤 조건이 갖춰지면 시장이 상승할지. 트리거 포함.","scenario_base":"기본 시나리오: 현재 흐름이 지속될 때 예상되는 시장 방향.","scenario_bear":"약세 시나리오: 어떤 리스크가 현실화되면 하락할지. 트리거 포함.","entry_triggers":["구체적 수치가 포함된 진입 트리거 조건 1","진입 트리거 2","진입 트리거 3"],"key_events":[{{"date":"YYYY-MM-DD","event":"이벤트명","impact":"예상 시장 영향"}},{{"date":"YYYY-MM-DD","event":"이벤트명","impact":"예상 시장 영향"}},{{"date":"YYYY-MM-DD","event":"이벤트명","impact":"예상 시장 영향"}}]}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 매크로 투자 전략가입니다. 요청한 JSON 형식만 출력하고 다른 텍스트는 절대 포함하지 마세요. 모든 분석은 한국어로 작성하세요."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        text = response.choices[0].message.content.strip()
        print(f"Groq 응답 앞 200자: {text[:200]}")

        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        return json.loads(text)

    except json.JSONDecodeError as e:
        print(f"JSON 파싱 오류: {e}")
        return _fallback()
    except Exception as e:
        print(f"Groq 오류: {e}")
        return _fallback()

def _fallback():
    return {
        "section0_summary": "분석 생성 실패",
        "section1_fed": "-", "section2_flow": "-",
        "section3_sector": "-", "section4_risk": "-",
        "bull_case": "-", "bear_case": "-",
        "verdict_reason": "AI 분석 실패",
        "scenario_bull": "-", "scenario_base": "-", "scenario_bear": "-",
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

    print("Groq 분석 중...")
    analysis = groq_analysis(d, scores)

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
