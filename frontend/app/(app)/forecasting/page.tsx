"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import type { ForecastResponse, ForecastPoint } from "@/lib/types";
import {
  ComposedChart, Bar, Line, Area,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine,
} from "recharts";
import {
  TrendingUp, TrendingDown, SlidersHorizontal, Sparkles,
  Target, BarChart3, Activity, ArrowDownRight, ArrowUpRight,
  ChevronDown, Zap,
} from "lucide-react";

const SCENARIOS = [
  { value: "base", label: "Base Case", icon: Target, color: "#C9A962" },
  { value: "optimistic", label: "Optimistic", icon: TrendingUp, color: "#5E9E7E" },
  { value: "pessimistic", label: "Pessimistic", icon: TrendingDown, color: "#C75050" },
];

const MONTH_OPTIONS = [
  { value: 3, label: "3 mo" },
  { value: 6, label: "6 mo" },
  { value: 12, label: "12 mo" },
  { value: 24, label: "24 mo" },
];

const fmt = (n: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency", currency: "INR",
    maximumFractionDigits: 0, notation: Math.abs(n) >= 1e6 ? "compact" : "standard",
  }).format(n);

const fmtShort = (n: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency", currency: "INR",
    maximumFractionDigits: 1, notation: "compact",
  }).format(n);

const formatPeriod = (p: string) => {
  const [y, m] = p.split("-");
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${months[parseInt(m) - 1]} '${y.slice(2)}`;
};

/* ── Custom Tooltip ─────────────────────────────────────────────── */
const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "rgba(8, 8, 8, 0.96)", backdropFilter: "blur(12px)",
      border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12,
      padding: "14px 18px", minWidth: 220, boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
    }}>
      <p style={{ color: "#9A948A", fontSize: 11, fontWeight: 600, marginBottom: 10, letterSpacing: "0.05em" }}>
        {formatPeriod(label)}
      </p>
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ display: "flex", justifyContent: "space-between", gap: 24, marginBottom: 4 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: p.color }} />
            <span style={{ color: "#9A948A", fontSize: 12 }}>{p.name}</span>
          </div>
          <span style={{ color: "#E8E4DE", fontSize: 12, fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
            {fmt(p.value)}
          </span>
        </div>
      ))}
    </div>
  );
};

/* ── Sparkline mini-chart ───────────────────────────────────────── */
const Sparkline = ({ data, color, height = 32 }: { data: number[]; color: string; height?: number }) => {
  if (!data.length) return null;
  const max = Math.max(...data.map(Math.abs));
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 80;
  const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${height - ((v - min) / range) * (height - 4)}`).join(" ");
  return (
    <svg width={w} height={height} style={{ opacity: 0.7 }}>
      <defs>
        <linearGradient id={`spark-${color.replace("#","")}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.3} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <polygon
        points={`0,${height} ${points} ${w},${height}`}
        fill={`url(#spark-${color.replace("#","")})`}
      />
      <polyline points={points} fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
};

