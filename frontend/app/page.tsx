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
const colorMap: Record<string, string> = {
  green: "#00ff9d", yellow: "#ffd000", red: "#ff4560", gray: "#666"
};
const verdictColor: Record<string, string> = {
  NOW: "#00ff9d", WAIT: "#ffd000", AVOID: "#ff4560"
};
const verdictLabel: Record<string, string> = {
  NOW: "지금 진입 가능", WAIT: "트리거 대기", AVOID: "진입 금지"
};
const scoreLabel: Record<string, string> = {
  green: "🟢", yellow: "🟡", red: "🔴", gray: "⚫"
};
const fmt = (v: number | null, dec = 2) =>
  v == null ? "—" : v.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
const chgColor = (v: number | null) =>
  v == null ? "#aaa" : v >= 0 ? "#00ff9d" : "#ff4560";

// ── 서브 컴포넌트 ──────────────────────────────────────
function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.03)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: 12,
      padding: "20px 24px",
      marginBottom: 20,
    }}>
      <div style={{ fontSize: 11, letterSpacing: "0.15em", color: "#666", textTransform: "uppercase", marginBottom: 14 }}>
        {title}
      </div>
      {children}
    </div>
  );
}

function Row({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "7px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
      <span style={{ color: "#888", fontSize: 13 }}>{label}</span>
      <span style={{ color: color || "#e8e8e8", fontSize: 13, fontWeight: 600, textAlign: "right" }}>
        {value}
        {sub && <span style={{ color: "#555", fontSize: 11, marginLeft: 6 }}>{sub}</span>}
      </span>
    </div>
  );
}

function ScoreBar({ scores }: { scores: Scores }) {
  const items = [
    { key: "vix",       label: "VIX" },
    { key: "curve",     label: "금리곡선" },
    { key: "hy_spread", label: "HY스프레드" },
    { key: "rates",     label: "금리수준" },
    { key: "dxy",       label: "달러" },
    { key: "tips",      label: "실질금리" },
    { key: "sector",    label: "섹터" },
  ];
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      {items.map(i => (
        <div key={i.key} style={{
          display: "flex", flexDirection: "column", alignItems: "center",
          background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: "10px 14px",
          border: `1px solid ${colorMap[(scores as any)[i.key]]}33`,
          minWidth: 70,
        }}>
          <span style={{ fontSize: 18 }}>{scoreLabel[(scores as any)[i.key]]}</span>
          <span style={{ fontSize: 10, color: "#666", marginTop: 4, letterSpacing: "0.05em" }}>{i.label}</span>
        </div>
      ))}
    </div>
  );
}

