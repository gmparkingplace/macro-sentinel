"use client";
import { useEffect, useState } from "react";

// ── 타입 ──────────────────────────────────────────────
interface HistoryEntry {
  date: string; verdict: string;
  vix: number | null; sp500: number | null; fg_score: number | null;
  skew: number | null; hy_spread: number | null; us10y: number | null;
  wti: number | null; ratio: number | null;
}

// ── 타입 ──────────────────────────────────────────────
interface IndexData { close: number | null; change_pct: number | null; pct_52w: number | null; }
interface SectorData { close: number | null; change_pct: number | null; change_4w: number | null; pct_52w: number | null; }
interface FredData  { value: number | null; date: string | null; }
interface SkewData  {
  close: number | null; change_pct: number | null;
  signal: string | null; combo_signal: string | null; combo_label: string | null;
}
interface Scores {
  vix: string; curve: string; hy_spread: string; rates: string;
  dxy: string; tips: string; sector: string; sentiment: string;
  unemployment: string; overall: string; verdict: string;
  oil?: string; gdp?: string; gold_signal?: string;
  skew?: string; combo?: string; copper?: string; ism_mfg?: string; ism_svc?: string;
  stagflation_risk?: boolean; override_reason?: string[];
  ratio?: number;
  contrarian_signal?: string | null;
}
interface Analysis {
  section0_summary: string; section1_fed: string;
  section2_flow: string;    section3_sector: string;
  section4_risk: string;    section5_commodities?: string;
  section6_skew?: string;   bull_case: string;
  bear_case: string;        verdict_reason: string;
  scenario_bull: string;    scenario_base: string; scenario_bear: string;
  entry_triggers: string[];
  key_events: { date: string; event: string; impact: string }[];
}
interface NewsItem {
  title: string; title_ko?: string; url: string; source: string; published: string;
}
interface Report {
  date: string;
  data: {
    indices: { sp500: IndexData; nasdaq100: IndexData; russell: IndexData; vix: IndexData };
    rates:   { us2y: FredData; us10y: FredData; tips10y: FredData };
    spreads: { us2s10s: FredData; us5s30s?: FredData; hy_spread: FredData; fra_ois?: FredData };
    fx:      { dxy: FredData & { change_pct?: number | null }; usdkrw: IndexData; usdjpy: IndexData; eurusd: IndexData };
    commodities: { wti: IndexData; gold: IndexData; copper?: IndexData };
    sectors: Record<string, SectorData>;
    liquidity: { fed_bs: FredData; rrp: FredData };
    macro: { cpi_yoy: FredData; core_cpi: FredData; unemployment: FredData; pce: FredData; gdp_growth: FredData; ism_mfg?: FredData; ism_svc?: FredData };
    sentiment: {
      fear_greed: { score: number | null; rating: string | null };
      skew?: SkewData;
    };
    news?: NewsItem[];
  };
  scores:   Scores;
  analysis: Analysis;
  verdict:  string;
}

// ── 유틸 ──────────────────────────────────────────────
const verdictColor: Record<string, string> = { NOW: "#0a8f5c", WAIT: "#b07800", AVOID: "#c0392b" };
const verdictBg:    Record<string, string> = { NOW: "#eafaf3", WAIT: "#fffbe6", AVOID: "#fdf0ef" };
const verdictLabel: Record<string, string> = { NOW: "지금 진입 가능", WAIT: "트리거 대기", AVOID: "진입 금지" };
const scoreColor:   Record<string, string> = { green: "#0a8f5c", yellow: "#b07800", red: "#c0392b", orange: "#e67e22", gray: "#aaa" };
const scoreEmoji:   Record<string, string> = { green: "🟢", yellow: "🟡", red: "🔴", orange: "🟠", gray: "⚫" };
const fmt = (v: number | null, dec = 2) =>
  v == null ? "—" : v.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
const chgColor = (v: number | null) => v == null ? "#999" : v >= 0 ? "#0a8f5c" : "#c0392b";
const chgStr   = (v: number | null) => v == null ? "—" : `${v >= 0 ? "+" : ""}${fmt(v)}%`;

// ── 히스토리 차트 ─────────────────────────────────────
const verdictDot: Record<string, string> = { NOW: "#0a8f5c", WAIT: "#b07800", AVOID: "#c0392b" };

