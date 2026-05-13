"use client";

import { useState } from "react";
import { useCurrency } from "@/components/CurrencyContext";

// ═══════════════════════════════════════════════════════════════════
// AI CFO — Report Chart Components
// Pure SVG/CSS charts for the Reports page. Zero external dependencies.
// Upgraded: cubic Bézier smoothing, gradient fills, polished hover states.
// ═══════════════════════════════════════════════════════════════════

const PALETTE = [
  "#C9A962", "#6B8EC2", "#9B7CB8", "#D4965A",
  "#5E9E7E", "#C75050", "#8B7355", "#7BA3A3",
  "#B8926A", "#7E9D6E", "#A07DA0", "#6A90B0",
];

// ── Format helpers ───────────────────────────────────────────────

function formatCurrencyValue(
  value: number,
  currencyCode: string,
  compact = false,
): string {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currencyCode,
      notation: compact ? "compact" : "standard",
      minimumFractionDigits: 0,
      maximumFractionDigits: compact ? 1 : 0,
    }).format(value);
  } catch {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: compact ? "compact" : "standard",
      minimumFractionDigits: 0,
      maximumFractionDigits: compact ? 1 : 0,
    }).format(value);
  }
}

function formatAxisValue(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  return v.toFixed(0);
}

// ── Donut Chart ──────────────────────────────────────────────────

interface DonutSlice {
  label: string;
  value: number;
}

export function DonutChart({
  data,
  size = 230,
  thickness = 38,
  currencyCode: currencyCodeProp,
}: {
  data: DonutSlice[];
  size?: number;
  thickness?: number;
  currencyCode?: string;
}) {
  const [hovered, setHovered] = useState<number | null>(null);
  const { currencyCode: contextCurrencyCode } = useCurrency();
  const currencyCode = currencyCodeProp || contextCurrencyCode;
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return <EmptyChart label="No category data" />;

  const radius = (size - thickness) / 2;
  const cx = size / 2;
  const cy = size / 2;

  let cumAngle = -90;
  const slices = data.map((d, i) => {
    const pct = d.value / total;
    const angle = pct * 360;
    const startAngle = cumAngle;
    cumAngle += angle;
    const endAngle = cumAngle;

    const startRad = (startAngle * Math.PI) / 180;
    const endRad = (endAngle * Math.PI) / 180;
    const largeArc = angle > 180 ? 1 : 0;

    const x1 = cx + radius * Math.cos(startRad);
    const y1 = cy + radius * Math.sin(startRad);
    const x2 = cx + radius * Math.cos(endRad);
    const y2 = cy + radius * Math.sin(endRad);

    const d_path = [
      `M ${x1} ${y1}`,
      `A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`,
    ].join(" ");

    return { ...d, path: d_path, color: PALETTE[i % PALETTE.length], pct, idx: i };
  });

  return (
    <div className="flex flex-col sm:flex-row items-center gap-6">
      <div style={{ position: "relative", width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          style={{ overflow: "visible" }}
        >
          {/* Subtle shadow ring */}
          <circle
            cx={cx}
            cy={cy}
            r={radius}
            fill="none"
            stroke="var(--border)"
            strokeWidth={thickness + 10}
            opacity={0.15}
          />
          {slices.map((s) => (
            <path
              key={s.idx}
              d={s.path}
              fill="none"
              stroke={s.color}
              strokeWidth={hovered === s.idx ? thickness + 8 : thickness}
              strokeLinecap="butt"
              style={{
                transition: "stroke-width 0.25s cubic-bezier(.4,0,.2,1), opacity 0.25s ease",
                cursor: "pointer",
                opacity: hovered !== null && hovered !== s.idx ? 0.35 : 1,
                filter: hovered === s.idx ? `drop-shadow(0 0 8px ${s.color}66)` : "none",
              }}
              onMouseEnter={() => setHovered(s.idx)}
              onMouseLeave={() => setHovered(null)}
            />
          ))}
          {/* Center text */}
          <text
            x={cx}
            y={cy - 8}
            textAnchor="middle"
            fontSize="20"
            fontWeight="700"
            fill="var(--text)"
            style={{ fontFamily: "var(--font-mono, monospace)" }}
          >
            {hovered !== null
              ? formatCurrencyValue(slices[hovered].value, currencyCode, true)
              : formatCurrencyValue(total, currencyCode, true)}
          </text>
          <text
            x={cx}
            y={cy + 12}
            textAnchor="middle"
            fontSize="10"
            fill="var(--text-muted)"
          >
            {hovered !== null ? slices[hovered].label : "Total Spend"}
          </text>
          {hovered !== null && (
            <text
              x={cx}
              y={cy + 26}
              textAnchor="middle"
              fontSize="10"
              fontWeight="600"
              fill={slices[hovered].color}
            >
              {(slices[hovered].pct * 100).toFixed(1)}%
            </text>
          )}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex flex-col gap-1.5 min-w-0">
        {slices.slice(0, 8).map((s) => (
          <div
            key={s.idx}
            className="flex items-center gap-2 text-xs cursor-pointer rounded-md px-2 py-1"
            style={{
              opacity: hovered !== null && hovered !== s.idx ? 0.35 : 1,
              background: hovered === s.idx ? `${s.color}12` : "transparent",
              transition: "all 0.2s ease",
            }}
            onMouseEnter={() => setHovered(s.idx)}
            onMouseLeave={() => setHovered(null)}
          >
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: "3px",
                background: s.color,
                flexShrink: 0,
                boxShadow: hovered === s.idx ? `0 0 6px ${s.color}88` : "none",
              }}
            />
            <span
              className="truncate"
              style={{ color: "var(--text)", maxWidth: 130, fontWeight: hovered === s.idx ? 600 : 400 }}
            >
              {s.label}
            </span>
            <span className="ml-auto font-mono tabular-nums" style={{ color: "var(--text-muted)" }}>
              {(s.pct * 100).toFixed(1)}%
            </span>
          </div>
        ))}
        {data.length > 8 && (
          <span className="text-xs px-2" style={{ color: "var(--text-dim)" }}>
            +{data.length - 8} more
          </span>
        )}
      </div>
    </div>
  );
}

