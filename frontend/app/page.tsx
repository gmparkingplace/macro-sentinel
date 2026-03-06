"use client";
import { useEffect, useState } from "react";

// ── 타입 ──────────────────────────────────────────────
interface IndexData { close: number | null; change_pct: number | null; pct_52w: number | null; }
interface FredData  { value: number | null; date: string | null; }
interface Scores {
  vix: string; curve: string; hy_spread: string;
  rates: string; dxy: string; tips: string;
  sector: string; overall: string; verdict: string;
}
interface Analysis {
  section0_summary: string; section1_fed: string;
  section2_flow: string;    section3_sector: string;
  section4_risk: string;    bull_case: string;
  bear_case: string;        verdict_reason: string;
  entry_triggers: string[];
  key_events: { date: string; event: string; impact: string }[];
}
interface Report {
  date: string;
  data: {
    indices: { sp500: IndexData; nasdaq100: IndexData; russell: IndexData; vix: IndexData };
    rates:   { us2y: FredData; us10y: FredData; tips10y: FredData };
    spreads: { us2s10s: FredData; hy_spread: FredData };
    fx:      { dxy: IndexData; usdkrw: IndexData; usdjpy: IndexData; eurusd: IndexData };
    commodities: { wti: IndexData; gold: IndexData };
    sectors: Record<string, IndexData>;
    liquidity: { fed_bs: FredData; rrp: FredData };
  };
  scores:   Scores;
  analysis: Analysis;
  verdict:  string;
}

// ── 유틸 ──────────────────────────────────────────────
const verdictColor: Record<string, string> = {
  NOW: "#00ff9d", WAIT: "#ffd000", AVOID: "#ff4560"
};
const verdictLabel: Record<string, string> = {
  NOW: "지금 진입 가능", WAIT: "트리거 대기", AVOID: "진입 금지"
};
const verdictDesc: Record<string, string> = {
  NOW: "매크로 환경이 진입에 우호적입니다",
  WAIT: "일부 지표가 개선을 기다리고 있습니다",
  AVOID: "매크로 역풍이 강합니다"
};
const scoreColor: Record<string, string> = {
  green: "#00ff9d", yellow: "#ffd000", red: "#ff4560", gray: "#555"
};
const scoreEmoji: Record<string, string> = {
  green: "🟢", yellow: "🟡", red: "🔴", gray: "⚫"
};
const fmt = (v: number | null, dec = 2) =>
  v == null ? "—" : v.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
const chgColor = (v: number | null) =>
  v == null ? "#666" : v >= 0 ? "#00ff9d" : "#ff4560";
const chgStr = (v: number | null) =>
  v == null ? "—" : `${v >= 0 ? "+" : ""}${fmt(v)}%`;

// ── 아코디언 카드 ──────────────────────────────────────
function AccordionCard({
  icon, title, summary, score, children
}: {
  icon: string;
  title: string;
  summary: string;
  score?: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{
      background: "rgba(255,255,255,0.03)",
      border: `1px solid ${open ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.06)"}`,
      borderRadius: 12,
      overflow: "hidden",
      transition: "border-color 0.2s",
    }}>
      {/* 헤더 — 항상 보임 */}
      <div
        onClick={() => setOpen(!open)}
        style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "16px 20px", cursor: "pointer",
          background: open ? "rgba(255,255,255,0.03)" : "transparent",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 20 }}>{icon}</span>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#e8e8e8" }}>{title}</div>
            <div style={{ fontSize: 11, color: "#666", marginTop: 2 }}>{summary}</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {score && <span style={{ fontSize: 16 }}>{scoreEmoji[score]}</span>}
          <span style={{ color: "#444", fontSize: 12, transition: "transform 0.2s", display: "inline-block", transform: open ? "rotate(180deg)" : "rotate(0deg)" }}>▼</span>
        </div>
      </div>

      {/* 세부 내용 — 클릭 시 펼침 */}
      {open && (
        <div style={{ padding: "0 20px 20px", borderTop: "1px solid rgba(255,255,255,0.05)" }}>
          <div style={{ height: 16 }} />
          {children}
        </div>
      )}
    </div>
  );
}

