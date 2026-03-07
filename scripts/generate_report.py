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
        scores["sentiment"] = "red" if fg < 35 else ("yellow" if fg < 55 else "green")
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

    # 환율 방향 텍스트를 LLM이 오해할 수 없도록 더 명확하게 고정
    krw_chg = d['fx']['usdkrw']['change_pct']
    dxy_chg = d['fx']['dxy']['change_pct']
    
    krw_dir = f"원화 약세(달러 대비 가치 하락, USD/KRW +{krw_chg:.2f}%)" if krw_chg > 0 else f"원화 강세(달러 대비 가치 상승, USD/KRW {krw_chg:.2f}%)"
    dxy_dir = f"달러 강세(DXY +{dxy_chg:.2f}%)" if dxy_chg > 0 else f"달러 약세(DXY {dxy_chg:.2f}%)"

    prompt = f"""당신은 월스트리트 수석 매크로 전략가입니다. 아래 실시간 뉴스와 시장 데이터를 함께 분석하세요.

━━━ 실시간 뉴스 헤드라인 ({TODAY}) ━━━
{news_block}
{stag_warning}{override_block}
━━━ 시장 데이터 ━━━
[지수]
- S&P 500: {d['indices']['sp500']['close']} | VIX: {d['indices']['vix']['close']}

[금리 & 스프레드]
- 10Y: {d['rates']['us10y']['value']}% | HY 크레딧 스프레드: {d['spreads']['hy_spread']['value']}%

[매크로 경제]
- 실업률: {d['macro']['unemployment']['value']}% | GDP 성장률: {d['macro']['gdp_growth']['value']}%

[달러 & 환율] ※ 중요: 아래 문구를 분석에 그대로 복사해서 사용할 것. 임의로 해석을 바꾸지 마세요.
- 달러: {dxy_dir}
- 원화: {krw_dir}

[원자재]
- WTI: ${d['commodities']['wti']['close']} ({d['commodities']['wti']['change_pct']:+.2f}%) 
- Gold: ${d['commodities']['gold']['close']} ({d['commodities']['gold']['change_pct']:+.2f}%)

[시장 심리]
- Fear & Greed: {fg_str}

[스코어카드]
종합판정: {scores['verdict']} (ratio: {scores['ratio']})

━━━ 분석 지시 ━━━
- 순수 JSON만 출력하세요 (마크다운 불포함).
- 반드시 아래 제공된 JSON 키(Key)를 모두 포함해야 합니다.

{{
  "section0_summary":"현재 시장 좌표 3줄 (뉴스 맥락 + 수치 포함)",
  "section1_fed":"Fed·금리 분석 4줄",
  "section2_flow":"달러·자금흐름 3줄 (반드시 '{krw_dir}' 문구를 그대로 포함할 것)",
  "section3_sector":"섹터 로테이션 3줄",
  "section4_risk":"지정학·정책 리스크 3줄",
  "section5_commodities":"원자재(WTI, Gold) 동향 및 스태그플레이션 리스크 분석 3줄",
  "bull_case":"강세 논거 2가지",
  "bear_case":"약세 논거 2가지",
  "verdict_reason":"판정 {scores['verdict']} 이유 2줄",
  "scenario_bull":"강세 시나리오",
  "scenario_base":"기본 시나리오",
  "scenario_bear":"약세 시나리오",
  "entry_triggers":["진입 트리거 1", "진입 트리거 2", "진입 트리거 3"],
  "key_events":[{{"date":"YYYY-MM-DD","event":"이벤트명","impact":"예상 영향"}}]
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 매크로 투자 전략가입니다. 오직 JSON 형식만 출력합니다. USD/KRW 상승은 원화 약세, 하락은 원화 강세입니다. 제공된 데이터를 반대로 해석하는 행위를 엄격히 금지합니다."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3, # 환각 방지를 위해 온도를 약간 낮춤
            max_tokens=2500,
        )
        text = response.choices[0].message.content.strip()
        print(f"Groq 응답 앞 200자: {text[:200]}")

        # 백틱 전체 제거
        text = re.sub(r"```json", "", text)
        text = re.sub(r"```",     "", text)
        text = text.strip()

        # JSON 시작점 찾기
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]

        return json.loads(text)
        # FX 해석 강제 교정 — Groq 출력 무시하고 Python 계산값으로 덮어쓰기
        try:
            parsed = json.loads(text)
            krw_chg = d['fx']['usdkrw']['change_pct']
            dxy_chg = d['fx']['dxy']['change_pct']
            krw_dir = f"원화약세(USD/KRW +{krw_chg:.2f}%)" if krw_chg > 0 else f"원화강세(USD/KRW {krw_chg:.2f}%)"
            dxy_dir = f"달러약세(DXY {dxy_chg:.2f}%)" if dxy_chg < 0 else f"달러강세(DXY +{dxy_chg:.2f}%)"
            parsed["section2_flow"] = (
                f"현재 환율: {dxy_dir}, {krw_dir}. "
                f"USD/KRW {d['fx']['usdkrw']['close']:.0f}원으로 "
                f"{'원화 약세 압력이 지속되며 수입 물가 상승 우려가 있다' if krw_chg > 0 else '원화 강세로 수출 기업 실적에 부담'}. "
                f"DXY {d['fx']['dxy']['close']:.2f}로 "
                f"{'달러 약세는 이머징 자금 유입에 긍정적' if dxy_chg < 0 else '달러 강세는 이머징 자금 유출 압력'}."
            )
            return parsed
        except:
            pass

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
