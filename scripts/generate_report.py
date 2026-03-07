"""
Macro Sentinel - Report Generator v6
뉴스 주입 + 강화된 가중치 + 하드 오버라이드 + 스태그플레이션 감지
"""

import os
import re
import json
import datetime
from groq import Groq

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
DATA_PATH    = "data/market_data.json"
REPORT_PATH  = "data/report.json"
TODAY = datetime.date.today().isoformat()

client = Groq(api_key=GROQ_API_KEY)

# ─────────────────────────────────────────
# 스코어 계산
# ─────────────────────────────────────────
def score_label(value, thresholds):
    if value is None:
        return "gray"
    for bound, color in thresholds:
        if value <= bound:
            return color
    return thresholds[-1][1]

def calc_scores(d):
    scores = {}

    vix   = d["indices"]["vix"]["close"]
    s2s10 = d["spreads"]["us2s10s"]["value"]
    hy    = d["spreads"]["hy_spread"]["value"]
    us10y = d["rates"]["us10y"]["value"]
    dxy   = d["fx"]["dxy"]["close"]
    tips  = d["rates"]["tips10y"]["value"]
    unemp = d["macro"]["unemployment"]["value"]
    gdp   = d["macro"]["gdp_growth"]["value"]
    wti   = d["commodities"]["wti"]["close"]
    gold  = d["commodities"]["gold"]["close"]
    gold_chg = d["commodities"]["gold"]["change_pct"]
    fg    = d["sentiment"]["fear_greed"]["score"]

    # ── VIX ──────────────────────────────
    scores["vix"] = score_label(vix, [
        (16,  "green"),
        (22,  "yellow"),
        (999, "red")
    ])

    # ── HY 크레딧 스프레드 ────────────────
    scores["hy_spread"] = score_label(hy, [
        (3.5,  "green"),
        (5.0,  "yellow"),
        (999,  "red")
    ])

    # ── 10Y 금리 ─────────────────────────
    scores["rates"] = score_label(us10y, [
        (4.0,  "green"),
        (4.5,  "yellow"),
        (999,  "red")
    ])

    # ── DXY 달러 ─────────────────────────
    scores["dxy"] = score_label(dxy, [
        (101,  "green"),
        (104,  "yellow"),
        (999,  "red")
    ])

    # ── TIPS 실질금리 ─────────────────────
    scores["tips"] = score_label(tips, [
        (1.2,  "green"),
        (2.0,  "yellow"),
        (999,  "red")
    ])

    # ── 금리 곡선 (2s10s) ─────────────────
    if s2s10 is None:
        scores["curve"] = "gray"
    elif s2s10 >= 0.2:
        scores["curve"] = "green"
    elif s2s10 >= -0.1:
        scores["curve"] = "yellow"
    else:
        scores["curve"] = "red"

    # ── 섹터 로테이션 (4주 누적) ──────────
    tech_4w = d["sectors"].get("tech", {}).get("change_4w")
    fin_4w  = d["sectors"].get("financials", {}).get("change_4w")
    if tech_4w is not None and fin_4w is not None:
        avg_4w = (tech_4w + fin_4w) / 2
        scores["sector"] = "green" if avg_4w > 3 else ("yellow" if avg_4w > -1 else "red")
    else:
        scores["sector"] = "gray"

    # ── Fear & Greed ──────────────────────
    if fg is not None:
        scores["sentiment"] = "green" if fg < 35 else ("yellow" if fg < 55 else "red")
    else:
        scores["sentiment"] = "gray"

    # ── 실업률 ───────────────────────────
    if unemp is not None:
        scores["unemployment"] = "green" if unemp < 4.2 else ("yellow" if unemp < 5.0 else "red")
    else:
        scores["unemployment"] = "gray"

    # ── 유가 ─────────────────────────────
    if wti is not None:
        scores["oil"] = "green" if wti < 75 else ("yellow" if wti < 85 else "red")
    else:
        scores["oil"] = "gray"

    # ── GDP ───────────────────────────────
    if gdp is not None:
        scores["gdp"] = "green" if gdp > 2.0 else ("yellow" if gdp > 0 else "red")
    else:
        scores["gdp"] = "gray"

    # ── Gold 위험회피 신호 ─────────────────
    if gold is not None:
        if gold > 4000 and (gold_chg or 0) > 0:
            scores["gold_signal"] = "red"
        elif gold > 3000:
            scores["gold_signal"] = "yellow"
        else:
            scores["gold_signal"] = "green"
    else:
        scores["gold_signal"] = "gray"

    # ── 스태그플레이션 감지 ───────────────
    stagflation_risk = False
    if wti is not None and unemp is not None:
        if wti > 85 and unemp > 4.3:
            stagflation_risk = True
            print(f"⚠️ 스태그플레이션 리스크 감지: WTI={wti}, 실업률={unemp}%")

    # ── 가중 점수 계산 ────────────────────
    color_weight = {"green": 2, "yellow": 1, "red": 0, "gray": 1}
    core = ["vix", "hy_spread", "rates", "curve", "oil"]
    skip = {"verdict", "overall", "stagflation_risk", "ratio",
            "override_reason", "gold_signal"}

    total = 0
    max_total = 0
    for k, v in scores.items():
        if k in skip:
            continue
        w = 2 if k in core else 1
        total     += color_weight.get(v, 1) * w
        max_total += 2 * w

    ratio = total / max_total if max_total > 0 else 0

    # ── 하드 오버라이드 ───────────────────
    hard_avoid = False
    hard_wait  = False
    override_reason = []

    # VIX 28 이상 → 무조건 AVOID
    if vix is not None and vix >= 28:
        hard_avoid = True
        override_reason.append(f"VIX {vix:.1f} >= 28")

    # WTI $90 이상 → 무조건 AVOID
    if wti is not None and wti >= 90:
        hard_avoid = True
        override_reason.append(f"WTI ${wti:.1f} >= $90")

    # 스태그플레이션 → AVOID
    if stagflation_risk:
        hard_avoid = True
        override_reason.append(f"스태그플레이션(WTI>{wti}, 실업률>{unemp}%)")

    # VIX 24 이상 → 최소 WAIT
    if vix is not None and 24 <= vix < 28:
        hard_wait = True
        override_reason.append(f"VIX {vix:.1f} >= 24")

    # Gold 극단 위험회피 → 최소 WAIT
    if scores.get("gold_signal") == "red":
        hard_wait = True
        override_reason.append(f"Gold 극단 위험회피 ${gold:.0f}")

    if override_reason:
        print(f"⚠️ 오버라이드 발동: {', '.join(override_reason)}")

    # ── 최종 판정 ─────────────────────────
    if hard_avoid:
        scores["overall"] = "red"
        verdict = "AVOID"
    elif hard_wait or ratio < 0.65:
        scores["overall"] = "yellow"
        verdict = "WAIT"
        if ratio >= 0.65:
            ratio = 0.60
    else:
        scores["overall"] = "green"
        verdict = "NOW"

    scores["verdict"]          = verdict
    scores["stagflation_risk"] = stagflation_risk
    scores["override_reason"]  = override_reason
    scores["ratio"]            = round(ratio, 3)

    print(f"스코어 ratio: {ratio:.3f} → {verdict}")
    return scores


