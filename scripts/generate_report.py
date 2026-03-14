"""
Macro Sentinel - Report Generator v9
Kimi K2 모델 + section_macro 추가 + 진입 트리거 개선 + 전체 정리
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
# 역발상 신호
# ─────────────────────────────────────────
def load_vix_history():
    try:
        if not os.path.exists("data/history.json"):
            return []
        with open("data/history.json", "r", encoding="utf-8") as f:
            history = json.load(f)
        return [h["vix"] for h in history[-14:] if h.get("vix") is not None]
    except Exception as e:
        print(f"히스토리 VIX 로드 오류: {e}")
        return []

def calc_contrarian_signal(vix_now, fg_now, vix_history):
    if len(vix_history) < 5:
        print(f"역발상 신호: 히스토리 부족 ({len(vix_history)}일) → 스킵")
        return None
    if vix_now is None or fg_now is None:
        return None

    extreme_fear       = fg_now <= 15
    vix_5d             = sum(vix_history[-5:]) / 5
    vix_peak           = max(vix_history)
    vix_drop_from_peak = (vix_peak - vix_now) / vix_peak * 100 if vix_peak > 0 else 0
    vix_3d_declining   = (
        len(vix_history) >= 3 and
        vix_history[-3] > vix_history[-2] > vix_history[-1]
    )

    print(f"역발상 분석: FG={fg_now}, VIX={vix_now:.1f}, "
          f"5일평균={vix_5d:.1f}, 고점={vix_peak:.1f}, "
          f"고점대비하락={vix_drop_from_peak:.1f}%, 3일연속하락={vix_3d_declining}")

    if extreme_fear and vix_drop_from_peak >= 10 and vix_3d_declining:
        print("⚡ 역발상 신호: STRONG")
        return "strong"
    if extreme_fear and vix_drop_from_peak >= 5:
        print("⚡ 역발상 신호: WEAK")
        return "weak"
    return None

def calc_contrarian_signal_intraday(vix_now, vix_chg, fg_now):
    if vix_now is None or fg_now is None or vix_chg is None:
        return None
    if fg_now <= 15 and 25 <= vix_now <= 40 and vix_chg < -1.0:
        print(f"⚡ 당일 역발상 신호: FG={fg_now}, VIX={vix_now:.1f}({vix_chg:+.1f}%)")
        return "intraday"
    return None

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

    vix        = d["indices"]["vix"]["close"]
    s2s10      = d["spreads"]["us2s10s"]["value"]
    hy         = d["spreads"]["hy_spread"]["value"]
    us10y      = d["rates"]["us10y"]["value"]
    dxy        = d["fx"]["dxy"].get("value") or d["fx"]["dxy"].get("close")
    tips       = d["rates"]["tips10y"]["value"]
    unemp      = d["macro"]["unemployment"]["value"]
    gdp        = d["macro"]["gdp_growth"]["value"]
    wti        = d["commodities"]["wti"]["close"]
    gold       = d["commodities"]["gold"]["close"]
    gold_chg   = d["commodities"]["gold"]["change_pct"]
    copper     = d["commodities"].get("copper", {}).get("close")
    copper_chg = d["commodities"].get("copper", {}).get("change_pct")
    fg         = d["sentiment"]["fear_greed"]["score"]
    skew_data  = d["sentiment"].get("skew", {})
    skew_val   = skew_data.get("close")
    ism_mfg    = d["macro"].get("ism_mfg", {}).get("value")
    ism_svc    = d["macro"].get("ism_svc", {}).get("value")
    s5s30s     = d["spreads"].get("us5s30s", {}).get("value")
    fra_ois    = d["spreads"].get("fra_ois", {}).get("value")

    # VIX
    scores["vix"] = score_label(vix, [(16, "green"), (22, "yellow"), (999, "red")])

    # HY 크레딧 스프레드
    scores["hy_spread"] = score_label(hy, [(3.5, "green"), (5.0, "yellow"), (999, "red")])

    # 10Y 금리
    scores["rates"] = score_label(us10y, [(4.0, "green"), (4.5, "yellow"), (999, "red")])

    # DXY
    scores["dxy"] = score_label(dxy, [(101, "green"), (104, "yellow"), (999, "red")])

    # TIPS 실질금리
    scores["tips"] = score_label(tips, [(1.2, "green"), (2.0, "yellow"), (999, "red")])

    # 금리 곡선 (2s10s)
    if s2s10 is None:
        scores["curve"] = "gray"
    elif s2s10 >= 0.2:
        scores["curve"] = "green"
    elif s2s10 >= -0.1:
        scores["curve"] = "yellow"
    else:
        scores["curve"] = "red"

    # 섹터 로테이션
    tech_4w = d["sectors"].get("tech", {}).get("change_4w")
    fin_4w  = d["sectors"].get("financials", {}).get("change_4w")
    if tech_4w is not None and fin_4w is not None:
        avg_4w = (tech_4w + fin_4w) / 2
        scores["sector"] = "green" if avg_4w > 3 else ("yellow" if avg_4w > -1 else "red")
    else:
        scores["sector"] = "gray"

    # Fear & Greed
    if fg is not None:
        scores["sentiment"] = "red" if fg < 35 else ("yellow" if fg < 55 else "green")
    else:
        scores["sentiment"] = "gray"

    # Skew 단독
    if skew_val is not None:
        if skew_val >= 150:   scores["skew"] = "red"
        elif skew_val >= 130: scores["skew"] = "yellow"
        else:                 scores["skew"] = "green"
    else:
        scores["skew"] = "gray"

    # VIX × Skew 조합
    combo = skew_data.get("combo_signal")
    if combo == "red":
        scores["combo"] = "red"
    elif combo in ("orange", "yellow"):
        scores["combo"] = "yellow"
    elif combo == "green":
        scores["combo"] = "green"
    else:
        scores["combo"] = "gray"

    # 실업률
    if unemp is not None:
        scores["unemployment"] = "green" if unemp < 4.2 else ("yellow" if unemp < 5.0 else "red")
    else:
        scores["unemployment"] = "gray"

    # 유가
    if wti is not None:
        scores["oil"] = "green" if wti < 75 else ("yellow" if wti < 85 else "red")
    else:
        scores["oil"] = "gray"

    # GDP
    if gdp is not None:
        scores["gdp"] = "green" if gdp >= 2.0 else ("yellow" if gdp >= 0.5 else "red")
    else:
        scores["gdp"] = "gray"

    # Gold 신호
    if gold is not None and gold_chg is not None:
        if gold > 3500 and gold_chg > 1.5:
            scores["gold_signal"] = "red"
        elif gold > 3000:
            scores["gold_signal"] = "yellow"
        else:
            scores["gold_signal"] = "green"
    else:
        scores["gold_signal"] = "gray"

    # 구리
    if copper_chg is not None:
        scores["copper"] = score_label(copper_chg, [(-3, "red"), (-1, "yellow"), (1, "yellow"), (999, "green")])
    else:
        scores["copper"] = "gray"

    # 소비자신뢰지수 (미시간대, 기준 ~80)
    scores["ism_mfg"] = score_label(ism_mfg, [(60, "red"), (75, "yellow"), (999, "green")])

    # OECD 소비자신뢰 (100 기준선)
    scores["ism_svc"] = score_label(ism_svc, [(97, "red"), (99, "yellow"), (999, "green")])

    # 스태그플레이션 감지
    stagflation_risk = False
    if wti is not None and unemp is not None:
        if wti > 85 and unemp > 4.3:
            stagflation_risk = True
            print(f"⚠️ 스태그플레이션 리스크 감지: WTI={wti}, 실업률={unemp}%")

    # 역발상 신호
    vix_history       = load_vix_history()
    contrarian_signal = calc_contrarian_signal(vix, fg, vix_history)
    if contrarian_signal is None:
        vix_chg = d["indices"]["vix"]["change_pct"]
        contrarian_signal = calc_contrarian_signal_intraday(vix, vix_chg, fg)
    scores["contrarian_signal"] = contrarian_signal

    # 가중 점수 계산
    color_weight = {"green": 2, "yellow": 1, "red": 0, "gray": 1}
    core = ["vix", "hy_spread", "rates", "curve", "oil"]
    skip = {"verdict", "overall", "stagflation_risk", "ratio",
            "override_reason", "gold_signal", "combo", "contrarian_signal"}

    total = 0
    max_total = 0
    for k, v in scores.items():
        if k in skip:
            continue
        w = 2 if k in core else 1
        total     += color_weight.get(v, 1) * w
        max_total += 2 * w

    ratio = total / max_total if max_total > 0 else 0

    # 하드 오버라이드
    hard_avoid = False
    hard_wait  = False
    override_reason = []

    if vix is not None and vix >= 28:
        hard_avoid = True
        override_reason.append(f"VIX {vix:.1f} >= 28")

    if wti is not None and wti >= 90:
        hard_avoid = True
        override_reason.append(f"WTI ${wti:.1f} >= $90")

    if stagflation_risk:
        hard_avoid = True
        override_reason.append(f"스태그플레이션(WTI>{wti}, 실업률>{unemp}%)")

    if skew_val is not None and vix is not None:
        if vix < 22 and skew_val >= 130:
            hard_wait = True
            override_reason.append(f"숨겨진경고: VIX {vix:.1f}(낮음)+Skew {skew_val:.0f}(높음)")

    if vix is not None and 24 <= vix < 28:
        hard_wait = True
        override_reason.append(f"VIX {vix:.1f} >= 24")

    if scores.get("gold_signal") == "red":
        hard_wait = True
        override_reason.append(f"Gold 극단 위험회피 ${gold:.0f}")

    if override_reason:
        print(f"⚠️ 오버라이드 발동: {', '.join(override_reason)}")

    # 최종 판정
    if hard_avoid:
        if contrarian_signal == "strong" and not stagflation_risk and (wti is None or wti < 90):
            scores["overall"] = "yellow"
            verdict = "WAIT"
            override_reason.append("⚡ 역발상 신호(극단공포+VIX꺾임): AVOID→WAIT 완화")
            print("⚡ 역발상 신호로 AVOID → WAIT 완화")
        else:
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
    fg         = d["sentiment"].get("fear_greed", {})
    fg_str     = f"{fg.get('score')} ({fg.get('rating')})" if fg.get("score") is not None else "계산 실패"
    skew_data  = d["sentiment"].get("skew", {})
    skew_val   = skew_data.get("close")
    skew_label = skew_data.get("combo_label", "데이터 없음")
    skew_str   = f"{skew_val:.0f} / 조합 신호: {skew_label}" if skew_val is not None else "데이터 없음"

    ism_mfg    = d["macro"].get("ism_mfg", {}).get("value")
    ism_svc    = d["macro"].get("ism_svc", {}).get("value")
    copper     = d["commodities"].get("copper", {}).get("close")
    copper_chg = d["commodities"].get("copper", {}).get("change_pct")
    s5s30s     = d["spreads"].get("us5s30s", {}).get("value")
    fra_ois    = d["spreads"].get("fra_ois", {}).get("value")
    cpi        = d["macro"].get("cpi_yoy", {}).get("value")
    core_cpi   = d["macro"].get("core_cpi", {}).get("value")
    pce        = d["macro"].get("pce", {}).get("value")

    news       = d.get("news", [])
    news_block = "\n".join(f"  - {n.get('title_ko') or n.get('title', '')}" for n in news) if news else "  - 수집 실패"

    calendar  = d.get("calendar", [])
    cal_block = "\n".join(f"  - {ev['date']} | {ev['event']}" for ev in calendar) if calendar else "  - 없음"

    stag_warning = ""
    if scores.get("stagflation_risk"):
        stag_warning = "\n⚠️ STAGFLATION ALERT: WTI > $85 + 실업률 > 4.3% 동시 발생.\n"

    override_block = ""
    if scores.get("override_reason"):
        override_block = "\n⚠️ 하드 오버라이드 발동: " + ", ".join(scores["override_reason"]) + "\n"

    # FX 방향 Python 계산
    krw_chg = d['fx']['usdkrw']['change_pct'] or 0.0
    dxy_chg = d['fx']['dxy'].get('change_pct') or 0.0
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
- 10Y: {d['rates']['us10y']['value']}% | 2Y: {d['rates']['us2y']['value']}% | TIPS(실질): {d['rates']['tips10y']['value']}%
- 2s10s: {d['spreads']['us2s10s']['value']}bp | 5s20s: {s5s30s}bp | SOFR: {fra_ois}%
- HY 크레딧 스프레드: {d['spreads']['hy_spread']['value']}%

[매크로 경제]
- CPI: {cpi}% | Core CPI: {core_cpi}% | PCE: {pce}% (모두 전년비, Fed 목표 2%)
- 실업률: {d['macro']['unemployment']['value']}% | GDP 성장률: {d['macro']['gdp_growth']['value']}%
- 미시간대 소비자신뢰지수: {ism_mfg} (기준선 80) | OECD 소비자신뢰: {ism_svc} (기준선 100)
- 구리: ${copper} ({f'+{copper_chg:.2f}%' if copper_chg and copper_chg > 0 else f'{copper_chg:.2f}%' if copper_chg else '—'}) ← 경기 선행 지표

[달러 & 환율] ※ 중요: 아래 문구를 분석에 그대로 복사해서 사용할 것.
- 달러: {dxy_dir}
- 원화: {krw_dir}

[원자재]
- WTI: ${d['commodities']['wti']['close']} ({f"+{d['commodities']['wti']['change_pct']:.2f}%" if d['commodities']['wti']['change_pct'] is not None else "—"})
- Gold: ${d['commodities']['gold']['close']} ({f"+{d['commodities']['gold']['change_pct']:.2f}%" if d['commodities']['gold']['change_pct'] and d['commodities']['gold']['change_pct'] > 0 else f"{d['commodities']['gold']['change_pct']:.2f}%" if d['commodities']['gold']['change_pct'] is not None else "—"})
- Copper: ${copper} (경기 선행)

[시장 심리]
- Fear & Greed: {fg_str}
- CBOE Skew Index: {skew_str}
  ※ Skew 130 미만=정상, 130~150=꼬리리스크 경고, 150 이상=블랙스완 대비 급증
  ※ VIX 낮음+Skew 높음 = 가장 위험한 역설 구간

[스코어카드]
종합판정: {scores['verdict']} (ratio: {scores['ratio']})

━━━ 향후 주요 경제 일정 ━━━
{cal_block}

━━━ 분석 지시 ━━━
순수 JSON만 출력하세요. 마크다운 없이. 모든 키를 포함하세요.

{{
  "section0_summary":"현재 시장 좌표를 5줄 이상으로 상세히 서술. 주요 지수 수치, 뉴스 맥락, 매크로 환경 포함.",
  "section1_fed":"Fed·금리 분석을 5줄 이상으로. FOMC 스탠스, 금리 곡선, 실질금리, 유동성 환경 포함.",
  "section2_flow":"달러·자금흐름 분석 4줄 이상. 반드시 '{krw_dir}' 문구를 그대로 포함할 것.",
  "section3_sector":"섹터 로테이션 분석 5줄 이상. Risk-On/Off 판독, 강세/약세 섹터 구체적으로 서술.",
  "section4_risk":"지정학·정책 리스크 5줄 이상. 현재 활성 리스크, 시장 반영도, 꼬리 리스크 포함.",
  "section5_commodities":"원자재(WTI, Gold, Copper) 동향 및 스태그플레이션 리스크 분석 4줄 이상.",
  "section6_skew":"VIX×Skew 조합 신호 해석 3줄 이상 (현재 조합: {skew_label}). 꼬리 리스크 함의 포함.",
  "section_macro":"[섹션7 - 매크로 경제 종합] CPI {cpi}%, Core CPI {core_cpi}%, PCE {pce}% 기반 인플레이션 추세 분석. 고용(실업률 {d['macro']['unemployment']['value']}%), GDP({d['macro']['gdp_growth']['value']}%), 소비자신뢰({ism_mfg})를 종합한 경기 사이클 위치 판단 3줄 이상. 스태그플레이션 리스크 여부 명시.",
  "bull_case":"강세 논거 3가지를 각각 2줄 이상으로 구체적으로 서술.",
  "bear_case":"약세 논거 3가지를 각각 2줄 이상으로 구체적으로 서술.",
  "verdict_reason":"판정 {scores['verdict']} 이유를 3줄 이상으로. 핵심 근거 수치 포함.",
  "scenario_bull":"강세 시나리오 2줄 이상. 발생 조건(VIX XX 이하, WTI $XX 이하 등)과 S&P 500 목표 수준 포함.",
  "scenario_base":"기본 시나리오 2줄 이상. 현재 추세 지속 시 향후 4주 예상 경로.",
  "scenario_bear":"약세 시나리오 2줄 이상. 강세/기본과 다른 리스크 트리거와 하방 목표 수준 포함.",
  "entry_triggers":["진입 트리거 1: 현재 판정이 AVOID/WAIT일 경우 완화 조건 (구체적 수치 포함, 현재 달성 여부 명시)","진입 트리거 2: 두 번째 완화 조건","진입 트리거 3: 세 번째 완화 조건 또는 NOW일 경우 무효화 조건"],
  "key_events":[{{"date":"YYYY-MM-DD","event":"이벤트명","impact":"예상 영향"}}]
}}"""

    try:
        response = client.chat.completions.create(
            model="moonshotai/kimi-k2-instruct",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 매크로 투자 전략가입니다. 뉴스 맥락과 시장 데이터를 종합 분석합니다. 요청한 JSON 형식만 출력하고 다른 텍스트는 절대 포함하지 마세요. 모든 분석은 한국어로 작성하세요. 중요: USD/KRW 수치 상승은 반드시 원화약세로 해석하세요. 반드시 순수 한국어만 사용하고 한자, 일본어, 중국어 문자를 절대 사용하지 마세요. 각 섹션 값에 큰따옴표가 포함될 경우 반드시 이스케이프 처리하세요."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=6000,
        )
        text = response.choices[0].message.content.strip()
        print(f"Groq 응답 앞 200자: {text[:200]}")

        text = re.sub(r"```json", "", text)
        text = re.sub(r"```",     "", text)
        text = text.strip()
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e1:
            print(f"1차 파싱 실패: {e1} → 키별 개별 추출 시도")
            parsed = _extract_by_key(text)
            if not parsed:
                print("키별 추출도 실패")
                raise e1

        # FX 강제 교정
        parsed["section2_flow"] = (
            f"{dxy_dir}. {krw_dir}. "
            f"USD/KRW {d['fx']['usdkrw']['close']:.0f}원으로 "
            f"{'원화 약세 압력이 지속되며 수입 물가 상승 우려가 있다' if krw_chg > 0 else '원화 강세로 수출 기업 실적에 부담'}. "
            f"{'달러 약세는 이머징 자금 유입에 긍정적' if dxy_chg < 0 else '달러 강세는 이머징 자금 유출 압력'}."
        )

        # key_events Python 캘린더로 교체
        parsed["key_events"] = [
            {"date": ev["date"], "event": ev["event"], "impact": _event_impact(ev["category"])}
            for ev in calendar
        ]

        return parsed

    except json.JSONDecodeError as e:
        print(f"JSON 파싱 오류: {e}")
        return _fallback()
    except Exception as e:
        print(f"Groq 오류: {e}")
        return _fallback()


