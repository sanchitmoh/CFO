"use client";

import { useState } from "react";
import {
  Calculator,
  DollarSign,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Repeat,
  Calendar,
  ArrowRight,
  Loader2,
} from "lucide-react";
import { calculatorApi } from "@/lib/api";
import type { AffordabilityResponse } from "@/lib/types";
import { useCurrency } from "@/components/CurrencyContext";

type Frequency = "one-time" | "monthly" | "annual";

type Verdict = "safe" | "caution" | "risky";

interface AffordResult {
  canAfford: boolean;
  runwayBefore: number;
  runwayAfter: number;
  currentBalance3Months: number;
  projectedBalance3Months: number;
  monthlyImpact: number;
  breakEven: number | null;
  suggestion: string;
  verdict: Verdict;
}

/** Map frontend frequency values to backend enum format. */
const freqToBackend = (f: Frequency): "one_time" | "monthly" | "annual" =>
  f === "one-time" ? "one_time" : f;

/** Derive a UI verdict from the backend response. */
function deriveVerdict(res: AffordabilityResponse): Verdict {
  if (!res.can_afford) return "risky";
  return res.projected_runway_months >= 6 ? "safe" : "caution";
}

/** Map backend AffordabilityResponse → UI AffordResult. */
function toAffordResult(
  res: AffordabilityResponse,
  amount: number,
  frequency: Frequency
): AffordResult {
  const monthlyImpact =
    frequency === "one-time" ? 0 : frequency === "monthly" ? amount : amount / 12;

  return {
    canAfford: res.can_afford,
    runwayBefore: res.current_runway_months,
    runwayAfter: res.projected_runway_months,
    currentBalance3Months: res.current_balance_3m,
    projectedBalance3Months: res.projected_balance_3m,
    monthlyImpact,
    breakEven: res.break_even_revenue ?? null,
    suggestion: res.ai_suggestion,
    verdict: deriveVerdict(res),
  };
}

