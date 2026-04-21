"use client";

import { useEffect, useState, useCallback } from "react";
import { investorApi, dashboardApi, healthScoreApi } from "@/lib/api";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Clock,
  Flame,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

// Investor view: read-only, clean, professional — no raw transactions

interface Metric {
  label: string;
  value: string;
  delta: string;
  positive: boolean;
  icon: React.ElementType;
  color: string;
  bg: string;
  note: string;
}

interface KPI {
  label: string;
  value: string;
  trend: string;
  change: string;
}

const DEMO_METRICS: Metric[] = [
  {
    label: "Monthly Revenue",
    value: "$28,000",
    delta: "+12%",
    positive: true,
    icon: TrendingUp,
    color: "var(--accent)",
    bg: "var(--accent-soft)",
    note: "Month-over-month",
  },
  {
    label: "Burn Rate",
    value: "$5,600/mo",
    delta: "+8%",
    positive: false,
    icon: Flame,
    color: "var(--danger)",
    bg: "var(--danger-soft)",
    note: "Rising — watch closely",
  },
  {
    label: "Cash Runway",
    value: "8 months",
    delta: "Healthy",
    positive: true,
    icon: Clock,
    color: "var(--warning)",
    bg: "var(--warning-soft)",
    note: "At current burn rate",
  },
  {
    label: "Cash Balance",
    value: "$45,200",
    delta: "",
    positive: true,
    icon: DollarSign,
    color: "var(--info)",
    bg: "var(--info-soft)",
    note: "As of Jan 15, 2025",
  },
];

const DEMO_REVENUE_TREND = [
  { month: "Aug", revenue: 18000, expenses: 14000 },
  { month: "Sep", revenue: 19500, expenses: 15200 },
  { month: "Oct", revenue: 21000, expenses: 16400 },
  { month: "Nov", revenue: 23500, expenses: 17800 },
  { month: "Dec", revenue: 25800, expenses: 19200 },
  { month: "Jan", revenue: 28000, expenses: 21600 },
];

const DEMO_KPIS: KPI[] = [
  { label: "Gross Margin", value: "62%", trend: "up", change: "+3pp" },
  { label: "MRR Growth", value: "12% MoM", trend: "up", change: "↑ 2pp" },
  { label: "Burn Multiple", value: "0.77×", trend: "up", change: "Efficient" },
  { label: "Revenue / Expense", value: "1.30×", trend: "up", change: "Positive" },
  { label: "Health Score", value: "72/100", trend: "neutral", change: "Good" },
  { label: "Top Expense", value: "Payroll", trend: "neutral", change: "45% of burn" },
];

const ICON_MAP: Record<string, React.ElementType> = {
  "Monthly Revenue": TrendingUp,
  "Burn Rate": Flame,
  "Cash Runway": Clock,
  "Cash Balance": DollarSign,
};

const COLOR_MAP: Record<string, [string, string]> = {
  "Monthly Revenue": ["var(--accent)", "var(--accent-soft)"],
  "Burn Rate": ["var(--danger)", "var(--danger-soft)"],
  "Cash Runway": ["var(--warning)", "var(--warning-soft)"],
  "Cash Balance": ["var(--info)", "var(--info-soft)"],
};

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