// ── 메인 ──────────────────────────────────────────────
export default function Home() {
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/report")
      .then(r => r.json())
      .then(d => { setReport(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", background: "#0a0a0a", color: "#444", fontFamily: "monospace" }}>
      데이터 로딩 중...
    </div>
  );
  if (!report) return (
    <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", background: "#0a0a0a", color: "#ff4560", fontFamily: "monospace" }}>
      리포트를 불러올 수 없습니다. GitHub Actions가 실행됐는지 확인하세요.
    </div>
  );

  const { data: d, scores, analysis, verdict, date } = report;

  return (
    <div style={{ background: "#0a0a0a", minHeight: "100vh", color: "#e8e8e8", fontFamily: "'IBM Plex Mono', 'Courier New', monospace" }}>
      {/* 헤더 */}
      <div style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", padding: "18px 32px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.2em", color: "#e8e8e8" }}>MACRO</span>
          <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.2em", color: "#00ff9d" }}> SENTINEL</span>
        </div>
        <div style={{ fontSize: 11, color: "#444", letterSpacing: "0.1em" }}>기준일 {date}</div>
      </div>

      <div style={{ maxWidth: 960, margin: "0 auto", padding: "32px 24px" }}>

        {/* 판정 배너 */}
        <div style={{
          border: `1px solid ${verdictColor[verdict]}44`,
          borderLeft: `4px solid ${verdictColor[verdict]}`,
          borderRadius: 8, padding: "20px 28px", marginBottom: 28,
          background: `${verdictColor[verdict]}08`,
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <div>
            <div style={{ fontSize: 11, color: "#555", letterSpacing: "0.15em", marginBottom: 6 }}>MACRO SENTINEL 최종 판정</div>
            <div style={{ fontSize: 32, fontWeight: 700, color: verdictColor[verdict], letterSpacing: "0.1em" }}>{verdict}</div>
            <div style={{ fontSize: 13, color: "#888", marginTop: 4 }}>{verdictLabel[verdict]}</div>
          </div>
          <div style={{ textAlign: "right", maxWidth: 420 }}>
            <div style={{ fontSize: 12, color: "#666", lineHeight: 1.7 }}>{analysis.verdict_reason}</div>
          </div>
        </div>

        {/* 스코어카드 */}
        <Card title="종합 스코어카드">
          <ScoreBar scores={scores} />
        </Card>

        {/* 2열 레이아웃 */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>

          {/* 주요 지수 */}
          <Card title="주요 지수">
            <Row label="S&P 500"    value={fmt(d.indices.sp500.close, 0)}    sub={`52w ${fmt(d.indices.sp500.pct_52w, 0)}%`}    color={chgColor(d.indices.sp500.change_pct)} />
            <Row label="Nasdaq 100" value={fmt(d.indices.nasdaq100.close, 0)} sub={`52w ${fmt(d.indices.nasdaq100.pct_52w, 0)}%`} color={chgColor(d.indices.nasdaq100.change_pct)} />
            <Row label="Russell 2000" value={fmt(d.indices.russell.close, 0)} sub={`52w ${fmt(d.indices.russell.pct_52w, 0)}%`}  color={chgColor(d.indices.russell.change_pct)} />
            <Row label="VIX"        value={fmt(d.indices.vix.close)}          color={d.indices.vix.close != null && d.indices.vix.close > 25 ? "#ff4560" : d.indices.vix.close != null && d.indices.vix.close > 18 ? "#ffd000" : "#00ff9d"} />
          </Card>

          {/* 금리 & 스프레드 */}
          <Card title="금리 · 스프레드">
            <Row label="2Y 국채"       value={`${fmt(d.rates.us2y.value)}%`} />
            <Row label="10Y 국채"      value={`${fmt(d.rates.us10y.value)}%`} />
            <Row label="TIPS 실질금리" value={`${fmt(d.rates.tips10y.value)}%`} />
            <Row label="2s10s 스프레드" value={`${fmt(d.spreads.us2s10s.value)}%`}
              color={d.spreads.us2s10s.value != null && d.spreads.us2s10s.value >= 0 ? "#00ff9d" : "#ff4560"} />
            <Row label="HY 크레딧 스프레드" value={`${fmt(d.spreads.hy_spread.value)}%`}
              color={d.spreads.hy_spread.value != null && d.spreads.hy_spread.value < 4 ? "#00ff9d" : d.spreads.hy_spread.value != null && d.spreads.hy_spread.value < 5.5 ? "#ffd000" : "#ff4560"} />
          </Card>

          {/* 환율 & 원자재 */}
          <Card title="환율 · 원자재">
            <Row label="DXY"      value={fmt(d.fx.dxy.close)}      color={chgColor(d.fx.dxy.change_pct ? -d.fx.dxy.change_pct : null)} />
            <Row label="USD/KRW"  value={fmt(d.fx.usdkrw.close, 0)} />
            <Row label="USD/JPY"  value={fmt(d.fx.usdjpy.close)}   />
            <Row label="EUR/USD"  value={fmt(d.fx.eurusd.close)}   />
            <Row label="WTI Oil"  value={`$${fmt(d.commodities.wti.close)}`}  color={chgColor(d.commodities.wti.change_pct)} />
            <Row label="Gold"     value={`$${fmt(d.commodities.gold.close, 0)}`} color={chgColor(d.commodities.gold.change_pct)} />
          </Card>

          {/* 섹터 */}
          <Card title="섹터 ETF (일간 등락)">
            {Object.entries(d.sectors).map(([name, v]) => (
              <Row key={name} label={name.toUpperCase()} value={v.change_pct != null ? `${v.change_pct > 0 ? "+" : ""}${fmt(v.change_pct)}%` : "—"} color={chgColor(v.change_pct)} />
            ))}
          </Card>
        </div>

        {/* AI 분석 섹션 */}
        <Card title="매크로 분석 (Gemini)">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            {[
              { label: "시장 좌표", text: analysis.section0_summary },
              { label: "Fed · 금리 · 유동성", text: analysis.section1_fed },
              { label: "글로벌 자금흐름 · 달러", text: analysis.section2_flow },
              { label: "섹터 로테이션", text: analysis.section3_sector },
            ].map(({ label, text }) => (
              <div key={label}>
                <div style={{ fontSize: 10, color: "#555", letterSpacing: "0.12em", marginBottom: 8 }}>{label.toUpperCase()}</div>
                <div style={{ fontSize: 12, color: "#999", lineHeight: 1.8 }}>{text}</div>
              </div>
            ))}
          </div>
        </Card>

        {/* Bull / Bear */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          <Card title="✅ Bull 논거">
            <div style={{ fontSize: 12, color: "#00ff9d", lineHeight: 1.8 }}>{analysis.bull_case}</div>
          </Card>
          <Card title="❌ Bear 논거">
            <div style={{ fontSize: 12, color: "#ff4560", lineHeight: 1.8 }}>{analysis.bear_case}</div>
          </Card>
        </div>

        {/* 지정학 리스크 */}
        <Card title="⚠️ 지정학 · 정책 리스크">
          <div style={{ fontSize: 12, color: "#999", lineHeight: 1.8 }}>{analysis.section4_risk}</div>
        </Card>

        {/* 진입 트리거 */}
        {analysis.entry_triggers?.length > 0 && (
          <Card title="진입 트리거 조건">
            {analysis.entry_triggers.map((t, i) => (
              <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "6px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                <span style={{ color: "#ffd000", fontSize: 11, marginTop: 2 }}>#{i + 1}</span>
                <span style={{ fontSize: 12, color: "#999", lineHeight: 1.7 }}>{t}</span>
              </div>
            ))}
          </Card>
        )}

        {/* 이벤트 캘린더 */}
        {analysis.key_events?.length > 0 && (
          <Card title="향후 핵심 이벤트">
            {analysis.key_events.map((e, i) => (
              <div key={i} style={{ display: "flex", gap: 16, padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.04)", alignItems: "flex-start" }}>
                <span style={{ color: "#ffd000", fontSize: 11, minWidth: 80, fontFamily: "monospace" }}>{e.date}</span>
                <span style={{ fontSize: 12, color: "#ccc", minWidth: 140 }}>{e.event}</span>
                <span style={{ fontSize: 12, color: "#666", lineHeight: 1.6 }}>{e.impact}</span>
              </div>
            ))}
          </Card>
        )}

        {/* 푸터 */}
        <div style={{ textAlign: "center", padding: "24px 0", fontSize: 10, color: "#333", letterSpacing: "0.1em" }}>
          MACRO SENTINEL · 데이터: FRED + Yahoo Finance · 분석: Gemini · 투자 조언 아님
        </div>
      </div>
    </div>
  );
}