export default function CalculatorPage() {
  const { currencyCode, formatAmount: fmt } = useCurrency();
  const [form, setForm] = useState({
    name: "",
    amount: "",
    frequency: "monthly" as Frequency,
    isHire: false,
  });
  const [result, setResult] = useState<AffordResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const amt = parseFloat(form.amount);
    if (!amt || amt <= 0) return;

    setLoading(true);
    setError(null);
    try {
      const res = await calculatorApi.checkAffordability({
        expense_name: form.name,
        amount: amt,
        frequency: freqToBackend(form.frequency),
        is_hire: form.isHire,
      });
      setResult(toAffordResult(res, amt, form.frequency));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to analyse affordability";
      setError(message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const verdictColor = {
    safe: "var(--accent)",
    caution: "var(--warning)",
    risky: "var(--danger)",
  };
  const verdictBg = {
    safe: "var(--accent-soft)",
    caution: "var(--warning-soft)",
    risky: "var(--danger-soft)",
  };
  const VerdictIcon = {
    safe: CheckCircle,
    caution: AlertTriangle,
    risky: XCircle,
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="animate-fade-up">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>
          What Can I Afford?
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          Model the impact of any business expense before you commit
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Card */}
        <div className="glass p-6 animate-fade-up delay-1">
          <div className="flex items-center gap-3 mb-5">
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: "var(--accent-soft)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Calculator size={18} style={{ color: "var(--accent)" }} />
            </div>
            <h2 className="font-semibold text-sm" style={{ color: "var(--text)" }}>
              Expense Details
            </h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                className="block text-xs font-medium mb-2 uppercase tracking-wider"
                style={{ color: "var(--text-muted)" }}
              >
                Expense Name
              </label>
              <input
                type="text"
                placeholder="e.g. Hire salesperson, New laptop, SaaS tool"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="w-full"
                required
              />
            </div>

            <div>
              <label
                className="block text-xs font-medium mb-2 uppercase tracking-wider"
                style={{ color: "var(--text-muted)" }}
              >
                Amount ({currencyCode})
              </label>
              <input
                type="number"
                placeholder="e.g. 5000"
                value={form.amount}
                onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                className="w-full"
                min={0}
                required
              />
            </div>

            <div>
              <label
                className="block text-xs font-medium mb-2 uppercase tracking-wider"
                style={{ color: "var(--text-muted)" }}
              >
                Frequency
              </label>
              <div className="grid grid-cols-3 gap-2">
                {([
                  { value: "one-time", label: "One-time", icon: DollarSign },
                  { value: "monthly", label: "Monthly", icon: Repeat },
                  { value: "annual", label: "Annual", icon: Calendar },
                ] as const).map(({ value, label, icon: Icon }) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setForm((f) => ({ ...f, frequency: value }))}
                    className="flex flex-col items-center gap-1.5 p-3 rounded-lg text-xs font-medium transition-all"
                    style={{
                      background:
                        form.frequency === value
                          ? "var(--accent-soft)"
                          : "var(--bg)",
                      color:
                        form.frequency === value
                          ? "var(--accent)"
                          : "var(--text-muted)",
                      border: `1px solid ${form.frequency === value ? "var(--accent)44" : "var(--border)"}`,
                    }}
                  >
                    <Icon size={16} />
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Hiring toggle */}
            <div
              className="flex items-center justify-between p-3 rounded-lg"
              style={{ background: "var(--bg)", border: "1px solid var(--border)" }}
            >
              <div>
                <p className="text-sm font-medium" style={{ color: "var(--text)" }}>
                  This is a hiring decision
                </p>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                  Uses hiring-specific wording and defaults the cost to a monthly view
                </p>
              </div>
              <button
                type="button"
                onClick={() =>
                  setForm((f) => ({
                    ...f,
                    isHire: !f.isHire,
                    frequency: !f.isHire ? "monthly" : f.frequency,
                  }))
                }
                className="relative rounded-full transition-all"
                style={{
                  width: 40,
                  height: 22,
                  background: form.isHire ? "var(--accent)" : "var(--border)",
                }}
              >
                <span
                  className="absolute top-1 transition-all rounded-full"
                  style={{
                    width: 14,
                    height: 14,
                    background: "white",
                    left: form.isHire ? 22 : 4,
                  }}
                />
              </button>
            </div>

            {/* Data source info */}
            <div
              className="p-3 rounded-lg text-xs"
              style={{ background: "var(--bg)", border: "1px solid var(--border)" }}
            >
              <p className="font-medium mb-1" style={{ color: "var(--text)" }}>
                📊 Powered by Your Financial Data
              </p>
              <p style={{ color: "var(--text-dim)" }}>
                Analysis uses your current cash position plus trailing 3-month income and expenses to model impact.
              </p>
            </div>

            {error && (
              <div
                className="p-3 rounded-lg text-xs"
                style={{ background: "var(--danger-soft)", border: "1px solid var(--danger)33", color: "var(--danger)" }}
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              className="btn-primary w-full flex items-center justify-center gap-2"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 size={15} className="animate-spin" />
                  Analysing…
                </>
              ) : (
                <>
                  <Calculator size={15} />
                  Calculate Affordability
                </>
              )}
            </button>
          </form>
        </div>

        {/* Result Card */}
        <div className="animate-fade-up delay-2">
          {!result ? (
            <div
              className="glass p-6 h-full flex flex-col items-center justify-center text-center"
              style={{ minHeight: 400 }}
            >
              <DollarSign size={40} className="mb-3" style={{ color: "var(--text-dim)" }} />
              <p className="text-sm font-medium" style={{ color: "var(--text-muted)" }}>
                Fill in the form to see the impact analysis
              </p>
              <p className="text-xs mt-1" style={{ color: "var(--text-dim)" }}>
                We'll model runway, balance, and break-even in real time
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Verdict */}
              <div
                className="glass p-5"
                style={{ borderColor: `${verdictColor[result.verdict]}33` }}
              >
                <div className="flex items-center gap-3 mb-3">
                  {(() => {
                    const Icon = VerdictIcon[result.verdict];
                    return (
                      <div
                        style={{
                          width: 40,
                          height: 40,
                          borderRadius: 10,
                          background: verdictBg[result.verdict],
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        <Icon size={20} style={{ color: verdictColor[result.verdict] }} />
                      </div>
                    );
                  })()}
                  <div>
                    <p className="font-bold text-sm" style={{ color: verdictColor[result.verdict] }}>
                      {result.verdict === "safe"
                        ? "✓ You Can Afford This"
                        : result.verdict === "caution"
                        ? "⚠ Proceed with Caution"
                        : "✗ Too Risky Right Now"}
                    </p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {form.name || "This expense"}
                      {form.frequency !== "one-time" ? ` · ${form.frequency}` : ""}
                    </p>
                  </div>
                </div>
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                  {result.suggestion}
                </p>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
                {[
                  {
                    label: "Runway Before",
                    value:
                      result.runwayBefore >= 99
                        ? "∞"
                        : `${result.runwayBefore.toFixed(1)} mo`,
                    color: "var(--accent)",
                    bg: "var(--accent-soft)",
                  },
                  {
                    label: "Runway After",
                    value:
                      result.runwayAfter >= 99
                        ? "∞"
                        : `${result.runwayAfter.toFixed(1)} mo`,
                    color: verdictColor[result.verdict],
                    bg: verdictBg[result.verdict],
                  },
                  {
                    label: "Current 3-Month Cash",
                    value: fmt(result.currentBalance3Months),
                    color: result.currentBalance3Months >= 0 ? "var(--accent)" : "var(--danger)",
                    bg: result.currentBalance3Months >= 0 ? "var(--accent-soft)" : "var(--danger-soft)",
                  },
                  {
                    label: "Projected 3-Month Cash",
                    value: fmt(result.projectedBalance3Months),
                    color: result.projectedBalance3Months >= 0 ? "var(--accent)" : "var(--danger)",
                    bg: result.projectedBalance3Months >= 0 ? "var(--accent-soft)" : "var(--danger-soft)",
                  },
                  {
                    label: "Monthly Cost Impact",
                    value: result.monthlyImpact > 0 ? fmt(result.monthlyImpact) + "/mo" : "One-time",
                    color: "var(--warning)",
                    bg: "var(--warning-soft)",
                  },
                ].map(({ label, value, color, bg }) => (
                  <div
                    key={label}
                    className="glass p-4"
                    style={{ borderColor: `${color}22` }}
                  >
                    <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "var(--text-muted)" }}>
                      {label}
                    </p>
                    <p className="text-xl font-bold" style={{ color }}>
                      {value}
                    </p>
                  </div>
                ))}
              </div>

              {/* Break-even */}
              {result.breakEven !== null && (
                <div
                  className="glass p-4 flex items-center gap-3"
                  style={{ borderColor: "var(--info)22" }}
                >
                  <ArrowRight size={16} style={{ color: "var(--info)", flexShrink: 0 }} />
                  <div>
                    <p className="text-sm font-medium" style={{ color: "var(--text)" }}>
                      Break-even Point
                    </p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                      You would need to generate an additional{" "}
                      <strong style={{ color: "var(--info)" }}>{fmt(result.breakEven)}</strong>{" "}
                      in revenue over 3 months to stay cash-neutral after this decision.
                    </p>
                  </div>
                </div>
              )}

              {/* Runway comparison bar */}
              <div className="glass p-4">
                <p className="text-xs uppercase tracking-wider mb-3" style={{ color: "var(--text-muted)" }}>
                  Runway Comparison
                </p>
                <div className="space-y-2">
                  {[
                    { label: "Before", value: Math.min(result.runwayBefore, 12), color: "var(--accent)" },
                    { label: "After", value: Math.min(result.runwayAfter, 12), color: verdictColor[result.verdict] },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="flex items-center gap-3 text-xs">
                      <span style={{ width: 40, color: "var(--text-muted)" }}>{label}</span>
                      <div style={{ flex: 1, height: 8, background: "var(--surface-hover)", borderRadius: 4 }}>
                        <div
                          style={{
                            width: `${(value / 12) * 100}%`,
                            height: "100%",
                            background: color,
                            borderRadius: 4,
                            transition: "width 0.5s ease",
                          }}
                        />
                      </div>
                      <span style={{ width: 50, color, fontWeight: 600 }}>
                        {value >= 12 ? "12+" : value.toFixed(1)} mo
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <p className="text-xs text-center animate-fade-up delay-5" style={{ color: "var(--text-dim)" }}>
        Analysis based on your current cash proxy and trailing 3-month operating performance.
      </p>
    </div>
  );
}
