"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import {
  BarChart3,
  Calendar,
  Check,
  Copy,
  Download,
  FileSpreadsheet,
  FileText,
  GitCompare,
  Layers,
  PieChart,
  RefreshCw,
  Target,
  TrendingUp,
} from "lucide-react";

import {
  dashboardApi,
  forecastApi,
  reportsApi,
  setTokenProvider,
  transactionsApi,
} from "@/lib/api";
import { useCurrency } from "@/components/CurrencyContext";
import { ChartSkeleton } from "@/components/ReportCharts";
import {
  CashFlowTab,
  CategoriesTab,
  CompareTab,
  ForecastTab,
  TrendsTab,
  VarianceTab,
} from "@/components/ReportTabs";
import type {
  DashboardSummary,
  ForecastResponse,
  ReportSummary,
  Transaction,
} from "@/lib/types";

function toISO(date: Date) {
  return date.toISOString().split("T")[0];
}

function getPresetDates(preset: string): [string, string] {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();

  switch (preset) {
    case "this_month":
      return [toISO(new Date(year, month, 1)), toISO(now)];
    case "last_month":
      return [toISO(new Date(year, month - 1, 1)), toISO(new Date(year, month, 0))];
    case "last_3m":
      return [toISO(new Date(year, month - 3, 1)), toISO(now)];
    case "last_6m":
      return [toISO(new Date(year, month - 6, 1)), toISO(now)];
    case "ytd":
      return [toISO(new Date(year, 0, 1)), toISO(now)];
    case "last_year":
      return [toISO(new Date(year - 1, 0, 1)), toISO(new Date(year - 1, 11, 31))];
    case "all":
      return ["2020-01-01", toISO(now)];
    default:
      return [toISO(new Date(year, month - 3, 1)), toISO(now)];
  }
}