# ─────────────────────────────────────────
# Groq 분석
# ─────────────────────────────────────────
def groq_analysis(d, scores):
    sector_lines = ""
    for name, v in d["sectors"].items():
        chg_1d = v.get("change_pct")
        chg_4w = v.get("change_4w")
        c1 = f"{chg_1d:+.2f}%" if chg_1d is not None else "N/A"
        c4 = f"{chg_4w:+.2f}%" if chg_4w is not None else "N/A"
        sector_lines += f"  - {name.upper()}: 1일 {c1} / 4주 {c4}\n"

    fg     = d["sentiment"].get("fear_greed", {})
    fg_str = f"{fg.get('score')} ({fg.get('rating')})" if fg.get("score") is not None else "계산 실패"

    news       = d.get("news", [])
    news_block = "\n".join(f"  - {h}" for h in news) if news else "  - 수집 실패"

    stag_warning = ""
    if scores.get("stagflation_risk"):
        stag_warning = "\n⚠️ STAGFLATION ALERT: WTI > $85 + 실업률 > 4.3% 동시 발생.\n"

    override_block = ""
    if scores.get("override_reason"):
        override_block = "\n⚠️ 하드 오버라이드 발동: " + ", ".join(scores["override_reason"]) + "\n"

    # FX 방향 Python에서 미리 계산 (Groq 해석 오류 방지)
    krw_chg = d['fx']['usdkrw']['change_pct']
    dxy_chg = d['fx']['dxy']['change_pct']
    jpy_chg = d['fx']['usdjpy']['change_pct']
    eur_chg = d['fx']['eurusd']['change_pct']
    krw_dir = f"원화약세·달러강세 (USD/KRW +{krw_chg:.2f}%)" if krw_chg > 0 else f"원화강세·달러약세 (USD/KRW {krw_chg:.2f}%)"
    dxy_dir = f"달러강세 (DXY +{dxy_chg:.2f}%)" if dxy_chg > 0 else f"달러약세 (DXY {dxy_chg:.2f}%)"
    jpy_dir = f"엔화약세 (USD/JPY +{jpy_chg:.2f}%)" if jpy_chg > 0 else f"엔화강세 (USD/JPY {jpy_chg:.2f}%)"
    eur_dir = f"유로강세 (EUR/USD +{eur_chg:.2f}%)" if eur_chg > 0 else f"유로약세 (EUR/USD {eur_chg:.2f}%)"

    prompt = f"""당신은 월스트리트 수석 매크로 전략가입니다. 아래 실시간 뉴스와 시장 데이터를 함께 분석하세요.

━━━ 실시간 뉴스 헤드라인 ({TODAY}) ━━━
{news_block}
{stag_warning}{override_block}
━━━ 시장 데이터 ━━━

[지수]
- S&P 500: {d['indices']['sp500']['close']} ({d['indices']['sp500']['change_pct']:+.2f}%) | 52주 위치: {d['indices']['sp500']['pct_52w']}%
- Nasdaq 100: {d['indices']['nasdaq100']['close']} ({d['indices']['nasdaq100']['change_pct']:+.2f}%)
- Russell 2000: {d['indices']['russell']['close']} ({d['indices']['russell']['change_pct']:+.2f}%)
- VIX: {d['indices']['vix']['close']}

[금리 & 스프레드]
- 2Y: {d['rates']['us2y']['value']}% | 10Y: {d['rates']['us10y']['value']}% | 2s10s: {d['spreads']['us2s10s']['value']}%
- TIPS 실질금리: {d['rates']['tips10y']['value']}%
- HY 크레딧 스프레드: {d['spreads']['hy_spread']['value']}%

[매크로 경제]
- Core CPI: {d['macro']['core_cpi']['value']} (기준일: {d['macro']['core_cpi']['date']})
- 실업률: {d['macro']['unemployment']['value']}%
- GDP 성장률: {d['macro']['gdp_growth']['value']}%

[달러 & 환율] ※ 아래 방향은 Python이 계산한 확정값. 반드시 이 방향 그대로 section2_flow에 사용할 것.
- 달러: {dxy_dir}
- 원화: {krw_dir}
- 엔화: {jpy_dir}
- 유로: {eur_dir}

[원자재]
- WTI: ${d['commodities']['wti']['close']} ({d['commodities']['wti']['change_pct']:+.2f}%) | Gold: ${d['commodities']['gold']['close']} ({d['commodities']['gold']['change_pct']:+.2f}%)

[섹터 로테이션]
{sector_lines}
[시장 심리]
- Fear & Greed: {fg_str}

[유동성]
- Fed 대차대조표: ${d['liquidity']['fed_bs']['value']:,.0f}M
- RRP 잔액: ${d['liquidity']['rrp']['value']}B

[스코어카드]
VIX:{scores['vix']} | 금리곡선:{scores['curve']} | HY:{scores['hy_spread']} | 금리:{scores['rates']} | DXY:{scores['dxy']} | TIPS:{scores['tips']} | 섹터:{scores['sector']} | 심리:{scores['sentiment']} | 고용:{scores['unemployment']} | 유가:{scores['oil']} | GDP:{scores['gdp']} | Gold:{scores['gold_signal']}
종합판정: {scores['verdict']} (ratio: {scores['ratio']})

━━━ 분석 지시 ━━━
- 뉴스 헤드라인 맥락을 반드시 분석에 반영하세요
- 오버라이드가 발동된 이유를 verdict_reason에 명확히 서술하세요
- [달러 & 환율] 섹션의 방향값을 그대로 사용하세요. 절대 반대로 해석하지 마세요.
- 순수 JSON만 출력 (마크다운 없이):

{{"section0_summary":"현재 시장 좌표 3줄 (뉴스 맥락 + 수치 포함)","section1_fed":"Fed·금리 분석 4줄","section2_flow":"달러·자금흐름 3줄 (반드시 위에서 계산된 {dxy_dir}, {krw_dir} 방향 그대로 사용)","section3_sector":"섹터 로테이션 3줄 (4주 누적 기준)","section4_risk":"지정학·정책 리스크 3줄 (뉴스 반영)","bull_case":"강세 논거 2가지 (수치 포함)","bear_case":"약세 논거 2가지 (수치 + 뉴스 맥락 포함)","verdict_reason":"판정 {scores['verdict']} 이유 2줄 (오버라이드 발동 시 그 이유 명시)","scenario_bull":"강세 시나리오와 트리거","scenario_base":"기본 시나리오","scenario_bear":"약세 시나리오와 트리거","entry_triggers":["진입 트리거 1 (수치 포함)","진입 트리거 2","진입 트리거 3"],"key_events":[{{"date":"YYYY-MM-DD","event":"이벤트명","impact":"예상 시장 영향"}},{{"date":"YYYY-MM-DD","event":"이벤트명","impact":"예상 시장 영향"}},{{"date":"YYYY-MM-DD","event":"이벤트명","impact":"예상 시장 영향"}}]}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 매크로 투자 전략가입니다. 뉴스 맥락과 시장 데이터를 종합 분석합니다. 요청한 JSON 형식만 출력하고 다른 텍스트는 절대 포함하지 마세요. 모든 분석은 한국어로 작성하세요. 중요: USD/KRW 수치 상승은 반드시 원화약세로 해석하고, 절대로 원화강세라고 쓰지 마세요."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=2500,
        )
        text = response.choices[0].message.content.strip()
        print(f"Groq 응답 앞 200자: {text[:200]}")

        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*",     "", text)
        text = re.sub(r"\s*```$",     "", text)
        text = text.strip()

        return json.loads(text)

    except json.JSONDecodeError as e:
        print(f"JSON 파싱 오류: {e}\n원문: {text[:500]}")
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
    print(f"종합 판정: {scores['verdict']} (ratio={scores['ratio']})")

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

    print(f"✅ 리포트 저장 완료 → 판정: {scores['verdict']}")


if __name__ == "__main__":
    generate()