function HistoryChart({ history }: { history: HistoryEntry[] }) {
  if (history.length === 0) return (
    <div style={{ color: "#aaa", fontSize: 12, textAlign: "center", padding: "20px 0" }}>
      히스토리 데이터 없음 — 내일부터 누적됩니다
    </div>
  );

  const recent = history.slice(-30);

  return (
    <div>
      {/* 판정 히스토리 도트 */}
      <div style={{ fontSize: 10, color: "#bbb", letterSpacing: "0.05em", margin: "12px 0 6px" }}>
        일별 판정 히스토리
      </div>
      <div style={{ display: "flex", gap: 3, flexWrap: "wrap" }}>
        {recent.map((h, i) => (
          <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
            <div
              title={`${h.date}\n${h.verdict}\nVIX: ${h.vix ?? "—"}\nS&P: ${h.sp500 ?? "—"}`}
              style={{
                width: 14, height: 14, borderRadius: "50%",
                background: verdictDot[h.verdict] ?? "#aaa",
                cursor: "default", flexShrink: 0,
              }}
            />
            <div style={{ fontSize: 8, color: "#bbb", writingMode: "vertical-rl", transform: "rotate(180deg)", lineHeight: 1 }}>
              {h.date.slice(5)}
            </div>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", gap: 12, marginTop: 8, fontSize: 10, color: "#aaa" }}>
        <span>🟢 NOW</span><span>🟡 WAIT</span><span>🔴 AVOID</span>
        <span style={{ marginLeft: "auto" }}>최신 →</span>
      </div>

      {/* VIX 추이 */}
      <div style={{ marginTop: 14 }}>
        <div style={{ fontSize: 10, color: "#bbb", letterSpacing: "0.05em", marginBottom: 6 }}>
          VIX 추이
        </div>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 2, height: 80 }}>
          {recent.map((h, i) => {
            const v = h.vix ?? 20;
            const barH = Math.min((v / 45) * 100, 100);
            const color = v >= 28 ? "#c0392b" : v >= 22 ? "#e67e22" : "#0a8f5c";
            return (
              <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end", height: "100%" }}>
                <div style={{ fontSize: 7, color: color, fontWeight: 600, marginBottom: 2, lineHeight: 1 }}>
                  {h.vix?.toFixed(0) ?? ""}
                </div>
                <div
                  title={`${h.date}: VIX ${h.vix ?? "—"}`}
                  style={{ width: "100%", height: `${barH}%`, background: color, borderRadius: "2px 2px 0 0", minWidth: 2 }}
                />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── Fear & Greed 게이지 ────────────────────────────────
function FearGreedGauge({ score, rating }: { score: number | null; rating: string | null }) {
  if (score == null) return <div style={{ color: "#aaa", fontSize: 12 }}>데이터 없음</div>;
  const color = score < 25 ? "#c0392b" : score < 45 ? "#e67e22" : score < 55 ? "#b07800" : score < 75 ? "#0a8f5c" : "#27ae60";
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <span style={{ fontSize: 11, color: "#999" }}>Extreme Fear</span>
        <span style={{ fontSize: 11, color: "#999" }}>Extreme Greed</span>
      </div>
      <div style={{ height: 8, background: "#e8e8e8", borderRadius: 4, position: "relative" }}>
        <div style={{ width: "100%", height: "100%", background: "linear-gradient(to right, #c0392b, #e67e22, #b07800, #0a8f5c)", borderRadius: 4, opacity: 0.3, position: "absolute" }} />
        <div style={{ position: "absolute", left: `${score}%`, transform: "translateX(-50%)", width: 14, height: 14, background: color, borderRadius: "50%", top: -3, border: "2px solid white", boxShadow: "0 1px 4px rgba(0,0,0,0.2)", transition: "left 0.5s" }} />
      </div>
      <div style={{ textAlign: "center", marginTop: 10 }}>
        <span style={{ fontSize: 28, fontWeight: 700, color }}>{score}</span>
        <span style={{ fontSize: 12, color: "#777", marginLeft: 8 }}>{rating}</span>
      </div>
    </div>
  );
}

// ── Skew 게이지 ───────────────────────────────────────
function SkewGauge({ skew }: { skew: SkewData | undefined }) {
  if (!skew || skew.close == null) return (
    <div style={{ color: "#aaa", fontSize: 12, textAlign: "center", padding: "8px 0" }}>Skew 데이터 없음</div>
  );

  const val = skew.close;
  // Skew는 보통 100~170 범위. 100=최소, 170=최대로 정규화
  const pct = Math.min(Math.max((val - 100) / 70 * 100, 0), 100);
  const color = val >= 150 ? "#c0392b" : val >= 130 ? "#e67e22" : "#0a8f5c";

  const comboColorMap: Record<string, string> = {
    red: "#c0392b", orange: "#e67e22", yellow: "#b07800", green: "#0a8f5c"
  };
  const comboBgMap: Record<string, string> = {
    red: "#fdf0ef", orange: "#fff5ee", yellow: "#fffbe6", green: "#eafaf3"
  };
  const comboColor = comboColorMap[skew.combo_signal ?? "gray"] ?? "#aaa";
  const comboBg    = comboBgMap[skew.combo_signal ?? "gray"] ?? "#f8f8f8";

  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ fontSize: 11, color: "#999", marginBottom: 8, letterSpacing: "0.05em" }}>CBOE SKEW INDEX</div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <span style={{ fontSize: 11, color: "#999" }}>안정 (100)</span>
        <span style={{ fontSize: 11, color: "#999" }}>위험 (170+)</span>
      </div>
      <div style={{ height: 8, background: "#e8e8e8", borderRadius: 4, position: "relative" }}>
        <div style={{ width: "100%", height: "100%", background: "linear-gradient(to right, #0a8f5c, #e67e22, #c0392b)", borderRadius: 4, opacity: 0.3, position: "absolute" }} />
        <div style={{ position: "absolute", left: `${pct}%`, transform: "translateX(-50%)", width: 14, height: 14, background: color, borderRadius: "50%", top: -3, border: "2px solid white", boxShadow: "0 1px 4px rgba(0,0,0,0.2)", transition: "left 0.5s" }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 10 }}>
        <div>
          <span style={{ fontSize: 28, fontWeight: 700, color }}>{val.toFixed(0)}</span>
          <span style={{ fontSize: 11, color: "#aaa", marginLeft: 8 }}>
            {val >= 150 ? "위험" : val >= 130 ? "경고" : "정상"}
            {skew.change_pct != null && ` (${chgStr(skew.change_pct)})`}
          </span>
        </div>
      </div>

      {/* VIX × Skew 조합 신호 */}
      {skew.combo_label && (
        <div style={{
          marginTop: 12, padding: "10px 14px",
          background: comboBg, border: `1px solid ${comboColor}44`,
          borderLeft: `3px solid ${comboColor}`,
          borderRadius: 8
        }}>
          <div style={{ fontSize: 10, color: comboColor, fontWeight: 700, marginBottom: 4 }}>
            VIX × Skew 조합 신호
          </div>
          <div style={{ fontSize: 12, color: "#444", fontWeight: 600 }}>{skew.combo_label}</div>
          <div style={{ fontSize: 11, color: "#888", marginTop: 4, lineHeight: 1.6 }}>
            {skew.combo_signal === "red"    && "단기 변동성 + 꼬리 리스크 동시 급등. 총체적 위기 경고."}
            {skew.combo_signal === "orange" && "표면은 조용하지만 내부에서 대형 하락 대비 중. 가장 위험한 역설 구간."}
            {skew.combo_signal === "yellow" && "단기 패닉이지만 꼬리 리스크는 낮음. 회복 가능성 있음."}
            {skew.combo_signal === "green"  && "VIX와 Skew 모두 안정. 진입 환경 우호적."}
          </div>
        </div>
      )}
    </div>
  );
}

// ── 시나리오 카드 ──────────────────────────────────────
function ScenarioCard({ label, color, bg, text }: { label: string; color: string; bg: string; text: string }) {
  return (
    <div style={{ padding: "12px 14px", background: bg, border: `1px solid ${color}33`, borderRadius: 8 }}>
      <div style={{ fontSize: 10, color, fontWeight: 700, letterSpacing: "0.1em", marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 12, color: "#555", lineHeight: 1.7 }}>{text}</div>
    </div>
  );
}

// ── 아코디언 카드 ──────────────────────────────────────
function AccordionCard({ icon, title, summary, score, children }: {
  icon: string; title: string; summary: string; score?: string; children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{
      background: "#ffffff",
      border: `1px solid ${open ? "#d0d0d0" : "#e8e8e8"}`,
      borderRadius: 12, overflow: "hidden",
      boxShadow: open ? "0 2px 12px rgba(0,0,0,0.08)" : "0 1px 4px rgba(0,0,0,0.04)",
    }}>
      <div onClick={() => setOpen(!open)} style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "16px 20px", cursor: "pointer",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 20 }}>{icon}</span>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#1a1a1a" }}>{title}</div>
            <div style={{ fontSize: 11, color: "#999", marginTop: 2 }}>{summary}</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {score && <span style={{ fontSize: 16 }}>{scoreEmoji[score] ?? "⚫"}</span>}
          <span style={{ color: "#bbb", fontSize: 11, display: "inline-block", transform: open ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>▼</span>
        </div>
      </div>
      {open && (
        <div style={{ padding: "0 20px 20px", borderTop: "1px solid #f0f0f0" }}>
          <div style={{ height: 14 }} />
          {children}
        </div>
      )}
    </div>
  );
}

function Row({ label, value, color, bar }: { label: string; value: string; color?: string; bar?: number }) {
  return (
    <div style={{ padding: "8px 0", borderBottom: "1px solid #f4f4f4" }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <span style={{ color: "#888", fontSize: 12 }}>{label}</span>
        <span style={{ color: color || "#1a1a1a", fontSize: 12, fontWeight: 600 }}>{value}</span>
      </div>
      {bar != null && (
        <div style={{ marginTop: 4, height: 3, background: "#f0f0f0", borderRadius: 2 }}>
          <div style={{ width: `${Math.min(bar, 100)}%`, height: "100%", background: color || "#0a8f5c", borderRadius: 2, opacity: 0.6 }} />
        </div>
      )}
    </div>
  );
}

function ScoreBadge({ label, score }: { label: string; score: string }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center",
      background: "#fafafa", border: `1px solid ${scoreColor[score] ?? "#aaa"}44`,
      borderRadius: 8, padding: "10px 8px", flex: 1, minWidth: 52,
    }}>
      <span style={{ fontSize: 16 }}>{scoreEmoji[score] ?? "⚫"}</span>
      <span style={{ fontSize: 9, color: "#999", marginTop: 4, textAlign: "center", letterSpacing: "0.03em" }}>{label}</span>
    </div>
  );
}