function formatDetailedMoney(value: number, currencyCode: string) {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currencyCode,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
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

const TABS = [
  { key: "cashflow", label: "Cash Flow", icon: BarChart3 },
  { key: "forecast", label: "Forecast", icon: TrendingUp },
  { key: "variance", label: "Variance", icon: Target },
  { key: "trends", label: "Trends", icon: Layers },
  { key: "categories", label: "Categories", icon: PieChart },
  { key: "compare", label: "Compare", icon: GitCompare },
] as const;

type TabKey = (typeof TABS)[number]["key"];

interface Annotation {
  section: string;
  text: string;
}

interface DrillDownState {
  category: string | null;
  transactions: Transaction[];
  loading: boolean;
}

export default function ReportsPage() {
  const { getToken } = useAuth();
  const { currencyCode } = useCurrency();

  const [tab, setTab] = useState<TabKey>("cashflow");
  const [preset, setPreset] = useState("all");
  const [startDate, setStartDate] = useState(() => getPresetDates("all")[0]);
  const [endDate, setEndDate] = useState(() => getPresetDates("all")[1]);
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [scenario, setScenario] = useState("base");
  const [compareData, setCompareData] = useState<ReportSummary | null>(null);
  const [comparePreset, setComparePreset] = useState("last_year");
  const [loading, setLoading] = useState(true);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [compareLoading, setCompareLoading] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [drillDown, setDrillDown] = useState<DrillDownState>({
    category: null,
    transactions: [],
    loading: false,
  });

  useEffect(() => {
    setTokenProvider(getToken);
  }, [getToken]);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [summaryResult, dashboardResult] = await Promise.allSettled([
        reportsApi.summary(startDate, endDate),
        dashboardApi.getSummary(6),
      ]);

      if (summaryResult.status === "fulfilled") {
        setSummary(summaryResult.value);
      } else {
        setSummary(null);
      }

      if (dashboardResult.status === "fulfilled") {
        setDashboard(dashboardResult.value);
      } else {
        setDashboard(null);
      }

      if (summaryResult.status === "rejected" && dashboardResult.status === "rejected") {
        setError("Unable to load reporting data for the selected period.");
      }
    } catch {
      setSummary(null);
      setDashboard(null);
      setError("Unable to load reporting data for the selected period.");
    } finally {
      setLoading(false);
    }
  }, [endDate, startDate]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const loadForecast = useCallback(async () => {
    setForecastLoading(true);
    try {
      const result = await forecastApi.get(6, scenario);
      setForecast(result);
    } catch {
      setForecast(null);
    } finally {
      setForecastLoading(false);
    }
  }, [scenario]);

  useEffect(() => {
    if (tab === "forecast") {
      loadForecast();
    }
  }, [loadForecast, tab]);

  const loadCompare = useCallback(async () => {
    setCompareLoading(true);
    try {
      const [compareStart, compareEnd] = getPresetDates(comparePreset);
      const result = await reportsApi.summary(compareStart, compareEnd);
      setCompareData(result);
    } catch {
      setCompareData(null);
    } finally {
      setCompareLoading(false);
    }
  }, [comparePreset]);

  useEffect(() => {
    if (tab === "compare") {
      loadCompare();
    }
  }, [loadCompare, tab]);

  const handleDrillDown = useCallback(async (category: string) => {
    if (drillDown.category === category) {
      setDrillDown({ category: null, transactions: [], loading: false });
      return;
    }

    setDrillDown({ category, transactions: [], loading: true });
    try {
      const result = await transactionsApi.list({
        category,
        type: "expense",
        start_date: startDate,
        end_date: endDate,
        per_page: 50,
      });
      setDrillDown({ category, transactions: result.items, loading: false });
    } catch {
      setDrillDown({ category, transactions: [], loading: false });
    }
  }, [drillDown.category, endDate, startDate]);

  const handleAnnotate = (section: string, text: string) => {
    setAnnotations((current) => [...current, { section, text }]);
  };

  const handlePreset = (key: string) => {
    setPreset(key);
    const [nextStart, nextEnd] = getPresetDates(key);
    setStartDate(nextStart);
    setEndDate(nextEnd);
    setDrillDown({ category: null, transactions: [], loading: false });
  };

  const handleExportCsv = async () => {
    setExporting("csv");
    try {
      await reportsApi.exportCsv(startDate, endDate);
    } finally {
      setExporting(null);
    }
  };

  const handleExportPdf = async () => {
    setExporting("pdf");
    try {
      await reportsApi.exportPdf(startDate, endDate);
    } finally {
      setExporting(null);
    }
  };

  const handleCopy = () => {
    if (!summary) return;

    const reportCurrency = summary.base_currency || currencyCode;
    const lines = [
      `Financial report: ${summary.period_start} to ${summary.period_end}`,
      `Workspace currency: ${reportCurrency}`,
      `Income: ${formatDetailedMoney(summary.total_income, reportCurrency)}`,
      `Expenses: ${formatDetailedMoney(summary.total_expenses, reportCurrency)}`,
      `Net cash flow: ${formatDetailedMoney(summary.net_cash_flow, reportCurrency)}`,
      `Budgeted spend: ${formatDetailedMoney(summary.budget_total, reportCurrency)}`,
      `Transactions: ${summary.transaction_count}`,
      "",
      "Expense categories:",
      ...summary.expense_by_category.map(
        (item) => `  ${item.category}: ${formatDetailedMoney(item.total, reportCurrency)} (${item.count} txns)`,
      ),
    ];

    if (summary.budget_variance.length > 0) {
      lines.push("", "Budget variance:");
      lines.push(
        ...summary.budget_variance.slice(0, 5).map(
          (item) =>
            `  ${item.category}: budget ${formatDetailedMoney(item.budget, reportCurrency)}, actual ${formatDetailedMoney(item.actual, reportCurrency)}, variance ${formatDetailedMoney(item.variance, reportCurrency)}`,
        ),
      );
    }

    navigator.clipboard.writeText(lines.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const reportCurrency = summary?.base_currency || currencyCode;
  const reportDateLabel = summary ? `${summary.period_start} to ${summary.period_end}` : `${startDate} to ${endDate}`;

  return (
    <div className="page-container" style={{ maxWidth: 1180, margin: "0 auto" }}>
      <section
        className="glass overflow-hidden mb-5"
        style={{
          background: `
            radial-gradient(circle at top left, rgba(201, 169, 98, 0.18), transparent 36%),
            radial-gradient(circle at top right, rgba(107, 142, 194, 0.16), transparent 28%),
            linear-gradient(180deg, rgba(17,17,17,0.96), rgba(8,8,8,0.98))
          `,
        }}
      >
        <div className="grid grid-cols-1 xl:grid-cols-[1.2fr_0.8fr] gap-5 p-5 md:p-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-semibold uppercase tracking-[0.18em]" style={{ background: "rgba(201, 169, 98, 0.12)", color: "var(--accent)", border: "1px solid rgba(201, 169, 98, 0.24)" }}>
              <FileText size={12} />
              Reporting Suite
            </div>
            <h1 className="text-2xl md:text-3xl font-semibold mt-4" style={{ color: "var(--text)" }}>
              Financial reports in workspace currency, ready to review or export.
            </h1>
            <p className="text-sm mt-3 max-w-2xl" style={{ color: "var(--text-muted)", lineHeight: 1.7 }}>
              Cash flow, forecasts, budget variance, trends, category mix, and comparison views are all driven from the same reporting window. CSV now includes original currency metadata, and PDF export is formatted for board-ready sharing.
            </p>

            <div className="flex flex-wrap gap-2 mt-5">
              <div className="px-3 py-2 rounded-xl text-xs" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)", color: "var(--text-muted)" }}>
                <div className="uppercase tracking-[0.16em] text-[10px]" style={{ color: "var(--text-dim)" }}>Base Currency</div>
                <div className="font-semibold mt-1" style={{ color: "var(--text)" }}>{reportCurrency}</div>
              </div>
              <div className="px-3 py-2 rounded-xl text-xs" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)", color: "var(--text-muted)" }}>
                <div className="uppercase tracking-[0.16em] text-[10px]" style={{ color: "var(--text-dim)" }}>Report Window</div>
                <div className="font-semibold mt-1" style={{ color: "var(--text)" }}>{reportDateLabel}</div>
              </div>
              <div className="px-3 py-2 rounded-xl text-xs" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)", color: "var(--text-muted)" }}>
                <div className="uppercase tracking-[0.16em] text-[10px]" style={{ color: "var(--text-dim)" }}>Transactions</div>
                <div className="font-semibold mt-1" style={{ color: "var(--text)" }}>{summary?.transaction_count ?? "..."}</div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 xl:grid-cols-1 gap-3">
            <button
              onClick={handleCopy}
              disabled={!summary}
              className="text-left rounded-2xl p-4 transition-all"
              style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)", color: "var(--text)" }}
            >
              <div className="flex items-center gap-2 text-sm font-semibold">
                {copied ? <Check size={15} style={{ color: "var(--success)" }} /> : <Copy size={15} style={{ color: "var(--accent)" }} />}
                {copied ? "Copied snapshot" : "Copy summary"}
              </div>
              <p className="text-xs mt-2" style={{ color: "var(--text-muted)", lineHeight: 1.6 }}>
                Share the current report in clean workspace-currency text with category and budget highlights.
              </p>
            </button>

            <button
              onClick={handleExportCsv}
              disabled={exporting === "csv"}
              className="text-left rounded-2xl p-4 transition-all"
              style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)", color: "var(--text)" }}
            >
              <div className="flex items-center gap-2 text-sm font-semibold">
                <FileSpreadsheet size={15} style={{ color: "var(--info)" }} />
                {exporting === "csv" ? "Exporting CSV..." : "Export CSV"}
              </div>
              <p className="text-xs mt-2" style={{ color: "var(--text-muted)", lineHeight: 1.6 }}>
                Download transaction-level data with workspace currency, original currency, and exchange-rate columns.
              </p>
            </button>

            <button
              onClick={handleExportPdf}
              disabled={exporting === "pdf"}
              className="text-left rounded-2xl p-4 transition-all"
              style={{ background: "rgba(201,169,98,0.14)", border: "1px solid rgba(201,169,98,0.35)", color: "var(--text)" }}
            >
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Download size={15} style={{ color: "var(--accent)" }} />
                {exporting === "pdf" ? "Exporting PDF..." : "Export PDF"}
              </div>
              <p className="text-xs mt-2" style={{ color: "var(--text-muted)", lineHeight: 1.6 }}>
                Generate a polished summary with budget-vs-actual, top vendors, and workspace-currency totals.
              </p>
            </button>
          </div>
        </div>
      </section>

      <div className="glass p-4 mb-4">
        <div className="flex flex-col lg:flex-row lg:items-center gap-4">
          <div className="flex items-center gap-2">
            <Calendar size={14} style={{ color: "var(--text-dim)" }} />
            <span className="text-xs font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--text-muted)" }}>
              Reporting Window
            </span>
          </div>

          <div className="flex flex-wrap gap-1.5">
            {PRESETS.map((presetOption) => (
              <button
                key={presetOption.key}
                onClick={() => handlePreset(presetOption.key)}
                className="px-3 py-1.5 text-xs rounded-lg font-medium transition-all"
                style={{
                  background: preset === presetOption.key ? "var(--accent)" : "var(--surface-hover)",
                  color: preset === presetOption.key ? "var(--bg)" : "var(--text)",
                  border: `1px solid ${preset === presetOption.key ? "var(--accent)" : "var(--border)"}`,
                }}
              >
                {presetOption.label}
              </button>
            ))}
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center gap-2 lg:ml-auto">
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={startDate}
                onChange={(event) => {
                  setStartDate(event.target.value);
                  setPreset("");
                  setDrillDown({ category: null, transactions: [], loading: false });
                }}
                className="text-xs"
              />
              <span className="text-xs" style={{ color: "var(--text-dim)" }}>to</span>
              <input
                type="date"
                value={endDate}
                onChange={(event) => {
                  setEndDate(event.target.value);
                  setPreset("");
                  setDrillDown({ category: null, transactions: [], loading: false });
                }}
                className="text-xs"
              />
            </div>
            <button
              onClick={loadData}
              className="px-3 py-2 rounded-lg text-xs flex items-center justify-center gap-1.5"
              style={{ color: "var(--text-muted)", border: "1px solid var(--border)", background: "var(--surface-hover)" }}
              title="Refresh report"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="glass p-2 mb-5 overflow-x-auto">
        <div className="flex gap-1 min-w-max">
          {TABS.map((tabOption) => {
            const Icon = tabOption.icon;
            const active = tab === tabOption.key;
            return (
              <button
                key={tabOption.key}
                onClick={() => setTab(tabOption.key)}
                className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium rounded-xl whitespace-nowrap transition-all"
                style={{
                  background: active ? "linear-gradient(135deg, rgba(201,169,98,1), rgba(214,148,90,0.9))" : "transparent",
                  color: active ? "#0a0a0a" : "var(--text-muted)",
                  border: `1px solid ${active ? "rgba(201,169,98,0.7)" : "transparent"}`,
                }}
              >
                <Icon size={14} />
                {tabOption.label}
              </button>
            );
          })}
        </div>
      </div>

      {error && (
        <div className="glass p-4 mb-4 text-sm" style={{ borderColor: "rgba(199, 80, 80, 0.4)", color: "var(--danger)", background: "rgba(199, 80, 80, 0.08)" }}>
          {error}
        </div>
      )}

      {loading && !summary ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map((index) => <ChartSkeleton key={index} height={90} />)}
          </div>
          <ChartSkeleton height={280} />
        </div>
      ) : !summary ? (
        <div className="glass p-12 text-center">
          <FileText size={32} className="mx-auto mb-3" style={{ color: "var(--text-dim)" }} />
          <p className="text-sm" style={{ color: "var(--text-dim)" }}>
            No data is available for the selected period. Try a wider date range or upload transactions.
          </p>
        </div>
      ) : (
        <>
          {tab === "cashflow" && (
            <CashFlowTab
              data={summary}
              annotations={annotations}
              onAnnotate={handleAnnotate}
              onDrillDown={handleDrillDown}
              drillDown={drillDown}
            />
          )}

          {tab === "forecast" && (
            <ForecastTab
              forecast={forecast}
              scenario={scenario}
              onScenarioChange={setScenario}
              loading={forecastLoading}
              annotations={annotations}
              onAnnotate={handleAnnotate}
            />
          )}

          {tab === "variance" && (
            <VarianceTab summary={summary} annotations={annotations} onAnnotate={handleAnnotate} />
          )}

          {tab === "trends" && (
            <TrendsTab dashboard={dashboard} loading={loading} annotations={annotations} onAnnotate={handleAnnotate} />
          )}

          {tab === "categories" && (
            <CategoriesTab data={summary} annotations={annotations} onAnnotate={handleAnnotate} />
          )}

          {tab === "compare" && (
            <div className="space-y-4">
              <div className="glass p-3 flex flex-col md:flex-row md:items-center gap-3">
                <span className="text-xs font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--text-muted)" }}>
                  Compare Against
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {PRESETS.filter((presetOption) => presetOption.key !== preset).map((presetOption) => (
                    <button
                      key={presetOption.key}
                      onClick={() => setComparePreset(presetOption.key)}
                      className="px-3 py-1.5 text-xs rounded-lg font-medium transition-all"
                      style={{
                        background: comparePreset === presetOption.key ? "var(--info)" : "var(--surface-hover)",
                        color: comparePreset === presetOption.key ? "#fff" : "var(--text)",
                        border: `1px solid ${comparePreset === presetOption.key ? "var(--info)" : "var(--border)"}`,
                      }}
                    >
                      {presetOption.label}
                    </button>
                  ))}
                </div>
              </div>

              <CompareTab
                periodA={summary}
                periodB={compareData}
                labelA={PRESETS.find((presetOption) => presetOption.key === preset)?.label ?? "Current"}
                labelB={PRESETS.find((presetOption) => presetOption.key === comparePreset)?.label ?? "Compare"}
                loading={compareLoading}
                annotations={annotations}
                onAnnotate={handleAnnotate}
              />
            </div>
          )}
        </>
      )}

      {summary && (
        <div className="mt-6 text-xs text-center" style={{ color: "var(--text-dim)" }}>
          Report period: {summary.period_start} to {summary.period_end} | {summary.transaction_count} transactions | base currency {reportCurrency}
        </div>
      )}
    </div>
  );
}
