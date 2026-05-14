"use client";

import { useCallback, useEffect, useState, type ElementType } from "react";
import { investorApi } from "@/lib/api";
import type { InvestorMetric, InvestorSummary, ScoreComponent } from "@/lib/types";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Building2,
  CalendarRange,
  CheckCircle2,
  CircleAlert,
  Flame,
  Gauge,
  LineChart,
  Scale,
  ShieldCheck,
  TrendingUp,
  Wallet,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useCurrency } from "@/components/CurrencyContext";

const METRIC_CHROME: Record<
  string,
  { icon: ElementType; color: string; bg: string }
> = {
  revenue_window: {
    icon: TrendingUp,
    color: "var(--accent)",
    bg: "var(--accent-soft)",
  },
  avg_monthly_spend: {
    icon: Flame,
    color: "var(--danger)",
    bg: "var(--danger-soft)",
  },
  net_cash_flow: {
    icon: Wallet,
    color: "var(--info)",
    bg: "var(--info-soft)",
  },
  operating_margin: {
    icon: Scale,
    color: "var(--warning)",
    bg: "color-mix(in srgb, var(--warning) 16%, transparent)",
  },
  revenue_coverage: {
    icon: ShieldCheck,
    color: "var(--success, var(--accent))",
    bg: "color-mix(in srgb, var(--accent) 18%, transparent)",
  },
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function compactNumber(value: number) {
  const absolute = Math.abs(value);
  if (absolute >= 1_000_000_000) return `${value < 0 ? "-" : ""}${(absolute / 1_000_000_000).toFixed(1)}B`;
  if (absolute >= 1_000_000) return `${value < 0 ? "-" : ""}${(absolute / 1_000_000).toFixed(1)}M`;
  if (absolute >= 1_000) return `${value < 0 ? "-" : ""}${(absolute / 1_000).toFixed(0)}K`;
  return `${value.toFixed(0)}`;
}

function humanizeLabel(value: string) {
  return value
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatPeriodLabel(period: string) {
  const date = new Date(`${period}-01T00:00:00`);
  if (Number.isNaN(date.getTime())) return period;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    year: "numeric",
  }).format(date);
}

function getHealthColor(score: number) {
  if (score >= 71) return "var(--accent)";
  if (score >= 41) return "var(--warning)";
  return "var(--danger)";
}

function getStatusColor(status: ScoreComponent["status"]) {
  if (status === "excellent") return "var(--accent)";
  if (status === "good") return "var(--info)";
  if (status === "fair") return "var(--warning)";
  return "var(--danger)";
}

function MetricCard({ metric }: { metric: InvestorMetric }) {
  const chrome = METRIC_CHROME[metric.id] ?? {
    icon: Activity,
    color: "var(--text)",
    bg: "var(--surface)",
  };
  const Icon = chrome.icon;
  const showDelta = metric.delta && metric.delta !== "N/A";

  return (
    <div
      className="glass relative overflow-hidden p-5"
      style={{
        borderColor: `${chrome.color}22`,
        background:
          "linear-gradient(180deg, color-mix(in srgb, var(--surface) 82%, transparent), color-mix(in srgb, var(--bg) 88%, transparent))",
      }}
    >
      <div
        aria-hidden
        className="absolute inset-x-0 top-0 h-px"
        style={{ background: `linear-gradient(90deg, transparent, ${chrome.color}, transparent)` }}
      />
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.22em]" style={{ color: "var(--text-dim)" }}>
            {metric.label}
          </p>
          <p className="mt-3 text-2xl font-semibold tracking-tight" style={{ color: chrome.color }}>
            {metric.value}
          </p>
        </div>
        <div
          className="flex items-center justify-center rounded-2xl"
          style={{ width: 42, height: 42, background: chrome.bg }}
        >
          <Icon size={18} style={{ color: chrome.color }} />
        </div>
      </div>
      <div className="mt-4 flex items-center gap-2 text-xs">
        {showDelta ? (
          <>
            {metric.positive ? (
              <ArrowUpRight size={14} style={{ color: "var(--accent)" }} />
            ) : (
              <ArrowDownRight size={14} style={{ color: "var(--danger)" }} />
            )}
            <span style={{ color: metric.positive ? "var(--accent)" : "var(--danger)" }}>
              {metric.delta}
            </span>
          </>
        ) : (
          <span style={{ color: "var(--text-dim)" }}>Snapshot</span>
        )}
        <span style={{ color: "var(--text-muted)" }}>{metric.note}</span>
      </div>
    </div>
  );
}