// ── 메인 ──────────────────────────────────────────────
export default function Home() {
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    fetch("/api/report").then(r => r.json()).then(d => { setReport(d); setLoading(false); }).catch(() => setLoading(false));
    fetch("/api/history").then(r => r.json()).then(d => { if (Array.isArray(d)) setHistory(d); }).catch(() => {});
  }, []);

  if (loading) return (
    <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", background: "#f8f8f8", color: "#aaa", fontFamily: "sans-serif", fontSize: 13 }}>
      로딩 중...
    </div>
  );
  if (!report) return (
    <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", background: "#f8f8f8", color: "#c0392b", fontFamily: "sans-serif", fontSize: 13 }}>
      리포트를 불러올 수 없습니다.
    </div>
  );

  const { data: d, scores, analysis, verdict, date } = report;
  const vc  = verdictColor[verdict];
  const vbg = verdictBg[verdict];
  const skewData = d.sentiment.skew;

  return (
    <div style={{ background: "#f5f5f5", minHeight: "100vh", color: "#1a1a1a", fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>

      {/* 헤더 */}
      <div style={{ borderBottom: "1px solid #e8e8e8", padding: "14px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", position: "sticky", top: 0, background: "#ffffff", zIndex: 100, boxShadow: "0 1px 4px rgba(0,0,0,0.06)" }}>
        <div>
          <span style={{ fontSize: 13, fontWeight: 800, letterSpacing: "0.15em", color: "#1a1a1a" }}>MACRO</span>
          <span style={{ fontSize: 13, fontWeight: 800, letterSpacing: "0.15em", color: "#0a8f5c" }}> SENTINEL</span>
        </div>
        <div style={{ fontSize: 11, color: "#bbb" }}>{date} 기준</div>
      </div>

      <div style={{ maxWidth: 680, margin: "0 auto", padding: "20px 16px 60px" }}>

        {/* 판정 배너 */}
        <div style={{ border: `1px solid ${vc}44`, borderLeft: `4px solid ${vc}`, borderRadius: 12, padding: "20px 24px", marginBottom: 16, background: vbg }}>
          <div style={{ fontSize: 10, color: "#aaa", letterSpacing: "0.15em", marginBottom: 8 }}>MACRO SENTINEL 최종 판정</div>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 16, flexWrap: "wrap" }}>
            <div>
              <div style={{ fontSize: 36, fontWeight: 800, color: vc, letterSpacing: "0.08em", lineHeight: 1 }}>{verdict}</div>
              <div style={{ fontSize: 11, color: "#888", marginTop: 6 }}>{verdictLabel[verdict]}</div>
            </div>
            <div style={{ fontSize: 12, color: "#555", lineHeight: 1.8, maxWidth: 360 }}>{analysis.verdict_reason}</div>
          </div>
        </div>

        {/* 오버라이드 배너 */}
        {scores.override_reason && scores.override_reason.length > 0 && (
          <div style={{
            padding: "10px 16px", marginBottom: 16,
            background: "#fdf0ef", border: "1px solid #f5c6c2",
            borderRadius: 8, fontSize: 11, color: "#c0392b", lineHeight: 1.7
          }}>
            ⚠️ 하드 오버라이드 발동: {scores.override_reason.join(" · ")}
          </div>
        )}

        {/* 역발상 신호 배너 */}
        {scores.contrarian_signal && (
          <div style={{
            padding: "10px 16px", marginBottom: 16,
            background: scores.contrarian_signal === "strong" ? "#fff8e1" : "#f3f8ff",
            border: `1px solid ${scores.contrarian_signal === "strong" ? "#ffe082" : "#b3d4f5"}`,
            borderRadius: 8, fontSize: 11, lineHeight: 1.7,
            color: scores.contrarian_signal === "strong" ? "#b07800" : "#1565c0",
          }}>
            ⚡ 역발상 신호 감지 ({scores.contrarian_signal === "strong" ? "강함" : "약함"}):
            극단적 공포 + VIX 고점 대비 하락 중 —
            {scores.contrarian_signal === "strong"
              ? " 중기 바닥권 진입 가능성. 단, 매크로 리스크 해소 확인 후 진입 검토."
              : " VIX 하락 초기 단계. 추가 확인 필요."}
          </div>
        )}

        {/* 스코어 배지 */}
        <div style={{ display: "flex", gap: 5, marginBottom: 16, flexWrap: "wrap" }}>
          <ScoreBadge label="VIX"       score={scores.vix         ?? "gray"} />
          <ScoreBadge label="금리곡선"   score={scores.curve       ?? "gray"} />
          <ScoreBadge label="HY스프레드" score={scores.hy_spread   ?? "gray"} />
          <ScoreBadge label="금리수준"   score={scores.rates       ?? "gray"} />
          <ScoreBadge label="달러"       score={scores.dxy         ?? "gray"} />
          <ScoreBadge label="실질금리"   score={scores.tips        ?? "gray"} />
          <ScoreBadge label="섹터"       score={scores.sector      ?? "gray"} />
          <ScoreBadge label="심리"       score={scores.sentiment   ?? "gray"} />
          <ScoreBadge label="Skew"       score={scores.skew        ?? "gray"} />
          <ScoreBadge label="VIX×Skew"   score={scores.combo       ?? "gray"} />
          <ScoreBadge label="고용"       score={scores.unemployment ?? "gray"} />
          <ScoreBadge label="유가"       score={scores.oil         ?? "gray"} />
          <ScoreBadge label="GDP"        score={scores.gdp         ?? "gray"} />
          <ScoreBadge label="금(Gold)"   score={scores.gold_signal ?? "gray"} />
          <ScoreBadge label="구리"       score={scores.copper      ?? "gray"} />
          <ScoreBadge label="소비자신뢰"  score={scores.ism_mfg     ?? "gray"} />
          <ScoreBadge label="OECD신뢰"   score={scores.ism_svc     ?? "gray"} />
        </div>

        {/* 아코디언 카드들 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>

          {/* 주요 지수 */}
          <AccordionCard icon="📊" title="주요 지수" score={scores.vix}
            summary={`S&P ${fmt(d.indices.sp500.close, 0)} ${chgStr(d.indices.sp500.change_pct)}  ·  VIX ${fmt(d.indices.vix.close)}`}>
            <Row label="S&P 500"      value={`${fmt(d.indices.sp500.close, 0)} (${chgStr(d.indices.sp500.change_pct)})`}        color={chgColor(d.indices.sp500.change_pct)}    bar={d.indices.sp500.pct_52w ?? undefined} />
            <Row label="Nasdaq 100"   value={`${fmt(d.indices.nasdaq100.close, 0)} (${chgStr(d.indices.nasdaq100.change_pct)})`} color={chgColor(d.indices.nasdaq100.change_pct)} bar={d.indices.nasdaq100.pct_52w ?? undefined} />
            <Row label="Russell 2000" value={`${fmt(d.indices.russell.close, 0)} (${chgStr(d.indices.russell.change_pct)})`}    color={chgColor(d.indices.russell.change_pct)}  bar={d.indices.russell.pct_52w ?? undefined} />
            <Row label="VIX"          value={fmt(d.indices.vix.close)} color={scoreColor[scores.vix]} />
            <div style={{ marginTop: 10, fontSize: 10, color: "#bbb" }}>막대: 52주 내 위치</div>
          </AccordionCard>

          {/* 금리 & 스프레드 */}
          <AccordionCard icon="💵" title="금리 · 스프레드" score={scores.rates}
            summary={`10Y ${fmt(d.rates.us10y.value)}%  ·  2s10s ${fmt(d.spreads.us2s10s.value)}%  ·  HY ${fmt(d.spreads.hy_spread.value)}%`}>
            <Row label="2Y 국채"            value={`${fmt(d.rates.us2y.value)}%`} />
            <Row label="10Y 국채"           value={`${fmt(d.rates.us10y.value)}%`}        color={scoreColor[scores.rates]} />
            <Row label="TIPS 실질금리"      value={`${fmt(d.rates.tips10y.value)}%`}      color={scoreColor[scores.tips]} />
            <Row label="2s10s 스프레드"     value={`${fmt(d.spreads.us2s10s.value)}%`}    color={d.spreads.us2s10s.value != null && d.spreads.us2s10s.value >= 0 ? "#0a8f5c" : "#c0392b"} />
            {d.spreads.us5s30s?.value != null && (
              <Row label="5s30s 스프레드" value={`${fmt(d.spreads.us5s30s.value)}%`} color={d.spreads.us5s30s.value >= 0 ? "#0a8f5c" : "#c0392b"} />
            )}
            <Row label="HY 크레딧 스프레드" value={`${fmt(d.spreads.hy_spread.value)}%`}  color={scoreColor[scores.hy_spread]} />
            {d.spreads.fra_ois?.value != null && (
              <Row label="SOFR (달러 유동성)" value={`${fmt(d.spreads.fra_ois.value)}%`} />
            )}
            <div style={{ marginTop: 12, padding: "10px 14px", background: "#f8f8f8", border: "1px solid #eee", borderRadius: 8, fontSize: 12, color: "#555", lineHeight: 1.8 }}>{analysis.section1_fed}</div>
          </AccordionCard>

          {/* 매크로 경제 */}
          <AccordionCard icon="📈" title="매크로 경제" score={scores.unemployment}
            summary={`실업률 ${fmt(d.macro.unemployment.value)}%  ·  Core CPI ${fmt(d.macro.core_cpi.value)}`}>
            <Row label="Core CPI"       value={fmt(d.macro.core_cpi.value)}       color={d.macro.core_cpi.value != null && d.macro.core_cpi.value > 3.5 ? "#c0392b" : "#0a8f5c"} />
            <Row label="PCE"            value={fmt(d.macro.pce.value)} />
            <Row label="실업률"         value={`${fmt(d.macro.unemployment.value)}%`} color={scoreColor[scores.unemployment]} />
            <Row label="GDP 성장률"     value={`${fmt(d.macro.gdp_growth.value)}%`}   color={d.macro.gdp_growth.value != null && d.macro.gdp_growth.value > 0 ? "#0a8f5c" : "#c0392b"} />
            {d.macro.ism_mfg?.value != null && (
              <Row label="소비자신뢰지수 (미시간대)" value={fmt(d.macro.ism_mfg.value)} color={d.macro.ism_mfg.value >= 80 ? "#0a8f5c" : d.macro.ism_mfg.value >= 60 ? "#b07800" : "#c0392b"} />
            )}
            {d.macro.ism_svc?.value != null && (
              <Row label="소비자신뢰 (OECD)" value={fmt(d.macro.ism_svc.value)} color={d.macro.ism_svc.value >= 100 ? "#0a8f5c" : "#c0392b"} />
            )}
            <Row label="Fed 대차대조표" value={d.liquidity.fed_bs.value ? `$${(d.liquidity.fed_bs.value / 1000000).toFixed(2)}T` : "—"} />
            <Row label="RRP 잔액"       value={d.liquidity.rrp.value ? `$${fmt(d.liquidity.rrp.value)}B` : "—"} />
          </AccordionCard>

          {/* 환율 & 원자재 */}
          <AccordionCard icon="🌍" title="환율 · 원자재" score={scores.oil ?? "gray"}
            summary={`DXY ${fmt(d.fx.dxy.value)}  ·  KRW ${fmt(d.fx.usdkrw.close, 0)}  ·  Gold $${fmt(d.commodities.gold.close, 0)}`}>
            <Row label="DXY"     value={`${fmt(d.fx.dxy.value)} (${chgStr(d.fx.dxy.change_pct ?? null)})`} color={chgColor(d.fx.dxy.change_pct ? -d.fx.dxy.change_pct : null)} />
            <Row label="USD/KRW" value={`${fmt(d.fx.usdkrw.close, 0)} (${chgStr(d.fx.usdkrw.change_pct)})`} color={chgColor(d.fx.usdkrw.change_pct)} />
            <Row label="USD/JPY" value={`${fmt(d.fx.usdjpy.close)} (${chgStr(d.fx.usdjpy.change_pct)})`} />
            <Row label="EUR/USD" value={`${fmt(d.fx.eurusd.close)} (${chgStr(d.fx.eurusd.change_pct)})`} />
            <Row label="WTI Oil" value={`$${fmt(d.commodities.wti.close)} (${chgStr(d.commodities.wti.change_pct)})`}    color={chgColor(d.commodities.wti.change_pct)} />
            <Row label="Gold"    value={`$${fmt(d.commodities.gold.close, 0)} (${chgStr(d.commodities.gold.change_pct)})`} color={chgColor(d.commodities.gold.change_pct)} />
            {d.commodities.copper?.close != null && (
              <Row label="Copper" value={`$${fmt(d.commodities.copper.close)} (${chgStr(d.commodities.copper.change_pct)})`} color={chgColor(d.commodities.copper.change_pct)} />
            )}
            <div style={{ marginTop: 12, padding: "10px 14px", background: "#f8f8f8", border: "1px solid #eee", borderRadius: 8, fontSize: 12, color: "#555", lineHeight: 1.8 }}>{analysis.section2_flow}</div>
          </AccordionCard>

          {/* 섹터 로테이션 */}
          <AccordionCard icon="🔄" title="섹터 로테이션" score={scores.sector}
            summary={`Tech 4주 ${chgStr(d.sectors.tech?.change_4w)}  ·  Fin 4주 ${chgStr(d.sectors.financials?.change_4w)}`}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 4, marginBottom: 8, paddingBottom: 6, borderBottom: "1px solid #f0f0f0" }}>
              <span style={{ fontSize: 10, color: "#bbb" }}>섹터</span>
              <span style={{ fontSize: 10, color: "#bbb", textAlign: "right" }}>1일</span>
              <span style={{ fontSize: 10, color: "#bbb", textAlign: "right" }}>4주 누적</span>
            </div>
            {Object.entries(d.sectors).map(([name, v]) => (
              <div key={name} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", padding: "7px 0", borderBottom: "1px solid #f4f4f4", fontSize: 12 }}>
                <span style={{ color: "#555" }}>{name.toUpperCase()}</span>
                <span style={{ color: chgColor(v.change_pct), textAlign: "right" }}>{chgStr(v.change_pct)}</span>
                <span style={{ color: chgColor(v.change_4w), textAlign: "right", fontWeight: 600 }}>{chgStr(v.change_4w)}</span>
              </div>
            ))}
            <div style={{ marginTop: 12, padding: "10px 14px", background: "#f8f8f8", border: "1px solid #eee", borderRadius: 8, fontSize: 12, color: "#555", lineHeight: 1.8 }}>{analysis.section3_sector}</div>
          </AccordionCard>

          {/* 시장 심리 */}
          <AccordionCard icon="🧠" title="시장 심리" score={scores.sentiment}
            summary={`Fear & Greed: ${d.sentiment.fear_greed.score ?? "—"} · Skew: ${skewData?.close?.toFixed(0) ?? "—"}`}>
            <FearGreedGauge score={d.sentiment.fear_greed.score} rating={d.sentiment.fear_greed.rating} />
            <SkewGauge skew={skewData} />
            {analysis.section6_skew && (
              <div style={{ marginTop: 12, padding: "10px 14px", background: "#f8f8f8", border: "1px solid #eee", borderRadius: 8, fontSize: 12, color: "#555", lineHeight: 1.8 }}>
                {analysis.section6_skew}
              </div>
            )}
          </AccordionCard>

          {/* AI 분석 */}
          <AccordionCard icon="🤖" title="AI 매크로 분석"
            summary={analysis.section0_summary.slice(0, 55) + "..."}>
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 10, color: "#bbb", letterSpacing: "0.1em", marginBottom: 8 }}>시나리오 분석</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <ScenarioCard label="🐂 강세 시나리오" color="#0a8f5c" bg="#eafaf3" text={analysis.scenario_bull} />
                <ScenarioCard label="➡️ 기본 시나리오" color="#b07800" bg="#fffbe6" text={analysis.scenario_base} />
                <ScenarioCard label="🐻 약세 시나리오" color="#c0392b" bg="#fdf0ef" text={analysis.scenario_bear} />
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 14 }}>
              <div style={{ padding: "12px 14px", background: "#eafaf3", border: "1px solid #a8dfc9", borderRadius: 8 }}>
                <div style={{ fontSize: 10, color: "#0a8f5c", fontWeight: 700, marginBottom: 6 }}>✅ BULL</div>
                <div style={{ fontSize: 11, color: "#444", lineHeight: 1.7 }}>{analysis.bull_case}</div>
              </div>
              <div style={{ padding: "12px 14px", background: "#fdf0ef", border: "1px solid #f5c6c2", borderRadius: 8 }}>
                <div style={{ fontSize: 10, color: "#c0392b", fontWeight: 700, marginBottom: 6 }}>❌ BEAR</div>
                <div style={{ fontSize: 11, color: "#444", lineHeight: 1.7 }}>{analysis.bear_case}</div>
              </div>
            </div>
            <div style={{ padding: "10px 14px", background: "#fffbe6", border: "1px solid #ffe082", borderRadius: 8, marginBottom: 14 }}>
              <div style={{ fontSize: 10, color: "#b07800", fontWeight: 700, marginBottom: 6 }}>⚠️ 리스크</div>
              <div style={{ fontSize: 11, color: "#444", lineHeight: 1.7 }}>{analysis.section4_risk}</div>
            </div>
            {analysis.entry_triggers?.length > 0 && (
              <div>
                <div style={{ fontSize: 10, color: "#bbb", letterSpacing: "0.1em", marginBottom: 8 }}>진입 트리거 조건</div>
                {analysis.entry_triggers.map((t, i) => (
                  <div key={i} style={{ display: "flex", gap: 8, padding: "7px 0", borderBottom: "1px solid #f4f4f4" }}>
                    <span style={{ color: "#b07800", fontSize: 11, fontWeight: 700, minWidth: 20 }}>#{i + 1}</span>
                    <span style={{ fontSize: 12, color: "#555", lineHeight: 1.6 }}>{t}</span>
                  </div>
                ))}
              </div>
            )}
          </AccordionCard>

          {/* 이벤트 캘린더 */}
          {analysis.key_events?.length > 0 && (
            <AccordionCard icon="📅" title="핵심 이벤트 캘린더"
              summary={`향후 주요 일정 ${analysis.key_events.length}개`}>
              {analysis.key_events.map((e, i) => (
                <div key={i} style={{ display: "flex", gap: 12, padding: "8px 0", borderBottom: "1px solid #f4f4f4", flexWrap: "wrap" }}>
                  <span style={{ color: "#b07800", fontSize: 11, fontWeight: 600, minWidth: 80, fontFamily: "monospace" }}>{e.date}</span>
                  <div>
                    <div style={{ fontSize: 12, color: "#1a1a1a", fontWeight: 500 }}>{e.event}</div>
                    <div style={{ fontSize: 11, color: "#aaa", marginTop: 2 }}>{e.impact}</div>
                  </div>
                </div>
              ))}
            </AccordionCard>
          )}

          {/* 히스토리 */}
          <AccordionCard icon="📉" title="판정 히스토리"
            summary={`최근 ${Math.min(history.length, 30)}일 누적`}>
            <HistoryChart history={history} />
          </AccordionCard>

          {/* 뉴스 헤드라인 */}
          {report.data.news && report.data.news.length > 0 && (
            <AccordionCard icon="📰" title="시장 헤드라인"
              summary={`${report.data.news[0].source} 외 ${report.data.news.length - 1}건`}>
              {report.data.news.map((item, i) => (
                <a
                  key={i}
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 2,
                    padding: "10px 0",
                    borderBottom: "1px solid #f4f4f4",
                    textDecoration: "none",
                    color: "inherit",
                  }}
                >
                  <div style={{ fontSize: 12, color: "#1a1a1a", fontWeight: 500, lineHeight: 1.5 }}>
                    {item.title_ko ?? item.title}
                  </div>
                  <div style={{ fontSize: 10, color: "#aaa" }}>
                    {item.source}
                    {item.published ? ` · ${item.published.slice(0, 16)}` : ""}
                  </div>
                </a>
              ))}
            </AccordionCard>
          )}
        </div>

        {/* 푸터 */}
        <div style={{ textAlign: "center", padding: "32px 0 0", fontSize: 10, color: "#ccc", letterSpacing: "0.08em" }}>
          MACRO SENTINEL · FRED + Yahoo Finance · Groq LLaMA · 투자 조언 아님
        </div>
      </div>
    </div>
  );
}
