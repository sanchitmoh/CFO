"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, TrendingUp, TrendingDown, Clock, Wallet } from "lucide-react";

interface HealthScoreGaugeProps {
  score?: number;
  runwayMonths?: number;
  burnTrend?: "increasing" | "decreasing" | "stable";
  budgetVariance?: number; // 0–100 how well actuals match budgets
  revenueGrowth?: number;  // MoM %
  compact?: boolean;
}

const DRIVERS = (props: HealthScoreGaugeProps) => [
  {
    label: "Runway",
    weight: "40%",
    score: Math.min(100, ((props.runwayMonths ?? 8.3) / 6) * 100),
    icon: Clock,
    color: "var(--accent)",
    note: `${(props.runwayMonths ?? 8.3).toFixed(1)} months — ${(props.runwayMonths ?? 8.3) >= 6 ? "Healthy" : "Needs attention"}`,
  },
  {
    label: "Burn Rate Trend",
    weight: "20%",
    score: props.burnTrend === "decreasing" ? 100 : props.burnTrend === "stable" ? 70 : 40,
    icon: TrendingDown,
    color: "var(--warning)",
    note: props.burnTrend === "increasing" ? "⚠ Rising — watch closely" : "Stable",
  },
  {
    label: "Budget Variance",
    weight: "20%",
    score: props.budgetVariance ?? 60,
    icon: Wallet,
    color: "var(--info)",
    note: `${(props.budgetVariance ?? 60).toFixed(0)}% match vs. plan`,
  },
  {
    label: "Revenue Growth",
    weight: "20%",
    score: Math.min(100, ((props.revenueGrowth ?? 12) / 10) * 100),
    icon: TrendingUp,
    color: "var(--income)",
    note: `${(props.revenueGrowth ?? 12).toFixed(1)}% MoM`,
  },
];

function scoreColor(s: number) {
  if (s >= 71) return "var(--accent)";
  if (s >= 41) return "var(--warning)";
  return "var(--danger)";
}
function scoreLabel(s: number) {
  if (s >= 71) return "Good";
  if (s >= 41) return "Caution";
  return "Critical";
}

export default function HealthScoreGauge({
  score = 72,
  compact = false,
  ...props
}: HealthScoreGaugeProps) {
  const [open, setOpen] = useState(false);
  const color = scoreColor(score);
  const label = scoreLabel(score);
  const radius = compact ? 40 : 52;
  const size = compact ? 96 : 120;
  const circumference = 2 * Math.PI * radius;
  // Draw 270° arc (start top-left, end top-right), offset by 135°
  const arcLen = (score / 100) * (circumference * 0.75);
  const drivers = DRIVERS(props);

  return (
    <div
      className="glass p-5 animate-fade-up"
      style={{ borderColor: `${color}22` }}
    >
      <div className="flex items-center gap-5">
        {/* Gauge SVG */}
        <div className="relative shrink-0" style={{ width: size, height: size }}>
          <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size}>
            {/* Track */}
            <circle
              cx={size / 2} cy={size / 2} r={radius}
              fill="none"
              stroke="var(--surface-hover)"
              strokeWidth={compact ? 8 : 10}
              strokeDasharray={`${circumference * 0.75} ${circumference * 0.25}`}
              strokeLinecap="round"
              transform={`rotate(135 ${size / 2} ${size / 2})`}
            />
            {/* Score arc */}
            <circle
              cx={size / 2} cy={size / 2} r={radius}
              fill="none"
              stroke={color}
              strokeWidth={compact ? 8 : 10}
              strokeDasharray={`${arcLen} ${circumference - arcLen}`}
              strokeLinecap="round"
              transform={`rotate(135 ${size / 2} ${size / 2})`}
              style={{ transition: "stroke-dasharray 0.8s ease" }}
            />
          </svg>
          {/* Center text */}
          <div
            className="absolute inset-0 flex flex-col items-center justify-center"
            style={{ paddingTop: compact ? 8 : 12 }}
          >
            <span
              className="font-bold leading-none"
              style={{ color, fontSize: compact ? 22 : 28 }}
            >
              {score}
            </span>
            {!compact && (
              <span className="text-xs mt-0.5" style={{ color: "var(--text-dim)" }}>
                /100
              </span>
            )}
          </div>
        </div>

        {/* Label + button */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase tracking-wider font-semibold" style={{ color: "var(--text-muted)" }}>
              Financial Health
            </span>
            <span
              className="badge"
              style={{ background: `${color}18`, color }}
            >
              {label}
            </span>
          </div>
          <p className="text-xl font-bold" style={{ color }}>
            {score}/100
          </p>
          <p className="text-xs mt-1" style={{ color: "var(--text-dim)" }}>
            {score >= 71
              ? "Strong runway & growth. Marketing overspend is the top drag."
              : score >= 41
              ? "Caution: burn rate rising. Take action within 60 days."
              : "Critical: immediate action needed on cash position."}
          </p>
          <button
            onClick={() => setOpen((o) => !o)}
            className="flex items-center gap-1 text-xs font-medium mt-2 transition-colors"
            style={{ color: "var(--accent)" }}
          >
            {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            What&apos;s driving this?
          </button>
        </div>
      </div>

      {/* Breakdown panel */}
      {open && (
        <div
          className="mt-4 pt-4 space-y-3 animate-fade-up"
          style={{ borderTop: "1px solid var(--border)" }}
        >
          <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>
            Score Breakdown
          </p>
          {drivers.map(({ label: dl, weight, score: ds, icon: Icon, color: dc, note }) => (
            <div key={dl}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5">
                  <Icon size={12} style={{ color: dc }} />
                  <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
                    {dl}
                  </span>
                  <span className="text-xs" style={{ color: "var(--text-dim)" }}>
                    ({weight})
                  </span>
                </div>
                <span className="text-xs font-semibold" style={{ color: dc }}>
                  {ds.toFixed(0)}/100
                </span>
              </div>
              <div
                className="rounded-full overflow-hidden"
                style={{ height: 4, background: "var(--bg)" }}
              >
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${Math.min(ds, 100)}%`, background: dc }}
                />
              </div>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-dim)" }}>
                {note}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Color legend */}
      <div
        className="flex items-center gap-4 mt-4 pt-3 text-xs"
        style={{ borderTop: "1px solid var(--border)", color: "var(--text-dim)" }}
      >
        <span style={{ color: "var(--danger)" }}>● 0–40 Critical</span>
        <span style={{ color: "var(--warning)" }}>● 41–70 Caution</span>
        <span style={{ color: "var(--accent)" }}>● 71–100 Good</span>
      </div>
    </div>
  );
}
