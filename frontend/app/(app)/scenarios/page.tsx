"use client";
import { useEffect, useState, useCallback } from "react";
import { scenariosApi } from "@/lib/api";
import type { Scenario, MonteCarloResult } from "@/lib/types";
import { GitBranch, Plus, X, Trash2, BarChart3 } from "lucide-react";
import { useCurrency } from "@/components/CurrencyContext";

export default function ScenariosPage() {
  const { formatAmount: fmt } = useCurrency();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [mcResult, setMcResult] = useState<MonteCarloResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"list"|"montecarlo">("list");
  const [showForm, setShowForm] = useState(false);
  const [mcLoading, setMcLoading] = useState(false);

  const load = useCallback(async () => {
    try { setScenarios(await scenariosApi.list()); } catch {} finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id: string) => { await scenariosApi.delete(id); load(); };

  const runMonteCarlo = async () => {
    setMcLoading(true);
    try { setMcResult(await scenariosApi.monteCarlo()); } catch {} finally { setMcLoading(false); }
  };

  const handleCreate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    await scenariosApi.create({
      name: fd.get("name") as string,
      description: fd.get("description") as string || undefined,
      assumptions: {
        revenue_growth_pct: Number(fd.get("rev_growth")) / 100,
        expense_change_pct: Number(fd.get("exp_growth")) / 100,
        one_time_income: Number(fd.get("oti")) || undefined,
        one_time_expense: Number(fd.get("ote")) || undefined,
      },
      months_ahead: Number(fd.get("months") || 12),
    });
    setShowForm(false); load();
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between animate-fade-up">
        <div>
          <h1 className="text-2xl font-bold" style={{ color:"var(--text)" }}>Scenario Planning</h1>
          <p className="text-sm mt-1" style={{ color:"var(--text-muted)" }}>What-if analysis & Monte Carlo simulations</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary flex items-center gap-2">
          {showForm ? <X size={16}/> : <Plus size={16}/>} {showForm ? "Cancel" : "New Scenario"}
        </button>
      </div>

      {showForm && (
        <div className="glass p-6 animate-fade-up">
          <h3 className="text-sm font-semibold mb-4" style={{ color:"var(--text)" }}>Create Scenario</h3>
          <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <input name="name" placeholder="Scenario Name" required />
            <input name="description" placeholder="Description (optional)" />
            <input name="months" type="number" min="1" max="60" defaultValue="12" placeholder="Months Ahead" />
            <input name="rev_growth" type="number" step="0.1" placeholder="Revenue Growth %" required />
            <input name="exp_growth" type="number" step="0.1" placeholder="Expense Growth %" required />
            <input name="oti" type="number" step="1" placeholder="One-time Income (optional)" />
            <input name="ote" type="number" step="1" placeholder="One-time Expense (optional)" />
            <div/>
            <button type="submit" className="btn-primary">Create</button>
          </form>
        </div>
      )}

      <div className="flex gap-2 animate-fade-up delay-1">
        {(["list","montecarlo"] as const).map(t => (
          <button key={t} onClick={() => { setTab(t); if (t === "montecarlo" && !mcResult) runMonteCarlo(); }} className="px-4 py-2 rounded-lg text-sm font-medium" style={{
            background: tab===t ? "var(--accent-soft)" : "var(--surface)",
            color: tab===t ? "var(--accent)" : "var(--text-muted)",
            border: `1px solid ${tab===t ? "var(--accent)" : "var(--border)"}`,
          }}>{t === "list" ? "Scenarios" : "Monte Carlo"}</button>
        ))}
      </div>

      {tab === "list" && (
        loading ? <div className="skeleton" style={{ height: 200 }}/> : scenarios.length === 0 ? (
          <div className="glass p-12 text-center">
            <GitBranch size={40} className="mx-auto mb-3" style={{ color:"var(--text-dim)" }}/>
            <p className="text-sm" style={{ color:"var(--text-dim)" }}>No scenarios created yet.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {scenarios.map((s,i) => (
              <div key={s.id} className={`glass p-5 animate-fade-up delay-${(i%4)+1}`}>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-semibold" style={{ color:"var(--text)" }}>{s.name}</span>
                  <button onClick={() => handleDelete(s.id)} className="p-1.5 rounded-md hover:bg-[var(--danger-soft)]"><Trash2 size={14} style={{ color:"var(--danger)" }}/></button>
                </div>
                {s.description && <p className="text-xs mb-3" style={{ color:"var(--text-muted)" }}>{s.description}</p>}
                <div className="space-y-1 text-xs" style={{ color:"var(--text-muted)" }}>
                  {s.assumptions ? (<>
                  <div className="flex justify-between"><span>Revenue Growth</span><span style={{ color: s.assumptions.revenue_growth_pct >= 0 ? "var(--success)" : "var(--danger)" }}>{(s.assumptions.revenue_growth_pct * 100).toFixed(1)}%</span></div>
                  <div className="flex justify-between"><span>Expense Growth</span><span style={{ color: s.assumptions.expense_change_pct <= 0 ? "var(--success)" : "var(--warning)" }}>{(s.assumptions.expense_change_pct * 100).toFixed(1)}%</span></div>
                  <div className="flex justify-between"><span>Projection Period</span><span>{s.months_ahead} months</span></div>
                  {s.assumptions.one_time_income ? <div className="flex justify-between"><span>One-time Income</span><span style={{ color:"var(--success)" }}>{fmt(s.assumptions.one_time_income)}</span></div> : null}
                  {s.assumptions.one_time_expense ? <div className="flex justify-between"><span>One-time Expense</span><span style={{ color:"var(--danger)" }}>{fmt(s.assumptions.one_time_expense)}</span></div> : null}
                  </>) : (
                  <div className="flex justify-between"><span>Projection Period</span><span>{s.months_ahead} months</span></div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {tab === "montecarlo" && (
        mcLoading ? <div className="skeleton" style={{ height: 250 }}/> : mcResult ? (
          <div className="space-y-4 animate-fade-up delay-2">
            {/* Runway KPIs */}
            <p className="text-xs uppercase tracking-wider" style={{ color:"var(--text-dim)" }}>Runway (Consecutive Positive Months)</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[
                { label: "Pessimistic (P10)", value: `${mcResult.p10_runway} mo`, color: "var(--danger)" },
                { label: "Median (P50)", value: `${mcResult.p50_runway} mo`, color: "var(--accent)" },
                { label: "Optimistic (P90)", value: `${mcResult.p90_runway} mo`, color: "var(--success)" },
              ].map(kpi => (
                <div key={kpi.label} className="glass p-5 text-center">
                  <p className="text-xs uppercase tracking-wider mb-2" style={{ color:"var(--text-dim)" }}>{kpi.label}</p>
                  <p className="text-3xl font-bold" style={{ color: kpi.color }}>{kpi.value}</p>
                </div>
              ))}
            </div>
            {/* Cash KPIs */}
            <p className="text-xs uppercase tracking-wider" style={{ color:"var(--text-dim)" }}>Projected Cash Position (End of Period)</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[
                { label: "Worst Case (P10)", value: fmt(mcResult.p10_cash ?? 0), color: "var(--danger)" },
                { label: "Median (P50)", value: fmt(mcResult.p50_cash ?? 0), color: "var(--accent)" },
                { label: "Best Case (P90)", value: fmt(mcResult.p90_cash ?? 0), color: "var(--success)" },
              ].map(kpi => (
                <div key={kpi.label} className="glass p-5 text-center">
                  <p className="text-xs uppercase tracking-wider mb-2" style={{ color:"var(--text-dim)" }}>{kpi.label}</p>
                  <p className="text-2xl font-bold" style={{ color: kpi.color }}>{kpi.value}</p>
                </div>
              ))}
            </div>
            {/* Baseline Inputs Transparency */}
            {(mcResult.baseline_monthly_income != null || mcResult.baseline_monthly_expense != null) && (
              <div className="glass p-4" style={{ borderLeft: "3px solid var(--accent)" }}>
                <p className="text-xs uppercase tracking-wider mb-3" style={{ color:"var(--text-dim)" }}>Simulation Inputs (auto-detected from transactions)</p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {[
                    { label: "Median Income / mo", value: fmt(mcResult.baseline_monthly_income ?? 0), color: "var(--success)" },
                    { label: "Median Expense / mo", value: fmt(mcResult.baseline_monthly_expense ?? 0), color: "var(--danger)" },
                    { label: "Starting Cash", value: fmt(mcResult.starting_cash ?? 0), color: "var(--accent)" },
                    { label: "Monthly Burn", value: fmt((mcResult.baseline_monthly_income ?? 0) - (mcResult.baseline_monthly_expense ?? 0)), color: (mcResult.baseline_monthly_income ?? 0) >= (mcResult.baseline_monthly_expense ?? 0) ? "var(--success)" : "var(--danger)" },
                  ].map(kpi => (
                    <div key={kpi.label} className="text-center">
                      <p className="text-[10px] uppercase tracking-wider mb-1" style={{ color:"var(--text-dim)" }}>{kpi.label}</p>
                      <p className="text-sm font-semibold" style={{ color: kpi.color }}>{kpi.value}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {/* Distribution Chart — adaptive: shows cash when runway is uniformly zero */}
            {(() => {
              const dist = mcResult.distribution || [];
              const allRunwayZero = dist.length > 0 && dist.every(d => d.runway === 0);
              const chartLabel = allRunwayZero
                ? `Cash Position Distribution (${(mcResult.num_simulations || mcResult.simulations || 0).toLocaleString()} sims, ${mcResult.months_ahead || 12}mo)`
                : `Runway Distribution (${(mcResult.num_simulations || mcResult.simulations || 0).toLocaleString()} sims, ${mcResult.months_ahead || 12}mo)`;

              return (
                <div className="glass p-5">
                  <p className="text-xs uppercase tracking-wider mb-3" style={{ color:"var(--text-dim)" }}>{chartLabel}</p>
                  <div className="flex items-end gap-1" style={{ height: 160 }}>
                    {dist.map((d, i) => {
                      if (allRunwayZero) {
                        // Cash distribution: normalize absolute values so bars are relative
                        const absCash = dist.map(x => Math.abs(x.cash));
                        const maxAbs = Math.max(...absCash, 1);
                        const minAbs = Math.min(...absCash);
                        const range = maxAbs - minAbs || 1;
                        // Invert: smallest absolute value = tallest bar (least negative = best)
                        const normalized = 1 - (Math.abs(d.cash) - minAbs) / range;
                        const barH = 20 + normalized * 80; // 20% min height
                        // Color: red for worst, amber for mid, green-ish for best
                        const hue = normalized * 60; // 0=red, 60=yellow
                        return (
                          <div key={i} className="flex-1 flex flex-col items-center gap-1" title={`P${d.percentile}: ${fmt(d.cash)}`}>
                            <span className="text-[8px] font-medium" style={{ color:`hsl(${hue}, 70%, 55%)` }}>{fmt(d.cash)}</span>
                            <div className="w-full rounded-t-sm transition-all" style={{ height: `${barH}%`, background: `hsl(${hue}, 60%, 40%)`, minHeight: 4, opacity: 0.85 }}/>
                            <span className="text-[9px]" style={{ color:"var(--text-dim)" }}>P{d.percentile}</span>
                          </div>
                        );
                      } else {
                        // Runway distribution: original behavior
                        const maxRunway = Math.max(...dist.map(x => x.runway), 1);
                        const pct = (d.runway / maxRunway) * 100;
                        return (
                          <div key={i} className="flex-1 flex flex-col items-center gap-1" title={`P${d.percentile}: ${d.runway} months, ${fmt(d.cash)}`}>
                            <div className="w-full rounded-t-sm transition-all" style={{ height: `${Math.max(pct, 3)}%`, background: `hsl(${120 * pct / 100}, 60%, 45%)`, minHeight: 2, opacity: 0.8 + (pct / 500) }}/>
                            <span className="text-[9px]" style={{ color:"var(--text-dim)" }}>P{d.percentile}</span>
                          </div>
                        );
                      }
                    })}
                  </div>
                </div>
              );
            })()}
            <button onClick={runMonteCarlo} className="btn-primary flex items-center gap-2 mx-auto"><BarChart3 size={16}/> Re-run Simulation</button>
          </div>
        ) : (
          <div className="glass p-12 text-center">
            <BarChart3 size={40} className="mx-auto mb-3" style={{ color:"var(--text-dim)" }}/>
            <button onClick={runMonteCarlo} className="btn-primary mt-2">Run Monte Carlo</button>
          </div>
        )
      )}
    </div>
  );
}