// ── Bar Chart (Vertical) ─────────────────────────────────────────

interface BarItem {
  label: string;
  value: number;
  color?: string;
}

export function BarChart({
  data,
  height = 200,
  showValues = true,
  currencyCode: currencyCodeProp,
}: {
  data: BarItem[];
  height?: number;
  showValues?: boolean;
  currencyCode?: string;
}) {
  const [hovered, setHovered] = useState<number | null>(null);
  const { currencyCode: contextCurrencyCode } = useCurrency();
  const currencyCode = currencyCodeProp || contextCurrencyCode;
  const max = Math.max(...data.map((d) => d.value), 1);
  if (data.length === 0) return <EmptyChart label="No data" />;

  return (
    <div className="w-full">
      <div
        className="flex items-end gap-2"
        style={{ height, paddingBottom: 28 }}
      >
        {data.map((d, i) => {
          const barH = (d.value / max) * (height - 44);
          const isHov = hovered === i;
          const color = d.color || PALETTE[i % PALETTE.length];
          return (
            <div
              key={i}
              className="flex-1 flex flex-col items-center justify-end"
              style={{ height: "100%" }}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
            >
              {showValues && isHov && (
                <div
                  className="text-xs font-mono mb-1.5 px-2 py-0.5 rounded-md"
                  style={{
                    color: "#fff",
                    background: color,
                    fontSize: 10,
                    whiteSpace: "nowrap",
                  }}
                >
                  {formatCurrencyValue(d.value, currencyCode, true)}
                </div>
              )}
              <div
                style={{
                  width: "100%",
                  maxWidth: 52,
                  height: Math.max(barH, 3),
                  borderRadius: "8px 8px 2px 2px",
                  background: `linear-gradient(180deg, ${color}, ${color}bb)`,
                  opacity: hovered !== null && !isHov ? 0.35 : 1,
                  transition: "all 0.3s cubic-bezier(.4,0,.2,1)",
                  transform: isHov ? "scaleY(1.05)" : "scaleY(1)",
                  transformOrigin: "bottom",
                  cursor: "pointer",
                  boxShadow: isHov ? `0 4px 16px ${color}44` : "none",
                }}
              />
            </div>
          );
        })}
      </div>
      <div className="flex gap-2">
        {data.map((d, i) => (
          <div key={i} className="flex-1 text-center">
            <span
              className="text-xs truncate block"
              style={{
                color: hovered === i ? "var(--text)" : "var(--text-dim)",
                fontWeight: hovered === i ? 600 : 400,
                transition: "all 0.15s",
              }}
              title={d.label}
            >
              {d.label.length > 10 ? `${d.label.slice(0, 9)}...` : d.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Line Chart (Cubic Bézier Smooth) ─────────────────────────────

interface LineDataset {
  label: string;
  values: number[];
  color: string;
}

export function LineChart({
  labels,
  datasets,
  height = 240,
  currencyCode: currencyCodeProp,
}: {
  labels: string[];
  datasets: LineDataset[];
  height?: number;
  currencyCode?: string;
}) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const { currencyCode: contextCurrencyCode } = useCurrency();
  const currencyCode = currencyCodeProp || contextCurrencyCode;
  const allVals = datasets.flatMap((d) => d.values);
  const rawMax = Math.max(...allVals, 1);
  const rawMin = Math.min(...allVals, 0);
  // Add 10% padding to range
  const padding = (rawMax - rawMin) * 0.1 || 1;
  const max = rawMax + padding;
  const min = rawMin < 0 ? rawMin - padding : 0;
  const range = max - min || 1;

  const width = 540;
  const padX = 50;
  const padY = 24;
  const chartW = width - padX * 2;
  const chartH = height - padY * 2;
  const n = labels.length;
  if (n === 0) return <EmptyChart label="No trend data" />;

  const xStep = chartW / Math.max(n - 1, 1);

  const toPoint = (val: number, i: number) => ({
    x: padX + i * xStep,
    y: padY + chartH - ((val - min) / range) * chartH,
  });

  // Cubic Bézier smooth path builder
  const buildSmoothPath = (vals: number[]) => {
    if (vals.length < 2) {
      const p = toPoint(vals[0] || 0, 0);
      return `M ${p.x} ${p.y}`;
    }

    const points = vals.map((v, i) => toPoint(v, i));
    let path = `M ${points[0].x} ${points[0].y}`;

    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[Math.max(i - 1, 0)];
      const p1 = points[i];
      const p2 = points[i + 1];
      const p3 = points[Math.min(i + 2, points.length - 1)];

      const tension = 0.3;
      const cp1x = p1.x + (p2.x - p0.x) * tension;
      const cp1y = p1.y + (p2.y - p0.y) * tension;
      const cp2x = p2.x - (p3.x - p1.x) * tension;
      const cp2y = p2.y - (p3.y - p1.y) * tension;

      path += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
    }
    return path;
  };

  // Grid lines
  const gridLines = 5;
  const gridY = Array.from({ length: gridLines + 1 }, (_, i) => {
    const y = padY + (chartH / gridLines) * i;
    const val = max - (range / gridLines) * i;
    return { y, val };
  });

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        style={{ minWidth: 380, maxHeight: height + 20 }}
        onMouseLeave={() => setHoveredIdx(null)}
      >
        {/* Grid */}
        {gridY.map((g, i) => (
          <g key={i}>
            <line
              x1={padX}
              y1={g.y}
              x2={width - padX}
              y2={g.y}
              stroke="var(--border)"
              strokeDasharray={i === gridLines ? "0" : "3 6"}
              strokeWidth="0.5"
              opacity={0.6}
            />
            <text
              x={padX - 8}
              y={g.y + 3}
              textAnchor="end"
              fontSize="9"
              fill="var(--text-dim)"
              style={{ fontFamily: "var(--font-mono, monospace)" }}
            >
              {formatAxisValue(g.val)}
            </text>
          </g>
        ))}

        {/* Area fills & Lines */}
        {datasets.map((ds, di) => {
          const smoothPath = buildSmoothPath(ds.values);
          const lastPt = toPoint(ds.values[ds.values.length - 1], ds.values.length - 1);
          const firstPt = toPoint(ds.values[0], 0);
          const areaPath = `${smoothPath} L ${lastPt.x} ${padY + chartH} L ${firstPt.x} ${padY + chartH} Z`;

          return (
            <g key={di}>
              <defs>
                <linearGradient id={`areafill-${di}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={ds.color} stopOpacity="0.2" />
                  <stop offset="100%" stopColor={ds.color} stopOpacity="0.02" />
                </linearGradient>
              </defs>
              {/* Area */}
              <path d={areaPath} fill={`url(#areafill-${di})`} />
              {/* Smooth line */}
              <path
                d={smoothPath}
                fill="none"
                stroke={ds.color}
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              {/* Data dots */}
              {ds.values.map((v, i) => {
                const p = toPoint(v, i);
                const isHov = hoveredIdx === i;
                return (
                  <g key={i}>
                    {isHov && (
                      <circle
                        cx={p.x}
                        cy={p.y}
                        r={10}
                        fill={`${ds.color}18`}
                      />
                    )}
                    <circle
                      cx={p.x}
                      cy={p.y}
                      r={isHov ? 5 : 3}
                      fill={isHov ? ds.color : "var(--bg)"}
                      stroke={ds.color}
                      strokeWidth={isHov ? 2.5 : 2}
                      style={{ transition: "all 0.15s ease" }}
                    />
                  </g>
                );
              })}
            </g>
          );
        })}

        {/* X labels */}
        {labels.map((l, i) => {
          const x = padX + i * xStep;
          return (
            <text
              key={i}
              x={x}
              y={height - 2}
              textAnchor="middle"
              fontSize="10"
              fill={hoveredIdx === i ? "var(--text)" : "var(--text-dim)"}
              fontWeight={hoveredIdx === i ? 600 : 400}
            >
              {l}
            </text>
          );
        })}

        {/* Hover columns */}
        {labels.map((_, i) => {
          const x = padX + i * xStep;
          return (
            <rect
              key={i}
              x={x - xStep / 2}
              y={padY}
              width={xStep}
              height={chartH}
              fill="transparent"
              onMouseEnter={() => setHoveredIdx(i)}
              style={{ cursor: "crosshair" }}
            />
          );
        })}

        {/* Hover vertical line */}
        {hoveredIdx !== null && (
          <line
            x1={padX + hoveredIdx * xStep}
            y1={padY}
            x2={padX + hoveredIdx * xStep}
            y2={padY + chartH}
            stroke="var(--text-dim)"
            strokeDasharray="3 3"
            strokeWidth="1"
            opacity={0.5}
          />
        )}
      </svg>

      {/* Legend */}
      <div className="flex items-center gap-5 mt-3 justify-center">
        {datasets.map((ds, i) => (
          <div key={i} className="flex items-center gap-2">
            <div
              style={{
                width: 14,
                height: 3,
                borderRadius: 2,
                background: ds.color,
              }}
            />
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              {ds.label}
            </span>
          </div>
        ))}
      </div>

      {/* Hover tooltip */}
      {hoveredIdx !== null && (
        <div
          className="flex gap-4 justify-center mt-2 px-3 py-1.5 rounded-lg mx-auto w-fit"
          style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
        >
          <span className="text-xs" style={{ color: "var(--text-dim)" }}>
            {labels[hoveredIdx]}
          </span>
          {datasets.map((ds, i) => (
            <span key={i} className="text-xs font-mono font-semibold" style={{ color: ds.color }}>
              {ds.label}: {formatCurrencyValue(ds.values[hoveredIdx] ?? 0, currencyCode, true)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Variance Bar ─────────────────────────────────────────────────

export function VarianceBar({
  budget,
  actual,
  label,
  currencyCode: currencyCodeProp,
}: {
  budget: number;
  actual: number;
  label: string;
  currencyCode?: string;
}) {
  const { currencyCode: contextCurrencyCode } = useCurrency();
  const currencyCode = currencyCodeProp || contextCurrencyCode;
  const pct = budget > 0 ? (actual / budget) * 100 : 0;
  const variance = actual - budget;
  const over = variance > 0;

  const barColor = over
    ? "var(--danger)"
    : pct > 80
      ? "var(--warning)"
      : "var(--success)";

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span style={{ color: "var(--text)", fontWeight: 500 }}>{label}</span>
        <span
          className="font-mono font-semibold"
          style={{ color: over ? "var(--danger)" : "var(--success)" }}
        >
          {over ? "+" : ""}{formatCurrencyValue(Math.abs(variance), currencyCode)} ({pct.toFixed(0)}%)
        </span>
      </div>
      <div
        className="relative rounded-full overflow-hidden"
        style={{ height: 10, background: "var(--surface-hover)" }}
      >
        <div
          className="absolute inset-y-0 left-0 rounded-full"
          style={{
            width: `${Math.min(pct, 100)}%`,
            background: barColor,
            transition: "width 0.8s cubic-bezier(.4,0,.2,1)",
            boxShadow: over ? `0 0 8px var(--danger)44` : "none",
          }}
        />
        {/* Budget target line */}
        <div
          className="absolute inset-y-0"
          style={{
            left: "100%",
            width: 2,
            background: "var(--text-dim)",
            transform: "translateX(-1px)",
          }}
        />
      </div>
      <div className="flex justify-between text-xs" style={{ color: "var(--text-dim)" }}>
        <span>Actual: {formatCurrencyValue(actual, currencyCode)}</span>
        <span>Budget: {formatCurrencyValue(budget, currencyCode)}</span>
      </div>
    </div>
  );
}

// ── Comparison Table ─────────────────────────────────────────────

interface CompareRow {
  metric: string;
  periodA: number;
  periodB: number;
  format?: "currency" | "number" | "percent";
  direction?: "higher" | "lower" | "neutral";
}

export function ComparisonTable({
  rows,
  periodALabel,
  periodBLabel,
  currencyCode: currencyCodeProp,
}: {
  rows: CompareRow[];
  periodALabel: string;
  periodBLabel: string;
  currencyCode?: string;
}) {
  const { currencyCode: contextCurrencyCode } = useCurrency();
  const currencyCode = currencyCodeProp || contextCurrencyCode;
  const fmt = (v: number, f?: string) => {
    if (f === "percent") return `${v.toFixed(1)}%`;
    if (f === "number") return v.toLocaleString();
    return formatCurrencyValue(v, currencyCode);
  };

  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full text-sm" style={{ borderCollapse: "separate", borderSpacing: "0 4px" }}>
        <thead>
          <tr>
            <th className="text-left text-xs font-semibold pb-2 px-3" style={{ color: "var(--text-muted)" }}>
              Metric
            </th>
            <th className="text-right text-xs font-semibold pb-2 px-3" style={{ color: "var(--accent)" }}>
              {periodALabel}
            </th>
            <th className="text-right text-xs font-semibold pb-2 px-3" style={{ color: "var(--info)" }}>
              {periodBLabel}
            </th>
            <th className="text-right text-xs font-semibold pb-2 px-3" style={{ color: "var(--text-muted)" }}>
              Change
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const delta = r.periodB !== 0
              ? ((r.periodA - r.periodB) / Math.abs(r.periodB)) * 100
              : r.periodA > 0 ? 100 : 0;
            const direction = r.direction ?? "neutral";
            const positive = direction === "neutral"
              ? delta === 0
              : direction === "higher"
                ? delta >= 0
                : delta <= 0;
            const deltaColor = direction === "neutral"
              ? "var(--info)"
              : positive
                ? "var(--success)"
                : "var(--danger)";
            const deltaDisplay = delta > 0
              ? `+${delta.toFixed(1)}%`
              : delta < 0
                ? `${delta.toFixed(1)}%`
                : "0.0%";

            return (
              <tr
                key={i}
                className="rounded-lg"
                style={{ background: "var(--surface)" }}
              >
                <td className="px-3 py-2.5 rounded-l-lg font-medium" style={{ color: "var(--text)" }}>
                  {r.metric}
                </td>
                <td className="text-right px-3 py-2.5 font-mono" style={{ color: "var(--text)" }}>
                  {fmt(r.periodA, r.format)}
                </td>
                <td className="text-right px-3 py-2.5 font-mono" style={{ color: "var(--text)" }}>
                  {fmt(r.periodB, r.format)}
                </td>
                <td className="text-right px-3 py-2.5 rounded-r-lg font-mono font-semibold" style={{
                  color: deltaColor,
                }}>
                  {deltaDisplay}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Metric Card ──────────────────────────────────────────────────

export function MetricCard({
  label,
  value,
  subtext,
  trend,
  icon,
}: {
  label: string;
  value: string;
  subtext?: string;
  trend?: "up" | "down" | "neutral";
  icon?: React.ReactNode;
}) {
  return (
    <div
      className="p-4 rounded-xl"
      style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
          {label}
        </span>
        {icon && <span style={{ color: "var(--text-dim)" }}>{icon}</span>}
      </div>
      <div className="text-lg font-bold font-mono" style={{ color: "var(--text)" }}>
        {value}
      </div>
      {subtext && (
        <div
          className="text-xs mt-1 font-medium"
          style={{
            color: trend === "up" ? "var(--success)" : trend === "down" ? "var(--danger)" : "var(--text-dim)",
          }}
        >
          {trend === "up" ? "↑ " : trend === "down" ? "↓ " : ""}{subtext}
        </div>
      )}
    </div>
  );
}

// ── Skeleton Loader ──────────────────────────────────────────────

export function ChartSkeleton({ height = 200 }: { height?: number }) {
  return (
    <div
      className="w-full rounded-xl animate-pulse"
      style={{ height, background: "var(--surface-hover)" }}
    />
  );
}

// ── Empty State ──────────────────────────────────────────────────

function EmptyChart({ label }: { label: string }) {
  return (
    <div
      className="flex items-center justify-center rounded-xl"
      style={{
        height: 160,
        background: "var(--surface)",
        border: "1px dashed var(--border)",
        color: "var(--text-dim)",
      }}
    >
      <span className="text-sm">{label}</span>
    </div>
  );
}