export default function InvestorPage() {
  const { formatAmount: fmt } = useCurrency();
  const [summary, setSummary] = useState<InvestorSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadInvestorData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await investorApi.getSummary();
      setSummary(data);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load investor data. Please try again.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInvestorData();
  }, [loadInvestorData]);

  if (loading && !summary) {
    return (
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="glass h-48 animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="glass h-36 animate-pulse" />
          ))}
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-[1.6fr_1fr] gap-6">
          <div className="glass h-96 animate-pulse" />
          <div className="glass h-96 animate-pulse" />
        </div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div
        className="glass max-w-2xl mx-auto p-8 flex flex-col gap-4"
        style={{ borderColor: "var(--danger)33" }}
      >
        <div className="flex items-center gap-3">
          <AlertTriangle size={18} style={{ color: "var(--danger)" }} />
          <h1 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
            Investor view is unavailable
          </h1>
        </div>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          {error ?? "We could not load the investor summary."}
        </p>
        <button
          onClick={loadInvestorData}
          className="w-fit px-4 py-2 rounded-xl text-sm font-medium"
          style={{ background: "var(--danger)", color: "#fff" }}
        >
          Retry
        </button>
      </div>
    );
  }

  const healthColor = getHealthColor(summary.health_score);
  const healthCircumference = 2 * Math.PI * 44;

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {error && (
        <div
          className="glass p-4 flex items-center gap-3"
          style={{ borderColor: "var(--warning)33", background: "var(--warning-soft)" }}
        >
          <CircleAlert size={18} style={{ color: "var(--warning)" }} />
          <p className="text-sm" style={{ color: "var(--warning)" }}>
            {error}
          </p>
        </div>
      )}

      <section
        className="glass relative overflow-hidden p-6 md:p-8"
        style={{
          borderColor: summary.data_quality.historical ? "var(--warning)33" : "var(--accent)33",
          background:
            "radial-gradient(circle at top left, color-mix(in srgb, var(--accent) 14%, transparent), transparent 32%), radial-gradient(circle at 88% 16%, color-mix(in srgb, var(--warning) 12%, transparent), transparent 26%), linear-gradient(180deg, color-mix(in srgb, var(--surface) 90%, transparent), color-mix(in srgb, var(--bg) 94%, transparent))",
        }}
      >
        <div
          aria-hidden
          className="absolute -top-14 right-[-4rem] h-40 w-40 rounded-full blur-3xl"
          style={{ background: "color-mix(in srgb, var(--accent) 20%, transparent)" }}
        />
        <div className="relative grid grid-cols-1 xl:grid-cols-[1.45fr_0.85fr] gap-6">
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className="px-3 py-1 rounded-full text-[11px] uppercase tracking-[0.22em] font-semibold"
                style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
              >
                Investor View
              </span>
              <span
                className="px-3 py-1 rounded-full text-[11px] uppercase tracking-[0.18em] font-semibold"
                style={{
                  background: summary.data_quality.historical ? "var(--warning-soft)" : "var(--info-soft)",
                  color: summary.data_quality.historical ? "var(--warning)" : "var(--info)",
                }}
              >
                {summary.data_quality.historical ? "Historical Snapshot" : "Current Snapshot"}
              </span>
              <span
                className="px-3 py-1 rounded-full text-[11px] uppercase tracking-[0.18em] font-semibold"
                style={{ background: "var(--surface)", color: "var(--text-dim)" }}
              >
                Read Only
              </span>
            </div>

            <div>
              <div className="flex items-center gap-3">
                <Building2 size={22} style={{ color: "var(--accent)" }} />
                <h1 className="text-3xl md:text-4xl font-semibold tracking-tight" style={{ color: "var(--text)" }}>
                  {summary.company.name}
                </h1>
              </div>
              <p className="mt-3 text-sm md:text-base" style={{ color: "var(--text-muted)" }}>
                {summary.company.industry} · Reporting window {formatDate(summary.data_quality.window_start)} to{" "}
                {formatDate(summary.data_quality.window_end)}
              </p>
            </div>

            <p
              className="max-w-4xl text-[15px] leading-7"
              style={{ color: "var(--text)" }}
            >
              {summary.narrative}
            </p>

            <div
              className="rounded-3xl p-4 md:p-5"
              style={{
                background: "linear-gradient(135deg, color-mix(in srgb, var(--surface) 86%, transparent), color-mix(in srgb, var(--bg) 95%, transparent))",
                border: "1px solid var(--border)",
              }}
            >
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>
                <CalendarRange size={14} />
                Data quality
              </div>
              <p className="mt-3 text-sm leading-6" style={{ color: "var(--text-muted)" }}>
                {summary.data_quality.note}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 xl:grid-cols-1 gap-4">
            <div
              className="rounded-3xl p-5"
              style={{
                background: "linear-gradient(180deg, color-mix(in srgb, var(--surface) 92%, transparent), color-mix(in srgb, var(--bg) 96%, transparent))",
                border: "1px solid var(--border)",
              }}
            >
              <p className="text-[11px] uppercase tracking-[0.22em]" style={{ color: "var(--text-dim)" }}>
                Data as of
              </p>
              <p className="mt-3 text-xl font-semibold" style={{ color: "var(--text)" }}>
                {formatDate(summary.data_quality.as_of)}
              </p>
              <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
                Latest transaction date in this workspace
              </p>
            </div>
            <div
              className="rounded-3xl p-5"
              style={{
                background: "linear-gradient(180deg, color-mix(in srgb, var(--surface) 92%, transparent), color-mix(in srgb, var(--bg) 96%, transparent))",
                border: "1px solid var(--border)",
              }}
            >
              <p className="text-[11px] uppercase tracking-[0.22em]" style={{ color: "var(--text-dim)" }}>
                Observed months
              </p>
              <p className="mt-3 text-xl font-semibold" style={{ color: "var(--text)" }}>
                {summary.data_quality.observed_months}
              </p>
              <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
                Months with activity used in the investor brief
              </p>
            </div>
            <div
              className="rounded-3xl p-5"
              style={{
                background: "linear-gradient(180deg, color-mix(in srgb, var(--surface) 92%, transparent), color-mix(in srgb, var(--bg) 96%, transparent))",
                border: "1px solid var(--border)",
              }}
            >
              <p className="text-[11px] uppercase tracking-[0.22em]" style={{ color: "var(--text-dim)" }}>
                Operating stage
              </p>
              <p className="mt-3 text-xl font-semibold" style={{ color: "var(--text)" }}>
                {humanizeLabel(summary.health_stage)}
              </p>
              <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
                Health model weighting profile
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
        {summary.metrics.map((metric) => (
          <MetricCard key={metric.id} metric={metric} />
        ))}
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-[1.4fr_0.9fr] gap-6">
        <div className="glass p-6 md:p-7" style={{ borderColor: "var(--accent)22" }}>
          <div className="flex items-center justify-between gap-4 mb-6">
            <div>
              <p className="text-[11px] uppercase tracking-[0.22em]" style={{ color: "var(--text-dim)" }}>
                Operating story
              </p>
              <h2 className="mt-2 text-xl font-semibold" style={{ color: "var(--text)" }}>
                Revenue vs expenses
              </h2>
            </div>
            <div className="hidden sm:flex items-center gap-3 text-xs" style={{ color: "var(--text-muted)" }}>
              <span className="inline-flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#4E8E73" }} />
                Revenue
              </span>
              <span className="inline-flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#C75C5C" }} />
                Expenses
              </span>
            </div>
          </div>
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={summary.revenue_trend}>
                <defs>
                  <linearGradient id="investorRevenue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#4E8E73" stopOpacity={0.42} />
                    <stop offset="100%" stopColor="#4E8E73" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="investorExpense" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#C75C5C" stopOpacity={0.34} />
                    <stop offset="100%" stopColor="#C75C5C" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(120,120,120,0.18)" vertical={false} />
                <XAxis dataKey="month" tick={{ fill: "#7A746B", fontSize: 12 }} tickLine={false} axisLine={false} />
                <YAxis
                  tick={{ fill: "#7A746B", fontSize: 12 }}
                  tickFormatter={(value) => compactNumber(Number(value))}
                  tickLine={false}
                  axisLine={false}
                  width={56}
                />
                <Tooltip
                  contentStyle={{
                    background: "rgba(12, 12, 12, 0.96)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: 16,
                    fontSize: 12,
                  }}
                  labelFormatter={(label, payload) => {
                    const period = payload?.[0]?.payload?.period;
                    return period ? formatPeriodLabel(period) : String(label);
                  }}
                  formatter={(value, name) => [fmt(Number(value ?? 0)), String(name)]}
                />
                <Area type="monotone" dataKey="revenue" name="Revenue" stroke="#4E8E73" fill="url(#investorRevenue)" strokeWidth={2.5} />
                <Area type="monotone" dataKey="expenses" name="Expenses" stroke="#C75C5C" fill="url(#investorExpense)" strokeWidth={2.5} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass p-6 md:p-7" style={{ borderColor: "var(--warning)22" }}>
          <div className="flex items-center gap-3 mb-6">
            <BarChart3 size={18} style={{ color: "var(--warning)" }} />
            <div>
              <p className="text-[11px] uppercase tracking-[0.22em]" style={{ color: "var(--text-dim)" }}>
                Cost structure
              </p>
              <h2 className="mt-2 text-xl font-semibold" style={{ color: "var(--text)" }}>
                Top expense categories
              </h2>
            </div>
          </div>
          <div className="space-y-4">
            {summary.expense_mix.map((item, index) => (
              <div key={item.category} className="space-y-2">
                <div className="flex items-baseline justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium" style={{ color: "var(--text)" }}>
                      {item.category}
                    </p>
                    <p className="text-xs" style={{ color: "var(--text-dim)" }}>
                      Rank #{index + 1}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                      {fmt(item.amount)}
                    </p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {item.share_pct.toFixed(1)}% of spend
                    </p>
                  </div>
                </div>
                <div
                  className="h-2.5 rounded-full overflow-hidden"
                  style={{ background: "color-mix(in srgb, var(--text) 10%, transparent)" }}
                >
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.min(item.share_pct, 100)}%`,
                      background:
                        index === 0
                          ? "linear-gradient(90deg, var(--danger), color-mix(in srgb, var(--warning) 70%, white))"
                          : "linear-gradient(90deg, var(--warning), color-mix(in srgb, var(--accent) 65%, white))",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-[0.92fr_1.08fr] gap-6">
        <div className="glass p-6 md:p-7" style={{ borderColor: `${healthColor}22` }}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-5 mb-6">
            <div className="flex items-center gap-4">
              <div className="relative flex items-center justify-center" style={{ width: 112, height: 112 }}>
                <svg viewBox="0 0 112 112" width={112} height={112}>
                  <circle cx="56" cy="56" r="44" fill="none" stroke="var(--surface-hover)" strokeWidth="10" />
                  <circle
                    cx="56"
                    cy="56"
                    r="44"
                    fill="none"
                    stroke={healthColor}
                    strokeWidth="10"
                    strokeLinecap="round"
                    strokeDasharray={`${(summary.health_score / 100) * healthCircumference} ${healthCircumference}`}
                    transform="rotate(-90 56 56)"
                  />
                </svg>
                <div className="absolute text-center">
                  <div className="text-3xl font-semibold leading-none" style={{ color: healthColor }}>
                    {summary.health_score}
                  </div>
                  <div className="mt-1 text-[11px] uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>
                    {summary.health_grade}
                  </div>
                </div>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <Gauge size={18} style={{ color: healthColor }} />
                  <p className="text-[11px] uppercase tracking-[0.22em]" style={{ color: "var(--text-dim)" }}>
                    Financial health
                  </p>
                </div>
                <h2 className="mt-2 text-2xl font-semibold" style={{ color: "var(--text)" }}>
                  {summary.health_label}
                </h2>
                <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
                  Stage model: {humanizeLabel(summary.health_stage)}
                </p>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs" style={{ color: "var(--text-dim)" }}>
              <span style={{ color: "var(--danger)" }}>0-40 Critical</span>
              <span style={{ color: "var(--warning)" }}>41-70 Caution</span>
              <span style={{ color: "var(--accent)" }}>71-100 Good</span>
            </div>
          </div>

          <div className="space-y-4">
            {summary.health_components.map((component) => {
              const ratio = component.max_score > 0 ? (component.score / component.max_score) * 100 : 0;
              const color = getStatusColor(component.status);
              return (
                <div key={component.name} className="rounded-2xl p-4" style={{ background: "var(--bg)", border: "1px solid var(--border)" }}>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium" style={{ color: "var(--text)" }}>
                        {component.name}
                      </p>
                      <p className="mt-1 text-xs leading-5" style={{ color: "var(--text-muted)" }}>
                        {component.description}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold" style={{ color }}>
                        {component.score}/{component.max_score}
                      </p>
                      <p className="text-[11px] uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>
                        {component.status}
                      </p>
                    </div>
                  </div>
                  <div className="mt-3 h-2 rounded-full overflow-hidden" style={{ background: "var(--surface-hover)" }}>
                    <div className="h-full rounded-full" style={{ width: `${Math.min(ratio, 100)}%`, background: color }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="glass p-6 md:p-7" style={{ borderColor: "var(--info)22" }}>
          <div className="flex items-center gap-3 mb-6">
            <LineChart size={18} style={{ color: "var(--info)" }} />
            <div>
              <p className="text-[11px] uppercase tracking-[0.22em]" style={{ color: "var(--text-dim)" }}>
                What investors check
              </p>
              <h2 className="mt-2 text-xl font-semibold" style={{ color: "var(--text)" }}>
                Key diligence markers
              </h2>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {summary.kpis.map((kpi) => (
              <div
                key={kpi.label}
                className="rounded-2xl p-4"
                style={{
                  background: "linear-gradient(180deg, color-mix(in srgb, var(--surface) 90%, transparent), color-mix(in srgb, var(--bg) 96%, transparent))",
                  border: "1px solid var(--border)",
                }}
              >
                <p className="text-[11px] uppercase tracking-[0.2em]" style={{ color: "var(--text-dim)" }}>
                  {kpi.label}
                </p>
                <p className="mt-3 text-2xl font-semibold" style={{ color: "var(--text)" }}>
                  {kpi.value}
                </p>
                <p
                  className="mt-2 text-xs leading-5"
                  style={{
                    color:
                      kpi.trend === "up"
                        ? "var(--accent)"
                        : kpi.trend === "down"
                        ? "var(--danger)"
                        : "var(--text-muted)",
                  }}
                >
                  {kpi.change}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="glass p-6 md:p-7" style={{ borderColor: "var(--accent)22" }}>
          <div className="flex items-center gap-3 mb-5">
            <CheckCircle2 size={18} style={{ color: "var(--accent)" }} />
            <h2 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
              Highlights
            </h2>
          </div>
          <div className="space-y-3">
            {summary.highlights.map((item) => (
              <div key={item} className="rounded-2xl p-4" style={{ background: "var(--bg)", border: "1px solid var(--border)" }}>
                <p className="text-sm leading-6" style={{ color: "var(--text)" }}>
                  {item}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="glass p-6 md:p-7" style={{ borderColor: "var(--warning)22" }}>
          <div className="flex items-center gap-3 mb-5">
            <AlertTriangle size={18} style={{ color: "var(--warning)" }} />
            <h2 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
              Risks
            </h2>
          </div>
          <div className="space-y-3">
            {summary.risks.length ? (
              summary.risks.map((item) => (
                <div key={item} className="rounded-2xl p-4" style={{ background: "var(--bg)", border: "1px solid var(--border)" }}>
                  <p className="text-sm leading-6" style={{ color: "var(--text)" }}>
                    {item}
                  </p>
                </div>
              ))
            ) : (
              <div className="rounded-2xl p-4" style={{ background: "var(--bg)", border: "1px solid var(--border)" }}>
                <p className="text-sm leading-6" style={{ color: "var(--text-muted)" }}>
                  No critical investor risks were flagged in this reporting window.
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="glass p-6 md:p-7" style={{ borderColor: "var(--info)22" }}>
          <div className="flex items-center gap-3 mb-5">
            <ShieldCheck size={18} style={{ color: "var(--info)" }} />
            <h2 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
              Recommended next moves
            </h2>
          </div>
          <div className="space-y-3">
            {summary.recommendations.map((item) => (
              <div key={item} className="rounded-2xl p-4" style={{ background: "var(--bg)", border: "1px solid var(--border)" }}>
                <p className="text-sm leading-6" style={{ color: "var(--text)" }}>
                  {item}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section
        className="glass p-5 flex flex-col md:flex-row md:items-start gap-4"
        style={{ borderColor: "var(--border)" }}
      >
        <div
          className="flex items-center justify-center rounded-2xl"
          style={{ width: 44, height: 44, background: "var(--surface)" }}
        >
          <CalendarRange size={18} style={{ color: "var(--text-dim)" }} />
        </div>
        <div className="space-y-2">
          <p className="text-sm font-medium" style={{ color: "var(--text)" }}>
            Investor memo assumptions
          </p>
          <p className="text-sm leading-6" style={{ color: "var(--text-muted)" }}>
            This view summarizes uploaded accounting activity only. It does not replace audited statements, cash-balance reconciliations, or a full fundraising dataroom, and historical imports should be refreshed before they are used for live investor conversations.
          </p>
        </div>
      </section>
    </div>
  );
}