// ── 데이터 행 ──────────────────────────────────────────
function Row({ label, value, color, bar }: { label: string; value: string; color?: string; bar?: number }) {
  return (
    <div style={{ padding: "7px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ color: "#777", fontSize: 12 }}>{label}</span>
        <span style={{ color: color || "#e8e8e8", fontSize: 13, fontWeight: 600 }}>{value}</span>
      </div>
      {bar != null && (
        <div style={{ marginTop: 5, height: 3, background: "rgba(255,255,255,0.06)", borderRadius: 2 }}>
          <div style={{ width: `${Math.min(bar, 100)}%`, height: "100%", background: color || "#00ff9d", borderRadius: 2, transition: "width 0.5s" }} />
        </div>
      )}
    </div>
  );
}

// ── 스코어 배지 ────────────────────────────────────────
function ScoreBadge({ label, score }: { label: string; score: string }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center",
      background: "rgba(255,255,255,0.03)",
      border: `1px solid ${scoreColor[score]}33`,
      borderRadius: 8, padding: "10px 12px", minWidth: 60, flex: 1,
    }}>
      <span style={{ fontSize: 18 }}>{scoreEmoji[score]}</span>
      <span style={{ fontSize: 9, color: "#555", marginTop: 5, letterSpacing: "0.05em", textAlign: "center" }}>
        {label}
      </span>
    </div>
  );
}

