"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import {
  FileText,
  Download,
  FileSpreadsheet,
  Copy,
  Check,
  Calendar,
  RefreshCw,
  BarChart3,
  TrendingUp,
  PieChart,
  GitCompare,
  Layers,
  Target,
} from "lucide-react";

import {
  reportsApi,
  forecastApi,
  budgetsApi,
  dashboardApi,
  transactionsApi,
  setTokenProvider,
} from "@/lib/api";
import type {
  ReportSummary,
  ForecastResponse,
  Budget,
  DashboardSummary,
  Transaction,
} from "@/lib/types";

import {
  CashFlowTab,
  ForecastTab,
  VarianceTab,
  TrendsTab,
  CategoriesTab,
  CompareTab,
  AnnotationBox,
} from "@/components/ReportTabs";
import { ChartSkeleton } from "@/components/ReportCharts";

// ═══════════════════════════════════════════════════════════════
// Date helpers
// ═══════════════════════════════════════════════════════════════

function toISO(d: Date) {
  return d.toISOString().split("T")[0];
}

function getPresetDates(preset: string): [string, string] {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth();

  switch (preset) {
    case "this_month":
      return [toISO(new Date(y, m, 1)), toISO(now)];
    case "last_month":
      return [toISO(new Date(y, m - 1, 1)), toISO(new Date(y, m, 0))];
    case "last_3m":
      return [toISO(new Date(y, m - 3, 1)), toISO(now)];
    case "last_6m":
      return [toISO(new Date(y, m - 6, 1)), toISO(now)];
    case "ytd":
      return [toISO(new Date(y, 0, 1)), toISO(now)];
    case "last_year":
      return [toISO(new Date(y - 1, 0, 1)), toISO(new Date(y - 1, 11, 31))];
    case "all":
      return ["2020-01-01", toISO(now)];
    default:
      return [toISO(new Date(y, m - 3, 1)), toISO(now)];
  }
}

const PRESETS = [
  { key: "this_month", label: "This Month" },
  { key: "last_month", label: "Last Month" },
  { key: "last_3m", label: "3 Months" },
  { key: "last_6m", label: "6 Months" },
  { key: "ytd", label: "YTD" },
  { key: "all", label: "All Time" },
];

// ═══════════════════════════════════════════════════════════════
// Tab definitions
// ═══════════════════════════════════════════════════════════════

const TABS = [
  { key: "cashflow", label: "Cash Flow", icon: BarChart3 },
  { key: "forecast", label: "Forecast", icon: TrendingUp },
  { key: "variance", label: "Variance", icon: Target },
  { key: "trends", label: "Trends", icon: Layers },
  { key: "categories", label: "Categories", icon: PieChart },
  { key: "compare", label: "Compare", icon: GitCompare },
] as const;

type TabKey = (typeof TABS)[number]["key"];

// ═══════════════════════════════════════════════════════════════
// Main Page
// ═══════════════════════════════════════════════════════════════

interface Annotation { section: string; text: string; }
interface DrillDownState { category: string | null; transactions: Transaction[]; loading: boolean; }