def _extract_by_key(text: str) -> dict:
    """
    JSON 파싱 실패 시 정규식으로 키별 값 개별 추출
    문자열 값만 추출 (배열 키는 별도 처리)
    """
    STRING_KEYS = [
        "section0_summary", "section1_fed", "section2_flow", "section3_sector",
        "section4_risk", "section5_commodities", "section6_skew", "section_macro",
        "bull_case", "bear_case", "verdict_reason",
        "scenario_bull", "scenario_base", "scenario_bear",
    ]
    result = {}
    for key in STRING_KEYS:
        # "key":"값" 패턴 추출 (줄바꿈 포함)
        pattern = rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"|"{key}"\s*:\s*"([\s\S]*?)(?=",\s*"|"\s*\}})'
        m = re.search(rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        if m:
            result[key] = m.group(1).replace('\\"', '"').replace('\\n', '\n')
        else:
            result[key] = "-"

    # entry_triggers 배열 추출
    m = re.search(r'"entry_triggers"\s*:\s*\[([\s\S]*?)\]', text)
    if m:
        items = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))
        result["entry_triggers"] = [i.replace('\\"', '"') for i in items] if items else []
    else:
        result["entry_triggers"] = []

    # key_events는 Python 캘린더로 덮어쓰므로 빈값
    result["key_events"] = []

    found = sum(1 for v in result.values() if v and v != "-" and v != [])
    print(f"키별 추출 완료: {found}/{len(STRING_KEYS)}개 성공")
    return result if found >= 5 else {}


def _event_impact(category: str) -> str:
    return {
        "fed":  "금리 결정 및 향후 통화정책 경로에 직접 영향",
        "cpi":  "인플레이션 추세 확인 → Fed 정책 기대 변화",
        "pce":  "Fed 선호 인플레이션 지표 → 피벗 타이밍 영향",
        "jobs": "고용 강도 확인 → 경기 연착륙 여부 판단",
        "gdp":  "경제 성장률 확인 → 스태그플레이션 리스크 평가",
    }.get(category, "시장 변동성 주의")


def _fallback():
    return {
        "section0_summary": "분석 생성 실패",
        "section1_fed": "-", "section2_flow": "-",
        "section3_sector": "-", "section4_risk": "-",
        "section5_commodities": "-", "section6_skew": "-",
        "section_macro": "-",
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

    # 히스토리 누적
    try:
        from fetch_data import update_history
        update_history(d, scores)
    except Exception as e:
        print(f"히스토리 업데이트 건너뜀: {e}")


if __name__ == "__main__":
    generate()