// ── 메인 ──────────────────────────────────────────────
export default function Home() {
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  useEffect(() => {
    fetch("/api/report")
      .then(r => r.json())
      .then(d => {
        setReport(d);
        setLoading(false);
        // 마지막 업데이트 시간
        const now = new Date();
        setLastUpdated(`${now.getHours()}:${String(now.getMinutes()).padStart(2, "0")} 기준`);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", background: "#0a0a0a", color: "#444", fontFamily: "monospace", fontSize: 13 }}>
      로딩 중...
    </div>
  );
  if (!report) return (
    <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", background: "#0a0a0a", color: "#ff4560", fontFamily: "monospace", fontSize: 13 }}>
      리포트를 불러올 수 없습니다.
    </div>
  );

  const { data: d, scores, analysis, verdict, date } = report;
  const vc = verdictColor[verdict];

  return (
    <div style={{ background: "#0a0a0a", minHeight: "100vh", color: "#e8e8e8", fontFamily: "'IBM Plex Mono', monospace" }}>

      {/* 헤더 */}
      <div style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", padding: "16px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", position: "sticky", top: 0, background: "#0a0a0a", zIndex: 100 }}>
        <div>
          <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.2em" }}>MACRO</span>
          <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.2em", color: "#00ff9d" }}> SENTINEL</span>
        </div>
        <div style={{ fontSize: 10, color: "#444" }}>{date} · {lastUpdated}</div>
      </div>

      <div style={{ maxWidth: 680, margin: "0 auto", padding: "20px 16px 60px" }}>

        {/* 판정 배너 */}
        <div style={{
          border: `1px solid ${vc}33`,
          borderLeft: `4px solid ${vc}`,
          borderRadius: 12, padding: "20px 24px", marginBottom: 20,
          background: `${vc}08`,
        }}>
          <div style={{ fontSize: 10, color: "#555", letterSpacing: "0.15em", marginBottom: 8 }}>MACRO SENTINEL 최종 판정</div>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 16, flexWrap: "wrap" }}>
            <div>
              <div style={{ fontSize: 36, fontWeight: 700, color: vc, letterSpacing: "0.1em", lineHeight: 1 }}>{verdict}</div>
              <div style={{ fontSize: 12, color: "#888", marginTop: 6 }}>{verdictLabel[verdict]}</div>
            </div>
            <div style={{ fontSize: 11, color: "#666", lineHeight: 1.8, maxWidth: 340 }}>
              {analysis.verdict_reason}
            </div>
          </div>
        </div>

        {/* 스코어카드 한 줄 */}
        <div style={{ display: "flex", gap: 6, marginBottom: 20, flexWrap: "wrap" }}>
          <ScoreBadge label="VIX" score={scores.vix} />
          <ScoreBadge label="금리곡선" score={scores.curve} />
          <ScoreBadge label="HY스프레드" score={scores.hy_spread} />
          <ScoreBadge label="금리수준" score={scores.rates} />
          <ScoreBadge label="달러" score={scores.dxy} />
          <ScoreBadge label="실질금리" score={scores.tips} />
          <ScoreBadge label="섹터" score={scores.sector} />
        </div>

        {/* 아코디언 카드들 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>

          {/* 주요 지수 */}
          <AccordionCard
            icon="📊"
            title="주요 지수"
            summary={`S&P ${fmt(d.indices.sp500.close, 0)}  ${chgStr(d.indices.sp500.change_pct)}  ·  VIX ${fmt(d.indices.vix.close)}`}
            score={scores.vix}
          >
            <Row label="S&P 500"     value={`${fmt(d.indices.sp500.close, 0)}  (${chgStr(d.indices.sp500.change_pct)})`}    color={chgColor(d.indices.sp500.change_pct)}    bar={d.indices.sp500.pct_52w ?? undefined} />
            <Row label="Nasdaq 100"  value={`${fmt(d.indices.nasdaq100.close, 0)}  (${chgStr(d.indices.nasdaq100.change_pct)})`} color={chgColor(d.indices.nasdaq100.change_pct)} bar={d.indices.nasdaq100.pct_52w ?? undefined} />
            <Row label="Russell 2000" value={`${fmt(d.indices.russell.close, 0)}  (${chgStr(d.indices.russell.change_pct)})`}  color={chgColor(d.indices.russell.change_pct)}  bar={d.indices.russell.pct_52w ?? undefined} />
            <Row label="VIX"         value={fmt(d.indices.vix.close)}  color={d.indices.vix.close != null && d.indices.vix.close > 25 ? "#ff4560" : d.indices.vix.close != null && d.indices.vix.close > 18 ? "#ffd000" : "#00ff9d"} />
            <div style={{ marginTop: 12, fontSize: 11, color: "#555" }}>막대: 52주 내 위치 (오른쪽 = 고점 근처)</div>
          </AccordionCard>

          {/* 금리 & 스프레드 */}
          <AccordionCard
            icon="💵"
            title="금리 · 스프레드"
            summary={`10Y ${fmt(d.rates.us10y.value)}%  ·  2s10s ${fmt(d.spreads.us2s10s.value)}%`}
            score={scores.rates}
          >
            <Row label="2Y 국채"          value={`${fmt(d.rates.us2y.value)}%`} />
            <Row label="10Y 국채"         value={`${fmt(d.rates.us10y.value)}%`} color={scores.rates === "green" ? "#00ff9d" : scores.rates === "yellow" ? "#ffd000" : "#ff4560"} />
            <Row label="TIPS 실질금리"    value={`${fmt(d.rates.tips10y.value)}%`} color={scores.tips === "green" ? "#00ff9d" : scores.tips === "yellow" ? "#ffd000" : "#ff4560"} />
            <Row label="2s10s 스프레드"   value={`${fmt(d.spreads.us2s10s.value)}%`} color={d.spreads.us2s10s.value != null && d.spreads.us2s10s.value >= 0 ? "#00ff9d" : "#ff4560"} />
            <Row label="HY 크레딧 스프레드" value={`${fmt(d.spreads.hy_spread.value)}%`} color={scores.hy_spread === "green" ? "#00ff9d" : scores.hy_spread === "yellow" ? "#ffd000" : "#ff4560"} />
            <div style={{ marginTop: 12, padding: "10px 14px", background: "rgba(255,255,255,0.03)", borderRadius: 8, fontSize: 11, color: "#777", lineHeight: 1.7 }}>
              {analysis.section1_fed}
            </div>
          </AccordionCard>

          {/* 환율 & 원자재 */}
          <AccordionCard
            icon="🌍"
            title="환율 · 원자재"
            summary={`DXY ${fmt(d.fx.dxy.close)}  ·  KRW ${fmt(d.fx.usdkrw.close, 0)}  ·  Gold $${fmt(d.commodities.gold.close, 0)}`}
            score={scores.dxy}
          >
            <Row label="DXY"     value={`${fmt(d.fx.dxy.close)}  (${chgStr(d.fx.dxy.change_pct)})`}    color={chgColor(d.fx.dxy.change_pct ? -d.fx.dxy.change_pct : null)} />
            <Row label="USD/KRW" value={`${fmt(d.fx.usdkrw.close, 0)}  (${chgStr(d.fx.usdkrw.change_pct)})`} color={chgColor(d.fx.usdkrw.change_pct)} />
            <Row label="USD/JPY" value={`${fmt(d.fx.usdjpy.close)}  (${chgStr(d.fx.usdjpy.change_pct)})`} />
            <Row label="EUR/USD" value={`${fmt(d.fx.eurusd.close)}  (${chgStr(d.fx.eurusd.change_pct)})`} />
            <Row label="WTI Oil" value={`$${fmt(d.commodities.wti.close)}  (${chgStr(d.commodities.wti.change_pct)})`} color={chgColor(d.commodities.wti.change_pct)} />
            <Row label="Gold"    value={`$${fmt(d.commodities.gold.close, 0)}  (${chgStr(d.commodities.gold.change_pct)})`} color={chgColor(d.commodities.gold.change_pct)} />
            <div style={{ marginTop: 12, padding: "10px 14px", background: "rgba(255,255,255,0.03)", borderRadius: 8, fontSize: 11, color: "#777", lineHeight: 1.7 }}>
              {analysis.section2_flow}
            </div>
          </AccordionCard>

          {/* 섹터 */}
          <AccordionCard
            icon="🔄"
            title="섹터 로테이션"
            summary={`Tech ${chgStr(d.sectors.tech.change_pct)}  ·  Fin ${chgStr(d.sectors.financials.change_pct)}  ·  Energy ${chgStr(d.sectors.energy.change_pct)}`}
            score={scores.sector}
          >
            {Object.entries(d.sectors).map(([name, v]) => (
              <Row key={name} label={name.toUpperCase()} value={chgStr(v.change_pct)} color={chgColor(v.change_pct)} bar={v.pct_52w ?? undefined} />
            ))}
            <div style={{ marginTop: 12, padding: "10px 14px", background: "rgba(255,255,255,0.03)", borderRadius: 8, fontSize: 11, color: "#777", lineHeight: 1.7 }}>
              {analysis.section3_sector}
            </div>
          </AccordionCard>

          {/* AI 분석 */}
          <AccordionCard
            icon="🤖"
            title="AI 매크로 분석"
            summary={analysis.section0_summary.slice(0, 50) + "..."}
          >
            {/* Bull / Bear */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 14 }}>
              <div style={{ padding: "12px 14px", background: "rgba(0,255,157,0.05)", border: "1px solid rgba(0,255,157,0.15)", borderRadius: 8 }}>
                <div style={{ fontSize: 10, color: "#00ff9d", letterSpacing: "0.1em", marginBottom: 6 }}>✅ BULL</div>
                <div style={{ fontSize: 11, color: "#999", lineHeight: 1.7 }}>{analysis.bull_case}</div>
              </div>
              <div style={{ padding: "12px 14px", background: "rgba(255,69,96,0.05)", border: "1px solid rgba(255,69,96,0.15)", borderRadius: 8 }}>
                <div style={{ fontSize: 10, color: "#ff4560", letterSpacing: "0.1em", marginBottom: 6 }}>❌ BEAR</div>
                <div style={{ fontSize: 11, color: "#999", lineHeight: 1.7 }}>{analysis.bear_case}</div>
              </div>
            </div>
            {/* 리스크 */}
            <div style={{ padding: "10px 14px", background: "rgba(255,208,0,0.04)", border: "1px solid rgba(255,208,0,0.12)", borderRadius: 8, marginBottom: 14 }}>
              <div style={{ fontSize: 10, color: "#ffd000", letterSpacing: "0.1em", marginBottom: 6 }}>⚠️ 리스크</div>
              <div style={{ fontSize: 11, color: "#999", lineHeight: 1.7 }}>{analysis.section4_risk}</div>
            </div>
            {/* 진입 트리거 */}
            {analysis.entry_triggers?.length > 0 && (
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 10, color: "#555", letterSpacing: "0.1em", marginBottom: 8 }}>진입 트리거</div>
                {analysis.entry_triggers.map((t, i) => (
                  <div key={i} style={{ display: "flex", gap: 8, padding: "6px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                    <span style={{ color: "#ffd000", fontSize: 10 }}>#{i + 1}</span>
                    <span style={{ fontSize: 11, color: "#888", lineHeight: 1.6 }}>{t}</span>
                  </div>
                ))}
              </div>
            )}
          </AccordionCard>

          {/* 이벤트 캘린더 */}
          {analysis.key_events?.length > 0 && (
            <AccordionCard
              icon="📅"
              title="핵심 이벤트 캘린더"
              summary={`향후 주요 일정 ${analysis.key_events.length}개`}
            >
              {analysis.key_events.map((e, i) => (
                <div key={i} style={{ display: "flex", gap: 12, padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.04)", flexWrap: "wrap" }}>
                  <span style={{ color: "#ffd000", fontSize: 11, minWidth: 70, fontFamily: "monospace" }}>{e.date}</span>
                  <div>
                    <div style={{ fontSize: 12, color: "#ccc" }}>{e.event}</div>
                    <div style={{ fontSize: 11, color: "#555", marginTop: 2 }}>{e.impact}</div>
                  </div>
                </div>
              ))}
            </AccordionCard>
          )}

        </div>

        {/* 푸터 */}
        <div style={{ textAlign: "center", padding: "32px 0 0", fontSize: 10, color: "#2a2a2a", letterSpacing: "0.08em" }}>
          MACRO SENTINEL · FRED + Yahoo Finance · Groq LLaMA · 투자 조언 아님
        </div>
      </div>
    </div>
  );
}