export default function ForecastingPage() {
  const { getToken } = useAuth();
  const [scenario, setScenario] = useState("base");
  const [months, setMonths] = useState(6);
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revenueGrowth, setRevenueGrowth] = useState(12);
  const [activeTab, setActiveTab] = useState<"chart" | "table">("chart");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const token = await getToken();
      const result = await api.getForecast(scenario, months, token);
      setData(result);
      if (result.assumptions?.income_growth_rate) {
        setRevenueGrowth(Math.round(Number(result.assumptions.income_growth_rate) * 100));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load forecast");
    } finally {
      setLoading(false);
    }
  }, [getToken, scenario, months]);

  useEffect(() => { load(); }, [load]);

  const points: ForecastPoint[] = useMemo(() => {
    if (!data?.data_points) return [];
    const baseGrowth = Number(data.assumptions?.income_growth_rate ?? 0.12);
    const baseGrowthPct = Math.round(baseGrowth * 100);
    if (revenueGrowth === baseGrowthPct) return data.data_points;
    const ratio = revenueGrowth / (baseGrowthPct || 1);
    let cumNet = 0;
    return data.data_points.map((p) => {
      const adjustedIncome = Math.round(p.projected_income * ratio);
      const net = adjustedIncome - p.projected_expenses;
      cumNet += net;
      return { ...p, projected_income: adjustedIncome, projected_net: net, cumulative_net: cumNet,
        confidence_lower: Math.round(p.confidence_lower * ratio),
        confidence_upper: Math.round(p.confidence_upper * ratio),
      };
    });
  }, [data, revenueGrowth]);

  /* ── Derived metrics ──────────────────────────────────────────── */
  const totalNet = points.reduce((s, p) => s + p.projected_net, 0);
  const lastCum = points[points.length - 1]?.cumulative_net ?? 0;
  const avgIncome = points.length > 0 ? points.reduce((s, p) => s + p.projected_income, 0) / points.length : 0;
  const avgExpenses = points.length > 0 ? points.reduce((s, p) => s + p.projected_expenses, 0) / points.length : 0;
  const expenseTrend = points.length >= 2
    ? ((points[points.length-1].projected_expenses - points[0].projected_expenses) / points[0].projected_expenses * 100)
    : 0;

  const chartData = points.map((p) => ({
    ...p,
    period: p.period,
    label: formatPeriod(p.period),
    confidenceRange: [p.confidence_lower, p.confidence_upper],
  }));

  const scenarioConfig = SCENARIOS.find(s => s.value === scenario)!;

  const kpis = [
    { label: "Projected Net", value: totalNet, color: totalNet >= 0 ? "#5E9E7E" : "#C75050",
      icon: totalNet >= 0 ? TrendingUp : TrendingDown, sparkData: points.map(p => p.projected_net),
      sub: `Over ${months} months` },
    { label: "Cumulative End", value: lastCum, color: lastCum >= 0 ? "#5E9E7E" : "#C75050",
      icon: Activity, sparkData: points.map(p => p.cumulative_net),
      sub: `${formatPeriod(points[points.length-1]?.period ?? "")}` },
    { label: "Avg Income/mo", value: avgIncome, color: "#5E9E7E",
      icon: ArrowUpRight, sparkData: points.map(p => p.projected_income),
      sub: `${points.length} months projected` },
    { label: "Avg Expense/mo", value: avgExpenses, color: "#C75050",
      icon: ArrowDownRight, sparkData: points.map(p => p.projected_expenses),
      sub: `Trend: ${expenseTrend > 0 ? "+" : ""}${expenseTrend.toFixed(1)}%` },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-fade-up">
        <div>
          <div className="flex items-center gap-3">
            <div style={{ width: 40, height: 40, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center",
              background: "linear-gradient(135deg, rgba(59,130,246,0.15), rgba(139,92,246,0.15))",
              border: "1px solid rgba(59,130,246,0.2)" }}>
              <BarChart3 size={20} style={{ color: "#C9A962" }} />
            </div>
            <div>
              <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>Forecasting</h1>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-dim)" }}>
                AI-powered projections • {data?.historical_months ?? 0} months historical data •{" "}
                <span style={{ color: scenarioConfig.color }}>{scenarioConfig.label}</span>
              </p>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {SCENARIOS.map((s) => (
            <button key={s.value} onClick={() => setScenario(s.value)}
              style={{
                padding: "6px 14px", borderRadius: 8, fontSize: 12, fontWeight: 600,
                border: scenario === s.value ? `1px solid ${s.color}` : "1px solid var(--border)",
                background: scenario === s.value ? `${s.color}15` : "transparent",
                color: scenario === s.value ? s.color : "var(--text-muted)",
                cursor: "pointer", transition: "all 0.2s ease",
              }}
            >
              {s.label}
            </button>
          ))}
          <div style={{ width: 1, height: 24, background: "var(--border)", margin: "0 4px" }} />
          {MONTH_OPTIONS.map((m) => (
            <button key={m.value} onClick={() => setMonths(m.value)}
              style={{
                padding: "6px 10px", borderRadius: 8, fontSize: 12, fontWeight: 600,
                border: months === m.value ? "1px solid var(--accent)" : "1px solid var(--border)",
                background: months === m.value ? "var(--accent-soft)" : "transparent",
                color: months === m.value ? "var(--accent)" : "var(--text-dim)",
                cursor: "pointer", transition: "all 0.2s ease",
              }}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="glass px-4 py-3 text-sm rounded-xl" style={{ background: "var(--danger-soft)", color: "var(--danger)" }}>{error}</div>
      )}

      {/* ── KPI Cards ──────────────────────────────────────────── */}
      {!loading && points.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-fade-up delay-1">
          {kpis.map((kpi, idx) => (
            <div key={kpi.label} className="glass glass-hover p-5" style={{ position: "relative", overflow: "hidden" }}>
              <div style={{ position: "absolute", right: 12, bottom: 8, opacity: 0.5 }}>
                <Sparkline data={kpi.sparkData} color={kpi.color} />
              </div>
              <div className="flex items-center gap-2 mb-2">
                <div style={{
                  width: 28, height: 28, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center",
                  background: `${kpi.color}15`,
                }}>
                  <kpi.icon size={14} style={{ color: kpi.color }} />
                </div>
                <span className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>{kpi.label}</span>
              </div>
              <p className="text-xl font-bold" style={{ color: kpi.color, fontVariantNumeric: "tabular-nums" }}>{fmt(kpi.value)}</p>
              <p className="text-xs mt-1" style={{ color: "var(--text-dim)" }}>{kpi.sub}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── Scenario Slider ────────────────────────────────────── */}
      {!loading && points.length > 0 && (
        <div className="glass p-5 animate-fade-up delay-2">
          <div className="flex items-center gap-2 mb-3">
            <div style={{ width: 24, height: 24, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center",
              background: "linear-gradient(135deg, rgba(139,92,246,0.2), rgba(59,130,246,0.2))" }}>
              <SlidersHorizontal size={12} style={{ color: "#9B7CB8" }} />
            </div>
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
              Revenue Growth Sensitivity
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-xs font-mono" style={{ color: "var(--text-dim)", width: 28 }}>0%</span>
            <div style={{ flex: 1, position: "relative" }}>
              <input type="range" min={0} max={30} step={1} value={revenueGrowth}
                onChange={(e) => setRevenueGrowth(Number(e.target.value))}
                style={{ width: "100%", accentColor: "#9B7CB8", height: 6 }} />
              <div style={{
                position: "absolute", top: -28, left: `${(revenueGrowth / 30) * 100}%`, transform: "translateX(-50%)",
                background: "#9B7CB8", color: "#fff", fontSize: 10, fontWeight: 700,
                padding: "2px 8px", borderRadius: 6, whiteSpace: "nowrap",
              }}>
                {revenueGrowth}% MoM
              </div>
            </div>
            <span className="text-xs font-mono" style={{ color: "var(--text-dim)", width: 28 }}>30%</span>
          </div>
          <div className="flex items-center justify-end mt-2 gap-2">
            <Zap size={11} style={{ color: "#9B7CB8" }} />
            <span className="text-xs" style={{ color: "var(--text-dim)" }}>
              Projected net:{" "}
              <strong style={{ color: totalNet >= 0 ? "#5E9E7E" : "#C75050" }}>{fmt(totalNet)}</strong>
              {" "}over {months}mo
            </span>
          </div>
        </div>
      )}

      {/* ── Main Chart ─────────────────────────────────────────── */}
      <div className="glass p-6 animate-fade-up delay-3">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
              Cash Flow Projection
            </h2>
            <p className="text-xs mt-0.5" style={{ color: "var(--text-dim)" }}>
              {formatPeriod(points[0]?.period ?? "")} — {formatPeriod(points[points.length-1]?.period ?? "")} •{" "}
              <span style={{ color: scenarioConfig.color }}>{scenarioConfig.label} scenario</span>
            </p>
          </div>
          <div className="flex gap-1" style={{ background: "var(--card)", borderRadius: 8, padding: 2, border: "1px solid var(--border)" }}>
            {(["chart", "table"] as const).map(t => (
              <button key={t} onClick={() => setActiveTab(t)}
                style={{
                  padding: "4px 12px", borderRadius: 6, fontSize: 11, fontWeight: 600,
                  background: activeTab === t ? "var(--accent-soft)" : "transparent",
                  color: activeTab === t ? "var(--accent)" : "var(--text-dim)",
                  border: "none", cursor: "pointer", textTransform: "capitalize",
                }}>
                {t}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="skeleton" style={{ height: 380 }} />
        ) : points.length === 0 ? (
          <div className="flex flex-col items-center justify-center" style={{ height: 380 }}>
            <BarChart3 size={40} className="mb-3" style={{ color: "var(--text-dim)" }} />
            <p className="text-sm" style={{ color: "var(--text-dim)" }}>No forecast data. Add transactions first.</p>
          </div>
        ) : activeTab === "chart" ? (
          <div className="overflow-x-auto" style={{ WebkitOverflowScrolling: "touch" }}>
          <ResponsiveContainer width="100%" height={320} minWidth={500}>
            <ComposedChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="fcIncG" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#5E9E7E" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#5E9E7E" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="fcExpG" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#C75050" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#C75050" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="fcConfG" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={scenarioConfig.color} stopOpacity={0.08} />
                  <stop offset="100%" stopColor={scenarioConfig.color} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis dataKey="period" tick={{ fontSize: 11, fill: "#5C5750" }} axisLine={false} tickLine={false}
                tickFormatter={formatPeriod} />
              <YAxis tick={{ fontSize: 11, fill: "#5C5750" }} axisLine={false} tickLine={false}
                tickFormatter={(v) => fmtShort(v)} width={65} />
              <Tooltip content={<ChartTooltip />} cursor={{ stroke: "rgba(255,255,255,0.06)", strokeWidth: 1 }} />
              <Legend wrapperStyle={{ fontSize: 11, paddingTop: 12 }}
                formatter={(value: string) => <span style={{ color: "#9A948A" }}>{value}</span>} />

              {/* Confidence band */}
              <Area type="monotone" dataKey="confidence_upper" name="Confidence Upper"
                stroke="none" fill="url(#fcConfG)" legendType="none" />
              <Area type="monotone" dataKey="confidence_lower" name="Confidence Lower"
                stroke="none" fill="var(--card)" legendType="none" />

              {/* Income & Expense bars */}
              <Bar dataKey="projected_income" name="Income" fill="#5E9E7E" radius={[3, 3, 0, 0]}
                barSize={16} fillOpacity={0.85} />
              <Bar dataKey="projected_expenses" name="Expenses" fill="#C75050" radius={[3, 3, 0, 0]}
                barSize={16} fillOpacity={0.85} />

              {/* Net & Cumulative lines */}
              <Line type="monotone" dataKey="projected_net" name="Net Cash Flow"
                stroke={scenarioConfig.color} strokeWidth={2.5} dot={{ r: 4, fill: scenarioConfig.color, strokeWidth: 0 }}
                activeDot={{ r: 6, fill: scenarioConfig.color, stroke: "#fff", strokeWidth: 2 }} />
              <Line type="monotone" dataKey="cumulative_net" name="Cumulative"
                stroke="#9B7CB8" strokeWidth={2} strokeDasharray="6 3"
                dot={false} />

              <ReferenceLine y={0} stroke="rgba(255,255,255,0.1)" strokeDasharray="3 3" />
            </ComposedChart>
          </ResponsiveContainer>
          </div>
        ) : (
          /* ── Table View ───────────────────────────────────────── */
          <div className="overflow-x-auto" style={{ WebkitOverflowScrolling: "touch" }}>
            <table className="w-full text-sm" style={{ minWidth: 640 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["Period","Income","Expenses","Net","Cumulative","Confidence","Range"].map(h => (
                    <th key={h} className="text-xs font-medium uppercase tracking-wider pb-3 text-right first:text-left"
                      style={{ color: "var(--text-dim)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {points.map((p, idx) => (
                  <tr key={p.period} style={{ borderBottom: "1px solid var(--border)" }}
                    className="transition-colors hover:bg-[rgba(255,255,255,0.02)]">
                    <td className="py-3 font-medium" style={{ color: "var(--text)" }}>{formatPeriod(p.period)}</td>
                    <td className="py-3 text-right font-mono" style={{ color: "#5E9E7E" }}>{fmt(p.projected_income)}</td>
                    <td className="py-3 text-right font-mono" style={{ color: "#C75050" }}>{fmt(p.projected_expenses)}</td>
                    <td className="py-3 text-right font-semibold font-mono"
                      style={{ color: p.projected_net >= 0 ? "#5E9E7E" : "#C75050" }}>{fmt(p.projected_net)}</td>
                    <td className="py-3 text-right font-mono" style={{ color: "var(--text-muted)" }}>{fmt(p.cumulative_net)}</td>
                    <td className="py-3 text-right">
                      <span style={{
                        display: "inline-block", padding: "2px 8px", borderRadius: 6, fontSize: 10, fontWeight: 600,
                        background: `${scenarioConfig.color}15`, color: scenarioConfig.color,
                      }}>
                        {(p.confidence * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="py-3 text-right text-xs font-mono" style={{ color: "var(--text-dim)" }}>
                      {fmtShort(p.confidence_lower)} — {fmtShort(p.confidence_upper)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Model Info Footer ──────────────────────────────────── */}
      {!loading && data && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs animate-fade-up delay-4"
          style={{ color: "var(--text-dim)", padding: "0 4px" }}>
          <div className="flex items-center gap-4">
            <span>Model: <strong style={{ color: "var(--text-muted)" }}>{data.model_version}</strong></span>
            <span>Historical: <strong style={{ color: "var(--text-muted)" }}>{data.historical_months} months</strong></span>
          </div>
          <span>Last computed: {new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</span>
        </div>
      )}
    </div>
  );
}
