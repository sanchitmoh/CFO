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
  AlertTriangle,
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
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [revenueTrend, setRevenueTrend] = useState<{ month: string; revenue: number; expenses: number }[]>([]);
  const [kpis, setKpis] = useState<KPI[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [healthScore, setHealthScore] = useState(0);
  const [healthLabel, setHealthLabel] = useState("—");

  const loadInvestorData = useCallback(async () => {
    setLoading(true);
    setError(null);
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
      } catch {
        setError("Unable to load investor data. Please check your connection and try again.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInvestorData();
  }, [loadInvestorData]);
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {error && (
        <div className="glass p-4 flex items-center gap-3 animate-fade-up" style={{ borderColor: "var(--danger)44", background: "var(--danger-soft)" }}>
          <AlertTriangle size={18} style={{ color: "var(--danger)", flexShrink: 0 }} />
          <p className="text-sm" style={{ color: "var(--danger)" }}>{error}</p>
          <button onClick={loadInvestorData} className="ml-auto text-xs font-medium px-3 py-1.5 rounded-lg" style={{ background: "var(--danger)", color: "#fff" }}>Retry</button>
        </div>
      )}
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 animate-fade-up">
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
        className="glass p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-fade-up delay-1"
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
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-fade-up delay-2">
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
        <div className="overflow-x-auto" style={{ WebkitOverflowScrolling: "touch" }}>
        <ResponsiveContainer width="100%" height={200} minWidth={400}>
          <AreaChart data={revenueTrend}>
            <defs>
              <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#5E9E7E" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#5E9E7E" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="expGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#C75050" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#C75050" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#232323" />
            <XAxis dataKey="month" tick={{ fill: "#5C5750", fontSize: 11 }} />
            <YAxis
              tick={{ fill: "#5C5750", fontSize: 11 }}
              tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`}
            />
            <Tooltip
              contentStyle={{ background: "#111111", border: "1px solid #232323", borderRadius: 8, fontSize: 12 }}
              formatter={(v) => fmt(Number(v ?? 0))}
            />
            <Area type="monotone" dataKey="revenue" name="Revenue" stroke="#5E9E7E" fill="url(#revGrad)" strokeWidth={2} />
            <Area type="monotone" dataKey="expenses" name="Expenses" stroke="#C75050" fill="url(#expGrad)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
        </div>
      </div>

      {/* Key KPI Grid */}
      <div className="glass p-6 animate-fade-up delay-4">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>
          Key Performance Indicators
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
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