export default function InvestorPage() {
  const [metrics, setMetrics] = useState<Metric[]>(DEMO_METRICS);
  const [revenueTrend, setRevenueTrend] = useState(DEMO_REVENUE_TREND);
  const [kpis, setKpis] = useState<KPI[]>(DEMO_KPIS);
  const [healthScore, setHealthScore] = useState(72);
  const [healthLabel, setHealthLabel] = useState("Good");

  const loadInvestorData = useCallback(async () => {
    try {
      const data = await investorApi.getSummary();
      if (data) {
        if (data.health_score) setHealthScore(data.health_score);
        if (data.health_label) setHealthLabel(data.health_label);
        if (data.metrics?.length) {
          setMetrics(data.metrics.map((m) => ({
            ...m,
            icon: ICON_MAP[m.label] || TrendingUp,
            color: COLOR_MAP[m.label]?.[0] || "var(--text)",
            bg: COLOR_MAP[m.label]?.[1] || "var(--surface)",
          })));
        }
        if (data.revenue_trend?.length) setRevenueTrend(data.revenue_trend);
        if (data.kpis?.length) setKpis(data.kpis);
      }
    } catch {
      // API unavailable — try individual endpoints
      try {
        const hs = await healthScoreApi.get();
        if (hs?.overall_score) {
          setHealthScore(hs.overall_score);
          setHealthLabel(hs.overall_score >= 71 ? "Good" : hs.overall_score >= 41 ? "Caution" : "Critical");
        }
      } catch { /* keep defaults */ }
    }
  }, []);

  useEffect(() => {
    loadInvestorData();
  }, [loadInvestorData]);
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between animate-fade-up">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>
              Luna Bakery
            </h1>
            <span
              className="badge"
              style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
            >
              Investor View
            </span>
          </div>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Financial overview · Read-only · As of January 2025
          </p>
        </div>
        <div
          className="px-3 py-1.5 rounded-lg text-xs font-medium"
          style={{ background: "var(--accent-soft)", color: "var(--accent)", border: "1px solid var(--accent)22" }}
        >
          🔒 Read Only
        </div>
      </div>

      {/* Health Score Banner */}
      <div
        className="glass p-5 flex items-center justify-between animate-fade-up delay-1"
        style={{ borderColor: "var(--warning)33" }}
      >
        <div className="flex items-center gap-5">
          {/* Gauge */}
          <div className="relative flex items-center justify-center" style={{ width: 72, height: 72 }}>
            <svg viewBox="0 0 72 72" width={72} height={72}>
              <circle cx="36" cy="36" r="28" fill="none" stroke="var(--surface-hover)" strokeWidth="8" />
              <circle
                cx="36"
                cy="36"
                r="28"
                fill="none"
                stroke="var(--warning)"
                strokeWidth="8"
                strokeDasharray={`${(healthScore / 100) * 2 * Math.PI * 28} ${2 * Math.PI * 28}`}
                strokeDashoffset={`${0.25 * 2 * Math.PI * 28}`}
                strokeLinecap="round"
                transform="rotate(-90 36 36)"
              />
            </svg>
            <div className="absolute text-center">
              <div className="text-xl font-bold leading-none" style={{ color: "var(--warning)" }}>{healthScore}</div>
              <div className="text-xs" style={{ color: "var(--text-dim)" }}>/100</div>
            </div>
          </div>
          <div>
            <p className="font-bold" style={{ color: "var(--text)" }}>
              Financial Health Score: {healthLabel}
            </p>
            <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
              Strong runway and revenue growth. Marketing overspend is the primary drag on this score.
            </p>
          </div>
        </div>
        <div className="hidden sm:flex flex-col items-end gap-1 text-xs" style={{ color: "var(--text-dim)" }}>
          <span style={{ color: "var(--danger)" }}>● 0–40 Critical</span>
          <span style={{ color: "var(--warning)" }}>● 41–70 Caution</span>
          <span style={{ color: "var(--accent)" }}>● 71–100 Good</span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 animate-fade-up delay-2">
        {metrics.map(({ label, value, delta, positive, icon: Icon, color, bg, note }, i) => (
          <div key={label} className={`glass p-5 animate-fade-up delay-${i + 1}`}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs uppercase tracking-wider font-medium" style={{ color: "var(--text-muted)" }}>
                {label}
              </span>
              <div
                className="flex items-center justify-center"
                style={{ width: 30, height: 30, borderRadius: 8, background: bg }}
              >
                <Icon size={14} style={{ color }} />
              </div>
            </div>
            <div className="text-xl font-bold" style={{ color }}>
              {value}
            </div>
            <div className="flex items-center gap-1 mt-1">
              {delta && (
                <>
                  {positive ? (
                    <ArrowUpRight size={12} style={{ color: "var(--accent)" }} />
                  ) : (
                    <ArrowDownRight size={12} style={{ color: "var(--danger)" }} />
                  )}
                  <span className="text-xs font-medium" style={{ color: positive ? "var(--accent)" : "var(--danger)" }}>
                    {delta}
                  </span>
                </>
              )}
              <span className="text-xs ml-1" style={{ color: "var(--text-dim)" }}>
                {note}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Revenue Trend Chart */}
      <div className="glass p-6 animate-fade-up delay-3">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>
          Revenue vs. Expenses — Last 6 Months
        </h3>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={revenueTrend}>
            <defs>
              <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00E5CC" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#00E5CC" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="expGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#FF4D6A" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#FF4D6A" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1E2A42" />
            <XAxis dataKey="month" tick={{ fill: "#7A8BA7", fontSize: 11 }} />
            <YAxis
              tick={{ fill: "#7A8BA7", fontSize: 11 }}
              tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`}
            />
            <Tooltip
              contentStyle={{ background: "#141A2B", border: "1px solid #1E2A42", borderRadius: 8, fontSize: 12 }}
              formatter={(v) => fmt(Number(v ?? 0))}
            />
            <Area type="monotone" dataKey="revenue" name="Revenue" stroke="#00E5CC" fill="url(#revGrad)" strokeWidth={2} />
            <Area type="monotone" dataKey="expenses" name="Expenses" stroke="#FF4D6A" fill="url(#expGrad)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Key KPI Grid */}
      <div className="glass p-6 animate-fade-up delay-4">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>
          Key Performance Indicators
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {kpis.map(({ label, value, trend, change }) => (
            <div
              key={label}
              className="p-4 rounded-lg"
              style={{ background: "var(--bg)", border: "1px solid var(--border)" }}
            >
              <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "var(--text-dim)" }}>
                {label}
              </p>
              <p className="text-lg font-bold" style={{ color: "var(--text)" }}>
                {value}
              </p>
              <p
                className="text-xs mt-0.5 font-medium"
                style={{
                  color:
                    trend === "up"
                      ? "var(--accent)"
                      : trend === "down"
                      ? "var(--danger)"
                      : "var(--text-muted)",
                }}
              >
                {change}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Disclaimer */}
      <div
        className="glass p-4 flex items-start gap-3 animate-fade-up delay-5"
        style={{ borderColor: "var(--warning)22" }}
      >
        <span style={{ color: "var(--warning)", fontSize: 16 }}>⚠</span>
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          This report is generated for informational purposes only. Raw transaction data is not shown in this view.
          All figures are based on uploaded financial data and AI-generated analysis. Consult a qualified accountant for official statements.
        </p>
      </div>
    </div>
  );
}