export default function ReportsPage() {
  const { getToken } = useAuth();

  // ── State ────────────────────────────────────────────
  const [tab, setTab] = useState<TabKey>("cashflow");
  const [preset, setPreset] = useState("all");
  const [startDate, setStartDate] = useState(() => getPresetDates("all")[0]);
  const [endDate, setEndDate] = useState(() => getPresetDates("all")[1]);

  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [scenario, setScenario] = useState("base");

  const [compareData, setCompareData] = useState<ReportSummary | null>(null);
  const [comparePreset, setComparePreset] = useState("last_year");

  const [loading, setLoading] = useState(true);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [compareLoading, setCompareLoading] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [drillDown, setDrillDown] = useState<DrillDownState>({ category: null, transactions: [], loading: false });

  // ── Auth ─────────────────────────────────────────────
  useEffect(() => {
    setTokenProvider(getToken);
  }, [getToken]);

  // ── Data fetch ───────────────────────────────────────
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [summaryRes, budgetRes, dashRes] = await Promise.allSettled([
        reportsApi.summary(startDate, endDate),
        budgetsApi.list(),
        dashboardApi.getSummary(6),
      ]);

      if (summaryRes.status === "fulfilled") setSummary(summaryRes.value);
      if (budgetRes.status === "fulfilled") setBudgets(budgetRes.value);
      if (dashRes.status === "fulfilled") setDashboard(dashRes.value);
    } catch (e) {
      console.error("Reports fetch failed:", e);
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate]);

  useEffect(() => { loadData(); }, [loadData]);

  // ── Forecast fetch (separate, scenario-dependent) ───
  const loadForecast = useCallback(async () => {
    setForecastLoading(true);
    try {
      const res = await forecastApi.get(6, scenario);
      setForecast(res);
    } catch (e) {
      console.error("Forecast fetch failed:", e);
    } finally {
      setForecastLoading(false);
    }
  }, [scenario]);

  useEffect(() => {
    if (tab === "forecast") loadForecast();
  }, [tab, loadForecast]);

  // ── Compare fetch ────────────────────────────────────
  const loadCompare = useCallback(async () => {
    setCompareLoading(true);
    try {
      const [s, e] = getPresetDates(comparePreset);
      const res = await reportsApi.summary(s, e);
      setCompareData(res);
    } catch (err) {
      console.error("Compare fetch failed:", err);
    } finally {
      setCompareLoading(false);
    }
  }, [comparePreset]);

  useEffect(() => {
    if (tab === "compare") loadCompare();
  }, [tab, loadCompare]);

  // ── Drill-down handler ──────────────────────────────
  const handleDrillDown = useCallback(async (category: string) => {
    if (drillDown.category === category) {
      setDrillDown({ category: null, transactions: [], loading: false });
      return;
    }
    setDrillDown({ category, transactions: [], loading: true });
    try {
      const res = await transactionsApi.list({ category, per_page: 50 });
      setDrillDown({ category, transactions: res.items, loading: false });
    } catch {
      setDrillDown({ category, transactions: [], loading: false });
    }
  }, [drillDown.category]);

  // ── Annotation handler ──────────────────────────────
  const handleAnnotate = (section: string, text: string) => {
    setAnnotations((prev) => [...prev, { section, text }]);
  };

  // ── Preset change ───────────────────────────────────
  const handlePreset = (key: string) => {
    setPreset(key);
    const [s, e] = getPresetDates(key);
    setStartDate(s);
    setEndDate(e);
  };

  // ── Exports ─────────────────────────────────────────
  const handleExportCsv = async () => {
    setExporting("csv");
    try { await reportsApi.exportCsv(startDate, endDate); }
    catch (e) { console.error(e); }
    finally { setExporting(null); }
  };

  const handleExportPdf = async () => {
    setExporting("pdf");
    try { await reportsApi.exportPdf(startDate, endDate); }
    catch (e) { console.error(e); }
    finally { setExporting(null); }
  };

  const handleCopy = () => {
    if (!summary) return;
    const text = [
      `Financial Report: ${startDate} → ${endDate}`,
      `Income: $${summary.total_income.toLocaleString()}`,
      `Expenses: $${summary.total_expenses.toLocaleString()}`,
      `Net Cash Flow: $${summary.net_cash_flow.toLocaleString()}`,
      `Transactions: ${summary.transaction_count}`,
      `\nCategories:`,
      ...summary.expense_by_category.map((c) => `  ${c.category}: $${c.total.toLocaleString()} (${c.count} txns)`),
    ].join("\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ═══════════════════════════════════════════════════════
  // Render
  // ═══════════════════════════════════════════════════════

  return (
    <div className="page-container" style={{ maxWidth: 1100, margin: "0 auto" }}>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <FileText size={22} style={{ color: "var(--accent)" }} />
            Financial Reports
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Analyze, compare, and export financial data
          </p>
        </div>

        {/* Export buttons */}
        <div className="flex gap-2">
          <button onClick={handleCopy} className="btn-secondary flex items-center gap-1.5 text-xs" disabled={!summary}>
            {copied ? <Check size={14} /> : <Copy size={14} />}
            {copied ? "Copied!" : "Copy"}
          </button>
          <button onClick={handleExportCsv} className="btn-secondary flex items-center gap-1.5 text-xs" disabled={exporting === "csv"}>
            <FileSpreadsheet size={14} />
            {exporting === "csv" ? "Exporting…" : "CSV"}
          </button>
          <button onClick={handleExportPdf} className="btn-primary flex items-center gap-1.5 text-xs" disabled={exporting === "pdf"}>
            <Download size={14} />
            {exporting === "pdf" ? "Exporting…" : "PDF"}
          </button>
        </div>
      </div>

      {/* Date Controls */}
      <div className="glass p-4 mb-4">
        <div className="flex flex-col md:flex-row md:items-center gap-3">
          <div className="flex items-center gap-2">
            <Calendar size={14} style={{ color: "var(--text-dim)" }} />
            <span className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>Period</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {PRESETS.map((p) => (
              <button
                key={p.key}
                onClick={() => handlePreset(p.key)}
                className="px-3 py-1 text-xs rounded-lg font-medium transition-all"
                style={{
                  background: preset === p.key ? "var(--accent)" : "var(--surface-hover)",
                  color: preset === p.key ? "var(--bg)" : "var(--text)",
                  border: `1px solid ${preset === p.key ? "var(--accent)" : "var(--border)"}`,
                }}
              >
                {p.label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2 ml-auto">
            <input type="date" value={startDate} onChange={(e) => { setStartDate(e.target.value); setPreset(""); }} className="text-xs" />
            <span className="text-xs" style={{ color: "var(--text-dim)" }}>→</span>
            <input type="date" value={endDate} onChange={(e) => { setEndDate(e.target.value); setPreset(""); }} className="text-xs" />
            <button onClick={loadData} className="p-1.5 rounded-md" style={{ color: "var(--text-dim)" }} title="Refresh">
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-5 overflow-x-auto pb-1">
        {TABS.map((t) => {
          const Icon = t.icon;
          const active = tab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-lg whitespace-nowrap transition-all"
              style={{
                background: active ? "var(--accent)" : "transparent",
                color: active ? "var(--bg)" : "var(--text-muted)",
                border: `1px solid ${active ? "var(--accent)" : "var(--border)"}`,
              }}
            >
              <Icon size={14} />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      {loading && !summary ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map((i) => <ChartSkeleton key={i} height={90} />)}
          </div>
          <ChartSkeleton height={260} />
        </div>
      ) : !summary ? (
        <div className="glass p-12 text-center">
          <FileText size={32} className="mx-auto mb-3" style={{ color: "var(--text-dim)" }} />
          <p className="text-sm" style={{ color: "var(--text-dim)" }}>
            No data available for the selected period. Try a wider date range or upload transactions.
          </p>
        </div>
      ) : (
        <>
          {tab === "cashflow" && (
            <CashFlowTab data={summary} annotations={annotations} onAnnotate={handleAnnotate} onDrillDown={handleDrillDown} drillDown={drillDown} />
          )}

          {tab === "forecast" && (
            <ForecastTab forecast={forecast} scenario={scenario} onScenarioChange={setScenario} loading={forecastLoading} annotations={annotations} onAnnotate={handleAnnotate} />
          )}

          {tab === "variance" && (
            <VarianceTab summary={summary} budgets={budgets} annotations={annotations} onAnnotate={handleAnnotate} />
          )}

          {tab === "trends" && (
            <TrendsTab dashboard={dashboard} loading={loading} annotations={annotations} onAnnotate={handleAnnotate} />
          )}

          {tab === "categories" && (
            <CategoriesTab data={summary} annotations={annotations} onAnnotate={handleAnnotate} />
          )}

          {tab === "compare" && (
            <div className="space-y-4">
              {/* Compare period selector */}
              <div className="glass p-3 flex items-center gap-3">
                <span className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>Compare with:</span>
                {PRESETS.filter((p) => p.key !== preset).map((p) => (
                  <button
                    key={p.key}
                    onClick={() => setComparePreset(p.key)}
                    className="px-3 py-1 text-xs rounded-lg font-medium transition-all"
                    style={{
                      background: comparePreset === p.key ? "var(--info)" : "var(--surface-hover)",
                      color: comparePreset === p.key ? "#fff" : "var(--text)",
                      border: `1px solid ${comparePreset === p.key ? "var(--info)" : "var(--border)"}`,
                    }}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
              <CompareTab
                periodA={summary}
                periodB={compareData}
                labelA={PRESETS.find((p) => p.key === preset)?.label ?? "Current"}
                labelB={PRESETS.find((p) => p.key === comparePreset)?.label ?? "Compare"}
                loading={compareLoading}
                annotations={annotations}
                onAnnotate={handleAnnotate}
              />
            </div>
          )}
        </>
      )}

      {/* Period info footer */}
      {summary && (
        <div className="mt-6 text-xs text-center" style={{ color: "var(--text-dim)" }}>
          Report period: {summary.period_start} → {summary.period_end} · {summary.transaction_count} transactions
        </div>
      )}
    </div>
  );
}
