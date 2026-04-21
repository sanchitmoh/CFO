"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import type { ForecastResponse, ForecastPoint } from "@/lib/types";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { TrendingUp, SlidersHorizontal, Sparkles } from "lucide-react";

const SCENARIOS = [
  { value: "base", label: "Base Case" },
  { value: "optimistic", label: "Optimistic" },
  { value: "pessimistic", label: "Pessimistic" },
];

const MONTH_OPTIONS = [
  { value: 3, label: "3 months" },
  { value: 6, label: "6 months" },
  { value: 12, label: "12 months" },
];

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

const CustomTooltip = ({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ color: string; name: string; value: number }>;
  label?: string;
}) => {
  if (!active || !payload) return null;
  return (
    <div className="glass p-3 text-xs space-y-1" style={{ minWidth: 160 }}>
      <p className="font-semibold mb-2" style={{ color: "var(--text)" }}>{label}</p>
      {payload.map((p) => (
        <div key={p.name} className="flex justify-between gap-4">
          <span style={{ color: p.color }}>{p.name}</span>
          <span style={{ color: "var(--text)" }}>{fmt(p.value)}</span>
        </div>
      ))}
    </div>
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

  useEffect(() => {
    load();
  }, [load]);

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
      return {
        ...p,
        projected_income: adjustedIncome,
        projected_net: net,
        cumulative_net: cumNet,
        confidence_lower: Math.round(p.confidence_lower * ratio),
        confidence_upper: Math.round(p.confidence_upper * ratio),
      };
    });
  }, [data, revenueGrowth]);

  const totalProjectedNet = points.reduce((s, p) => s + p.projected_net, 0);
  const lastCumulative = points[points.length - 1]?.cumulative_net ?? 0;
  const avgIncome = points.length > 0 ? points.reduce((s, p) => s + p.projected_income, 0) / points.length : 0;
  const avgExpenses = points.length > 0 ? points.reduce((s, p) => s + p.projected_expenses, 0) / points.length : 0;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-fade-up">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>Forecasting</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>AI-powered revenue and expense projections</p>
        </div>
        <div className="flex items-center gap-3">
          <select value={scenario} onChange={(e) => setScenario(e.target.value)} style={{ width: "auto" }}>
            {SCENARIOS.map((s) => (<option key={s.value} value={s.value}>{s.label}</option>))}
          </select>
          <select value={months} onChange={(e) => setMonths(Number(e.target.value))} style={{ width: "auto" }}>
            {MONTH_OPTIONS.map((m) => (<option key={m.value} value={m.value}>{m.label}</option>))}
          </select>
        </div>
      </div>

      {error && (
        <div className="glass px-4 py-3 text-sm rounded-xl" style={{ background: "var(--danger-soft)", color: "var(--danger)" }}>{error}</div>
      )}

      {/* Revenue Growth Slider */}
      {!loading && points.length > 0 && (
        <div className="glass p-5 animate-fade-up delay-1">
          <div className="flex items-center gap-2 mb-3">
            <SlidersHorizontal size={14} style={{ color: "var(--accent)" }} />
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
              Scenario Slider — What if revenue growth changes?
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-xs shrink-0" style={{ color: "var(--text-dim)" }}>0%</span>
            <input type="range" min={0} max={30} step={1} value={revenueGrowth} onChange={(e) => setRevenueGrowth(Number(e.target.value))} className="flex-1" style={{ accentColor: "var(--accent)", height: 6 }} />
            <span className="text-xs shrink-0" style={{ color: "var(--text-dim)" }}>30%</span>
          </div>
          <div className="flex items-center justify-between mt-2">
            <span className="text-sm font-bold" style={{ color: "var(--accent)" }}>{revenueGrowth}% MoM revenue growth</span>
            <div className="flex items-center gap-1 text-xs" style={{ color: "var(--text-dim)" }}>
              <Sparkles size={11} style={{ color: "var(--accent)" }} />
              Projected net: <strong style={{ color: totalProjectedNet >= 0 ? "var(--income)" : "var(--expense)" }}>{fmt(totalProjectedNet)}</strong> over {months}mo
            </div>
          </div>
        </div>
      )}

      {/* KPI Cards */}
      {!loading && points.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 animate-fade-up delay-2">
          {[
            { label: "Total Net", value: fmt(totalProjectedNet), color: totalProjectedNet >= 0 ? "var(--income)" : "var(--expense)" },
            { label: "Cumulative at End", value: fmt(lastCumulative), color: lastCumulative >= 0 ? "var(--income)" : "var(--expense)" },
            { label: "Avg Monthly Income", value: fmt(avgIncome), color: "var(--income)" },
            { label: "Avg Monthly Expenses", value: fmt(avgExpenses), color: "var(--expense)" },
          ].map((kpi) => (
            <div key={kpi.label} className="glass p-4 space-y-1">
              <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>{kpi.label}</p>
              <p className="text-xl font-bold" style={{ color: kpi.color }}>{kpi.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Chart */}
      <div className="glass p-6 animate-fade-up delay-3">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
            Projected Cash Flow — <span style={{ color: "var(--accent)" }}>{SCENARIOS.find((s) => s.value === scenario)?.label}</span>
          </h2>
          <div className="text-xs" style={{ color: "var(--text-dim)" }}>Growth: {revenueGrowth}% MoM</div>
        </div>

        {loading ? (
          <div className="skeleton" style={{ height: 320 }} />
        ) : points.length === 0 ? (
          <div className="flex flex-col items-center justify-center" style={{ height: 320 }}>
            <TrendingUp size={36} className="mb-3" style={{ color: "var(--text-dim)" }} />
            <p className="text-sm" style={{ color: "var(--text-dim)" }}>No forecast data available. Add transactions first.</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={points} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="fcIncomeGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--income)" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="var(--income)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="fcExpenseGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--expense)" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="var(--expense)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="fcNetGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="var(--accent)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="period" tick={{ fontSize: 11, fill: "var(--text-dim)" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "var(--text-dim)" }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11, color: "var(--text-muted)" }} />
              <Area type="monotone" dataKey="projected_income" name="Income" stroke="var(--income)" fill="url(#fcIncomeGrad)" strokeWidth={2} dot={false} />
              <Area type="monotone" dataKey="projected_expenses" name="Expenses" stroke="var(--expense)" fill="url(#fcExpenseGrad)" strokeWidth={2} dot={false} />
              <Area type="monotone" dataKey="projected_net" name="Net" stroke="var(--accent)" fill="url(#fcNetGrad)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Monthly Breakdown Table */}
      {!loading && points.length > 0 && (
        <div className="glass p-6 animate-fade-up delay-4">
          <h2 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>Monthly Breakdown</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>
                  <th className="text-left pb-3">Period</th>
                  <th className="text-right pb-3">Income</th>
                  <th className="text-right pb-3">Expenses</th>
                  <th className="text-right pb-3">Net</th>
                  <th className="text-right pb-3">Cumulative</th>
                  <th className="text-right pb-3">Range</th>
                </tr>
              </thead>
              <tbody>
                {points.map((p: ForecastPoint) => (
                  <tr key={p.period} className="border-t" style={{ borderColor: "var(--border)" }}>
                    <td className="py-2.5 font-medium" style={{ color: "var(--text)" }}>{p.period}</td>
                    <td className="py-2.5 text-right" style={{ color: "var(--income)" }}>{fmt(p.projected_income)}</td>
                    <td className="py-2.5 text-right" style={{ color: "var(--expense)" }}>{fmt(p.projected_expenses)}</td>
                    <td className="py-2.5 text-right font-semibold" style={{ color: p.projected_net >= 0 ? "var(--income)" : "var(--expense)" }}>{fmt(p.projected_net)}</td>
                    <td className="py-2.5 text-right" style={{ color: "var(--text-muted)" }}>{fmt(p.cumulative_net)}</td>
                    <td className="py-2.5 text-right text-xs" style={{ color: "var(--text-dim)" }}>{fmt(p.confidence_lower)} – {fmt(p.confidence_upper)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
