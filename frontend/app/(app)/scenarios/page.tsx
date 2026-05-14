"use client";

import { useEffect, useState, useCallback } from "react";
import { scenariosApi } from "@/lib/api";
import type {
  MonteCarloResult,
  Scenario,
  ScenarioAssumptions,
  ScenarioProjectionPoint,
} from "@/lib/types";
import {
  BarChart3,
  GitBranch,
  Plus,
  Sparkles,
  Trash2,
  TrendingDown,
  TrendingUp,
  X,
} from "lucide-react";
import { useCurrency } from "@/components/CurrencyContext";
import { LineChart, MetricCard } from "@/components/ReportCharts";

const RATE_KEYS: (keyof ScenarioAssumptions)[] = [
  "revenue_growth_pct",
  "expense_change_pct",
  "customer_churn_pct",
  "pricing_change_pct",
  "tax_rate_pct",
];

function getAssumptions(scenario: Scenario): ScenarioAssumptions | null {
  return scenario.assumptions_json ?? null;
}

function getProjection(scenario: Scenario): ScenarioProjectionPoint[] {
  return scenario.result_json?.monthly ?? [];
}

function inferRateMode(assumptions: ScenarioAssumptions | null): "percent" | "decimal" {
  if (!assumptions) return "percent";
  if (assumptions.rate_input_mode) return assumptions.rate_input_mode;

  const values = RATE_KEYS
    .map((key) => assumptions[key])
    .filter((value): value is number => typeof value === "number" && value !== 0)
    .map((value) => Math.abs(value));

  return values.length > 0 && values.every((value) => value <= 1) ? "decimal" : "percent";
}

function formatRate(value: number | undefined, assumptions: ScenarioAssumptions | null): string {
  if (typeof value !== "number") return "0.0%";
  const normalized = inferRateMode(assumptions) === "decimal" ? value * 100 : value;
  return `${normalized.toFixed(1)}%`;
}

function getRunwayMonth(points: ScenarioProjectionPoint[]): number {
  const monthIndex = points.findIndex((point) => point.cumulative_cash <= 0);
  return monthIndex === -1 ? points.length : monthIndex + 1;
}

export default function ScenariosPage() {
  const { formatAmount: fmt } = useCurrency();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);
  const [mcResult, setMcResult] = useState<MonteCarloResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"list" | "montecarlo">("list");
  const [showForm, setShowForm] = useState(false);
  const [mcLoading, setMcLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await scenariosApi.list();
      setScenarios(data);
      setSelectedScenarioId((current) =>
        current && data.some((scenario) => scenario.id === current) ? current : data[0]?.id ?? null,
      );
    } catch {
      setScenarios([]);
      setSelectedScenarioId(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (id: string) => {
    await scenariosApi.delete(id);
    load();
  };

  const runMonteCarlo = async () => {
    setMcLoading(true);
    try {
      setMcResult(await scenariosApi.monteCarlo({ scenarioId: selectedScenarioId }));
    } catch {
      setMcResult(null);
    } finally {
      setMcLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    await scenariosApi.create({
      name: fd.get("name") as string,
      description: (fd.get("description") as string) || undefined,
      assumptions: {
        revenue_growth_pct: Number(fd.get("rev_growth")) / 100,
        expense_change_pct: Number(fd.get("exp_growth")) / 100,
        one_time_income: Number(fd.get("oti")) || undefined,
        one_time_expense: Number(fd.get("ote")) || undefined,
        rate_input_mode: "decimal",
      },
    });
    form.reset();
    setShowForm(false);
    load();
  };

  const selectedScenario =
    scenarios.find((scenario) => scenario.id === selectedScenarioId) ?? scenarios[0] ?? null;
  const selectedAssumptions = selectedScenario ? getAssumptions(selectedScenario) : null;
  const selectedProjection = selectedScenario ? getProjection(selectedScenario) : [];
  useEffect(() => {
    setMcResult(null);
  }, [selectedScenarioId]);
  const projectionLabels = selectedProjection.map((point) => `M${point.month}`);
  const finalPoint = selectedProjection[selectedProjection.length - 1] ?? null;
  const avgMonthlyNet = selectedProjection.length
    ? selectedProjection.reduce((sum, point) => sum + point.net_cash_flow, 0) / selectedProjection.length
    : 0;
  const bestMonth = selectedProjection.length
    ? selectedProjection.reduce((best, point) =>
        point.net_cash_flow > best.net_cash_flow ? point : best,
      selectedProjection[0])
    : null;
  const worstMonth = selectedProjection.length
    ? selectedProjection.reduce((worst, point) =>
        point.net_cash_flow < worst.net_cash_flow ? point : worst,
      selectedProjection[0])
    : null;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between animate-fade-up">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>
            Scenario Planning
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            What-if analysis, compounding projections, and Monte Carlo simulations
          </p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary flex w-full items-center justify-center gap-2 sm:w-auto">
          {showForm ? <X size={16} /> : <Plus size={16} />}
          {showForm ? "Cancel" : "New Scenario"}
        </button>
      </div>

      {showForm && (
        <div className="glass p-6 animate-fade-up">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                Create Scenario
              </h3>
              <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                Growth inputs are entered as whole percentages in the form and stored with explicit rate metadata.
              </p>
            </div>
            <span
              className="text-[10px] uppercase tracking-[0.2em] px-2 py-1 rounded-full"
              style={{ color: "var(--accent)", background: "var(--accent-soft)" }}
            >
              12 month projection
            </span>
          </div>
          <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <input name="name" placeholder="Scenario Name" required />
            <input name="description" placeholder="Description (optional)" />
            <input name="rev_growth" type="number" step="0.1" placeholder="Revenue Growth %" required />
            <input name="exp_growth" type="number" step="0.1" placeholder="Expense Growth %" required />
            <input name="oti" type="number" step="1" placeholder="One-time Income (optional)" />
            <input name="ote" type="number" step="1" placeholder="One-time Expense (optional)" />
            <div className="sm:col-span-2 flex justify-stretch sm:justify-end">
              <button type="submit" className="btn-primary w-full sm:w-auto">
                Create
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="flex flex-wrap gap-2 animate-fade-up delay-1">
        {(["list", "montecarlo"] as const).map((currentTab) => (
          <button
            key={currentTab}
            onClick={() => {
              setTab(currentTab);
              if (currentTab === "montecarlo" && !mcResult) runMonteCarlo();
            }}
            className="px-4 py-2 rounded-lg text-sm font-medium"
            style={{
              background: tab === currentTab ? "var(--accent-soft)" : "var(--surface)",
              color: tab === currentTab ? "var(--accent)" : "var(--text-muted)",
              border: `1px solid ${tab === currentTab ? "var(--accent)" : "var(--border)"}`,
            }}
          >
            {currentTab === "list" ? "Scenarios" : "Monte Carlo"}
          </button>
        ))}
      </div>

      {tab === "list" &&
        (loading ? (
          <div className="skeleton" style={{ height: 240 }} />
        ) : scenarios.length === 0 ? (
          <div className="glass p-12 text-center">
            <GitBranch size={40} className="mx-auto mb-3" style={{ color: "var(--text-dim)" }} />
            <p className="text-sm" style={{ color: "var(--text-dim)" }}>
              No scenarios created yet.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {scenarios.map((scenario, index) => {
                const assumptions = getAssumptions(scenario);
                const points = getProjection(scenario);
                const lastPoint = points[points.length - 1] ?? null;
                const isSelected = scenario.id === selectedScenario?.id;

                return (
                  <div
                    key={scenario.id}
                    onClick={() => setSelectedScenarioId(scenario.id)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setSelectedScenarioId(scenario.id);
                      }
                    }}
                    role="button"
                    tabIndex={0}
                    className={`glass p-5 text-left animate-fade-up delay-${(index % 4) + 1} cursor-pointer`}
                    style={{
                      border: `1px solid ${isSelected ? "var(--accent)" : "var(--border)"}`,
                      background: isSelected ? "linear-gradient(180deg, var(--accent-soft), transparent)" : undefined,
                    }}
                  >
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                            {scenario.name}
                          </span>
                          {isSelected ? <Sparkles size={14} style={{ color: "var(--accent)" }} /> : null}
                        </div>
                        {scenario.description ? (
                          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                            {scenario.description}
                          </p>
                        ) : null}
                      </div>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          handleDelete(scenario.id);
                        }}
                        className="p-1.5 rounded-md hover:bg-[var(--danger-soft)]"
                      >
                        <Trash2 size={14} style={{ color: "var(--danger)" }} />
                      </button>
                    </div>

                    <div className="space-y-2 text-xs" style={{ color: "var(--text-muted)" }}>
                      <div className="flex justify-between">
                        <span>Revenue Growth</span>
                        <span
                          style={{
                            color:
                              (assumptions?.revenue_growth_pct ?? 0) >= 0 ? "var(--success)" : "var(--danger)",
                          }}
                        >
                          {formatRate(assumptions?.revenue_growth_pct, assumptions)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>Expense Growth</span>
                        <span
                          style={{
                            color:
                              (assumptions?.expense_change_pct ?? 0) <= 0 ? "var(--success)" : "var(--warning)",
                          }}
                        >
                          {formatRate(assumptions?.expense_change_pct, assumptions)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>Projection Period</span>
                        <span>{points.length || 12} months</span>
                      </div>
                      {lastPoint ? (
                        <>
                          <div className="flex justify-between">
                            <span>Ending Cash</span>
                            <span
                              style={{
                                color: lastPoint.cumulative_cash >= 0 ? "var(--success)" : "var(--danger)",
                              }}
                            >
                              {fmt(lastPoint.cumulative_cash)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>Month {lastPoint.month} Net</span>
                            <span
                              style={{
                                color: lastPoint.net_cash_flow >= 0 ? "var(--success)" : "var(--danger)",
                              }}
                            >
                              {fmt(lastPoint.net_cash_flow)}
                            </span>
                          </div>
                        </>
                      ) : null}
                      {assumptions?.one_time_income ? (
                        <div className="flex justify-between">
                          <span>One-time Income</span>
                          <span style={{ color: "var(--success)" }}>{fmt(assumptions.one_time_income)}</span>
                        </div>
                      ) : null}
                      {assumptions?.one_time_expense ? (
                        <div className="flex justify-between">
                          <span>One-time Expense</span>
                          <span style={{ color: "var(--danger)" }}>{fmt(assumptions.one_time_expense)}</span>
                        </div>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>

            {selectedScenario ? (
              <div className="glass p-6 animate-fade-up delay-2 space-y-6">
                <div className="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em]" style={{ color: "var(--text-dim)" }}>
                      Selected Scenario
                    </p>
                    <h2 className="text-xl font-semibold" style={{ color: "var(--text)" }}>
                      {selectedScenario.name}
                    </h2>
                    {selectedScenario.description ? (
                      <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
                        {selectedScenario.description}
                      </p>
                    ) : null}
                  </div>
                  <div className="text-xs" style={{ color: "var(--text-dim)" }}>
                    {selectedScenario.computed_at
                      ? `Recomputed ${new Date(selectedScenario.computed_at).toLocaleString()}`
                      : "Projection recalculated from current baseline"}
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                  <MetricCard
                    label="Ending Cash"
                    value={fmt(finalPoint?.cumulative_cash ?? 0)}
                    subtext={`${selectedProjection.length || 12} month horizon`}
                    trend={(finalPoint?.cumulative_cash ?? 0) >= 0 ? "up" : "down"}
                    icon={<Sparkles size={16} />}
                  />
                  <MetricCard
                    label="Average Monthly Net"
                    value={fmt(avgMonthlyNet)}
                    subtext={`Cash positive through month ${getRunwayMonth(selectedProjection)}`}
                    trend={avgMonthlyNet >= 0 ? "up" : "down"}
                    icon={<BarChart3 size={16} />}
                  />
                  <MetricCard
                    label="Best Month"
                    value={fmt(bestMonth?.net_cash_flow ?? 0)}
                    subtext={bestMonth ? `Month ${bestMonth.month}` : "No data"}
                    trend={(bestMonth?.net_cash_flow ?? 0) >= 0 ? "up" : "neutral"}
                    icon={<TrendingUp size={16} />}
                  />
                  <MetricCard
                    label="Worst Month"
                    value={fmt(worstMonth?.net_cash_flow ?? 0)}
                    subtext={worstMonth ? `Month ${worstMonth.month}` : "No data"}
                    trend={(worstMonth?.net_cash_flow ?? 0) < 0 ? "down" : "neutral"}
                    icon={<TrendingDown size={16} />}
                  />
                </div>

                {selectedProjection.length > 0 ? (
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] mb-3" style={{ color: "var(--text-dim)" }}>
                        Revenue vs Expenses
                      </p>
                      <LineChart
                        labels={projectionLabels}
                        datasets={[
                          {
                            label: "Income",
                            values: selectedProjection.map((point) => point.projected_income),
                            color: "#3BAE7C",
                          },
                          {
                            label: "Expenses",
                            values: selectedProjection.map((point) => point.projected_expenses),
                            color: "#D0674F",
                          },
                        ]}
                        height={260}
                      />
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] mb-3" style={{ color: "var(--text-dim)" }}>
                        Net Cash Flow vs Cumulative Cash
                      </p>
                      <LineChart
                        labels={projectionLabels}
                        datasets={[
                          {
                            label: "Net Cash Flow",
                            values: selectedProjection.map((point) => point.net_cash_flow),
                            color: "#C9A962",
                          },
                          {
                            label: "Cumulative Cash",
                            values: selectedProjection.map((point) => point.cumulative_cash),
                            color: "#6B8EC2",
                          },
                        ]}
                        height={260}
                      />
                    </div>
                  </div>
                ) : (
                  <div className="glass p-6 text-sm" style={{ color: "var(--text-muted)" }}>
                    No monthly projection data is available for this scenario yet.
                  </div>
                )}
              </div>
            ) : null}
          </div>
        ))}

      {tab === "montecarlo" &&
        (mcLoading ? (
          <div className="skeleton" style={{ height: 250 }} />
        ) : mcResult ? (
          <div className="space-y-4 animate-fade-up delay-2">
            <p className="text-xs uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>
              Runway (Consecutive Positive Months)
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[
                { label: "Pessimistic (P10)", value: `${mcResult.p10_runway} mo`, color: "var(--danger)" },
                { label: "Median (P50)", value: `${mcResult.p50_runway} mo`, color: "var(--accent)" },
                { label: "Optimistic (P90)", value: `${mcResult.p90_runway} mo`, color: "var(--success)" },
              ].map((kpi) => (
                <div key={kpi.label} className="glass p-5 text-center">
                  <p className="text-xs uppercase tracking-wider mb-2" style={{ color: "var(--text-dim)" }}>
                    {kpi.label}
                  </p>
                  <p className="text-3xl font-bold" style={{ color: kpi.color }}>
                    {kpi.value}
                  </p>
                </div>
              ))}
            </div>

            <p className="text-xs uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>
              Projected Cash Position (End of Period)
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[
                { label: "Worst Case (P10)", value: fmt(mcResult.p10_cash ?? 0), color: "var(--danger)" },
                { label: "Median (P50)", value: fmt(mcResult.p50_cash ?? 0), color: "var(--accent)" },
                { label: "Best Case (P90)", value: fmt(mcResult.p90_cash ?? 0), color: "var(--success)" },
              ].map((kpi) => (
                <div key={kpi.label} className="glass p-5 text-center">
                  <p className="text-xs uppercase tracking-wider mb-2" style={{ color: "var(--text-dim)" }}>
                    {kpi.label}
                  </p>
                  <p className="text-2xl font-bold" style={{ color: kpi.color }}>
                    {kpi.value}
                  </p>
                </div>
              ))}
            </div>

            {(mcResult.baseline_monthly_income != null || mcResult.baseline_monthly_expense != null) && (
              <div className="glass p-4" style={{ borderLeft: "3px solid var(--accent)" }}>
                <p className="text-xs uppercase tracking-wider mb-3" style={{ color: "var(--text-dim)" }}>
                  Simulation Inputs {selectedScenario ? `for ${selectedScenario.name}` : "(historical baseline)"}
                </p>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  {[
                    { label: "Median Income / mo", value: fmt(mcResult.baseline_monthly_income ?? 0), color: "var(--success)" },
                    { label: "Median Expense / mo", value: fmt(mcResult.baseline_monthly_expense ?? 0), color: "var(--danger)" },
                    { label: "Starting Cash", value: fmt(mcResult.starting_cash ?? 0), color: "var(--accent)" },
                    {
                      label: "Median Monthly Net",
                      value: fmt((mcResult.baseline_monthly_income ?? 0) - (mcResult.baseline_monthly_expense ?? 0)),
                      color:
                        (mcResult.baseline_monthly_income ?? 0) >= (mcResult.baseline_monthly_expense ?? 0)
                          ? "var(--success)"
                          : "var(--danger)",
                    },
                    {
                      label: "Income Volatility",
                      value: `${((mcResult.revenue_std_used ?? 0) * 100).toFixed(1)}%`,
                      color: "var(--success)",
                    },
                    {
                      label: "Expense Volatility",
                      value: `${((mcResult.expense_std_used ?? 0) * 100).toFixed(1)}%`,
                      color: "var(--warning)",
                    },
                  ].map((kpi) => (
                    <div key={kpi.label} className="text-center">
                      <p className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "var(--text-dim)" }}>
                        {kpi.label}
                      </p>
                      <p className="text-sm font-semibold" style={{ color: kpi.color }}>
                        {kpi.value}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {(() => {
              const dist = mcResult.distribution || [];
              const allRunwayZero = dist.length > 0 && dist.every((d) => d.runway === 0);
              const chartLabel = allRunwayZero
                ? `Cash Position Distribution (${(mcResult.num_simulations || mcResult.simulations || 0).toLocaleString()} sims, ${mcResult.months_ahead || 12}mo)`
                : `Runway Distribution (${(mcResult.num_simulations || mcResult.simulations || 0).toLocaleString()} sims, ${mcResult.months_ahead || 12}mo)`;

              return (
                <div className="glass p-5">
                  <p className="text-xs uppercase tracking-wider mb-3" style={{ color: "var(--text-dim)" }}>
                    {chartLabel}
                  </p>
                  <div className="flex items-end gap-1" style={{ height: 160 }}>
                    {dist.map((point, index) => {
                      if (allRunwayZero) {
                        const absCash = dist.map((item) => Math.abs(item.cash));
                        const maxAbs = Math.max(...absCash, 1);
                        const minAbs = Math.min(...absCash);
                        const range = maxAbs - minAbs || 1;
                        const normalized = 1 - (Math.abs(point.cash) - minAbs) / range;
                        const barHeight = 20 + normalized * 80;
                        const hue = normalized * 60;

                        return (
                          <div
                            key={index}
                            className="flex-1 flex flex-col items-center gap-1"
                            title={`P${point.percentile}: ${fmt(point.cash)}`}
                          >
                            <span className="text-[8px] font-medium" style={{ color: `hsl(${hue}, 70%, 55%)` }}>
                              {fmt(point.cash)}
                            </span>
                            <div
                              className="w-full rounded-t-sm transition-all"
                              style={{
                                height: `${barHeight}%`,
                                background: `hsl(${hue}, 60%, 40%)`,
                                minHeight: 4,
                                opacity: 0.85,
                              }}
                            />
                            <span className="text-[9px]" style={{ color: "var(--text-dim)" }}>
                              P{point.percentile}
                            </span>
                          </div>
                        );
                      }

                      const maxRunway = Math.max(...dist.map((item) => item.runway), 1);
                      const percent = (point.runway / maxRunway) * 100;
                      return (
                        <div
                          key={index}
                          className="flex-1 flex flex-col items-center gap-1"
                          title={`P${point.percentile}: ${point.runway} months, ${fmt(point.cash)}`}
                        >
                          <div
                            className="w-full rounded-t-sm transition-all"
                            style={{
                              height: `${Math.max(percent, 3)}%`,
                              background: `hsl(${(120 * percent) / 100}, 60%, 45%)`,
                              minHeight: 2,
                              opacity: 0.8 + percent / 500,
                            }}
                          />
                          <span className="text-[9px]" style={{ color: "var(--text-dim)" }}>
                            P{point.percentile}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })()}

            <button onClick={runMonteCarlo} className="btn-primary flex items-center gap-2 mx-auto">
              <BarChart3 size={16} />
              Re-run Simulation
            </button>
          </div>
        ) : (
          <div className="glass p-12 text-center">
            <BarChart3 size={40} className="mx-auto mb-3" style={{ color: "var(--text-dim)" }} />
            <button onClick={runMonteCarlo} className="btn-primary mt-2">
              Run Monte Carlo
            </button>
          </div>
        ))}
    </div>
  );
}
