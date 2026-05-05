"use client";

import { useState, useEffect } from "react";
import { reportsApi } from "@/lib/api";
import {
  FileText,
  Download,
  Mail,
  AlertCircle,
  TrendingUp,
  DollarSign,
  BarChart2,
  FileBarChart,
  CheckCircle,
  Calendar,
  ArrowUpCircle,
  ArrowDownCircle,
} from "lucide-react";

type ReportType =
  | "cash-flow"
  | "business-summary"
  | "investor-update"
  | "budget-actuals";

type DateRangePreset = "this-month" | "last-month" | "last-3-months" | "last-6-months" | "last-12-months" | "ytd" | "custom";

interface Report {
  id: ReportType;
  title: string;
  description: string;
  icon: React.ElementType;
  tags: string[];
  sections: string[];
}

const REPORTS: Report[] = [
  {
    id: "cash-flow",
    title: "Cash Flow Statement",
    description: "Industry-standard cash flow with operating, investing, and financing activities.",
    icon: TrendingUp,
    tags: ["Standard", "GAAP"],
    sections: [
      "Operating Activities",
      "Cash Inflows by Category",
      "Cash Outflows by Category",
      "Net Operating Cash Flow",
      "Investing Activities",
      "Financing Activities",
      "Net Change in Cash",
      "Beginning Cash Balance",
      "Ending Cash Balance",
      "Cash Flow Analysis",
    ],
  },
  {
    id: "business-summary",
    title: "1-Page Business Summary",
    description: "Key metrics snapshot for quick internal reviews — revenue, burn, runway, top expenses.",
    icon: BarChart2,
    tags: ["Executive", "1-Page"],
    sections: ["Revenue & MRR", "Burn Rate", "Cash Runway", "Top Expenses", "Month-over-Month Trend"],
  },
  {
    id: "investor-update",
    title: "Investor Update",
    description: "Pre-formatted for seed/Series A updates. Revenue, burns, runway, highlights, challenges.",
    icon: FileBarChart,
    tags: ["Investor", "Formal"],
    sections: ["Key Metrics", "Monthly Revenue", "Burn Rate & Runway", "Highlights", "Challenges", "Ask / Next Steps"],
  },
  {
    id: "budget-actuals",
    title: "Budget vs. Actuals",
    description: "Compare planned vs. real spending per category for the selected period.",
    icon: DollarSign,
    tags: ["Budget", "Detailed"],
    sections: ["Budget Allocated by Category", "Actual Spend", "Variance ($)", "Variance (%)", "Status"],
  },
];

const DATE_PRESETS: { value: DateRangePreset; label: string }[] = [
  { value: "this-month", label: "This Month" },
  { value: "last-month", label: "Last Month" },
  { value: "last-3-months", label: "Last 3 Months" },
  { value: "last-6-months", label: "Last 6 Months" },
  { value: "last-12-months", label: "Last 12 Months" },
  { value: "ytd", label: "Year to Date" },
  { value: "custom", label: "Custom Range" },
];

type ExportFormat = "pdf" | "csv" | "email";
type ExportStatus = "idle" | "loading" | "done" | "error";

function getDateRange(preset: DateRangePreset, customStart?: string, customEnd?: string): { start: string; end: string } {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth();

  switch (preset) {
    case "this-month":
      return {
        start: new Date(year, month, 1).toISOString().slice(0, 10),
        end: today.toISOString().slice(0, 10),
      };
    case "last-month": {
      const lastMonth = new Date(year, month - 1, 1);
      const lastMonthEnd = new Date(year, month, 0);
      return {
        start: lastMonth.toISOString().slice(0, 10),
        end: lastMonthEnd.toISOString().slice(0, 10),
      };
    }
    case "last-3-months":
      return {
        start: new Date(year, month - 3, 1).toISOString().slice(0, 10),
        end: today.toISOString().slice(0, 10),
      };
    case "last-6-months":
      return {
        start: new Date(year, month - 6, 1).toISOString().slice(0, 10),
        end: today.toISOString().slice(0, 10),
      };
    case "last-12-months":
      return {
        start: new Date(year, month - 12, 1).toISOString().slice(0, 10),
        end: today.toISOString().slice(0, 10),
      };
    case "ytd":
      return {
        start: new Date(year, 0, 1).toISOString().slice(0, 10),
        end: today.toISOString().slice(0, 10),
      };
    case "custom":
      return {
        start: customStart || new Date(year, month - 1, 1).toISOString().slice(0, 10),
        end: customEnd || today.toISOString().slice(0, 10),
      };
    default:
      return {
        start: new Date(year, month, 1).toISOString().slice(0, 10),
        end: today.toISOString().slice(0, 10),
      };
  }
}

export default function ReportsPage() {
  const [selected, setSelected] = useState<ReportType>("cash-flow");
  const [datePreset, setDatePreset] = useState<DateRangePreset>("last-month");
  const [customStartDate, setCustomStartDate] = useState("");
  const [customEndDate, setCustomEndDate] = useState("");
  const [exportStatus, setExportStatus] = useState<ExportStatus>("idle");
  const [emailTarget, setEmailTarget] = useState("");
  const [showEmail, setShowEmail] = useState(false);

  const activeReport = REPORTS.find((r) => r.id === selected)!;
  const dateRange = getDateRange(datePreset, customStartDate, customEndDate);

  // Initialize custom dates when switching to custom preset
  useEffect(() => {
    if (datePreset === "custom" && !customStartDate) {
      const today = new Date();
      const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      setCustomStartDate(lastMonth.toISOString().slice(0, 10));
      setCustomEndDate(today.toISOString().slice(0, 10));
    }
  }, [datePreset, customStartDate]);

  const handleExport = async (format: ExportFormat) => {
    if (format === "email") {
      setShowEmail(true);
      return;
    }

    setExportStatus("loading");

    try {
      if (format === "pdf") {
        await reportsApi.exportPdf(dateRange.start, dateRange.end);
      } else {
        await reportsApi.exportCsv(dateRange.start, dateRange.end);
      }
      setExportStatus("done");
      setTimeout(() => setExportStatus("idle"), 3000);
    } catch (err) {
      console.error("Export failed:", err);
      setExportStatus("error");
      setTimeout(() => setExportStatus("idle"), 3000);
    }
  };

  const handleEmailSend = () => {
    if (!emailTarget) return;
    setShowEmail(false);
    setExportStatus("loading");
    setTimeout(() => {
      setExportStatus("done");
      setTimeout(() => setExportStatus("idle"), 3000);
    }, 1500);
  };

  const formatDateRange = () => {
    const start = new Date(dateRange.start);
    const end = new Date(dateRange.end);
    const options: Intl.DateTimeFormatOptions = { month: "short", day: "numeric", year: "numeric" };
    return `${start.toLocaleDateString("en-US", options)} - ${end.toLocaleDateString("en-US", options)}`;
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="animate-fade-up">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>
          Reporting & Exports
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          Generate investor-friendly financial reports and export in multiple formats
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Report Selector */}
        <div className="space-y-3 animate-fade-up delay-1">
          <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
            Report Templates
          </h2>
          {REPORTS.map((report) => {
            const Icon = report.icon;
            const isActive = selected === report.id;
            return (
              <button
                key={report.id}
                onClick={() => setSelected(report.id)}
                className="w-full text-left p-4 rounded-xl transition-all"
                style={{
                  background: isActive ? "var(--accent-soft)" : "var(--surface)",
                  border: `1px solid ${isActive ? "var(--accent)44" : "var(--border)"}`,
                }}
              >
                <div className="flex items-center gap-3 mb-1">
                  <Icon size={16} style={{ color: isActive ? "var(--accent)" : "var(--text-muted)" }} />
                  <span
                    className="text-sm font-semibold"
                    style={{ color: isActive ? "var(--accent)" : "var(--text)" }}
                  >
                    {report.title}
                  </span>
                </div>
                <p className="text-xs pl-7" style={{ color: "var(--text-dim)" }}>
                  {report.description}
                </p>
                <div className="flex gap-1.5 pl-7 mt-2">
                  {report.tags.map((tag) => (
                    <span
                      key={tag}
                      className="badge"
                      style={{
                        background: isActive ? "var(--accent-soft)" : "var(--surface-hover)",
                        color: isActive ? "var(--accent)" : "var(--text-dim)",
                      }}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </button>
            );
          })}
        </div>

        {/* Preview + Export */}
        <div className="lg:col-span-2 space-y-4 animate-fade-up delay-2">
          {/* Date Range Selector */}
          <div className="glass p-4 space-y-4">
            <div className="flex items-center gap-2 mb-3">
              <Calendar size={16} style={{ color: "var(--accent)" }} />
              <label className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                Report Period
              </label>
            </div>
            
            {/* Preset buttons */}
            <div className="flex flex-wrap gap-2">
              {DATE_PRESETS.map((preset) => (
                <button
                  key={preset.value}
                  onClick={() => setDatePreset(preset.value)}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg transition-all"
                  style={{
                    background: datePreset === preset.value ? "var(--accent)" : "var(--surface-hover)",
                    color: datePreset === preset.value ? "var(--bg)" : "var(--text)",
                    border: `1px solid ${datePreset === preset.value ? "var(--accent)" : "var(--border)"}`,
                  }}
                >
                  {preset.label}
                </button>
              ))}
            </div>

            {/* Custom date inputs */}
            {datePreset === "custom" && (
              <div className="flex gap-3 items-center pt-2">
                <div className="flex-1">
                  <label className="text-xs" style={{ color: "var(--text-muted)" }}>Start Date</label>
                  <input
                    type="date"
                    value={customStartDate}
                    onChange={(e) => setCustomStartDate(e.target.value)}
                    className="w-full mt-1"
                  />
                </div>
                <div className="flex-1">
                  <label className="text-xs" style={{ color: "var(--text-muted)" }}>End Date</label>
                  <input
                    type="date"
                    value={customEndDate}
                    onChange={(e) => setCustomEndDate(e.target.value)}
                    className="w-full mt-1"
                  />
                </div>
              </div>
            )}

            {/* Selected range display */}
            <div
              className="p-3 rounded-lg flex items-center justify-between"
              style={{ background: "var(--accent-soft)", border: "1px solid var(--accent)22" }}
            >
              <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
                Selected Range:
              </span>
              <span className="text-sm font-semibold" style={{ color: "var(--accent)" }}>
                {formatDateRange()}
              </span>
            </div>
          </div>

          {/* Report Preview */}
          <div className="glass p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                {(() => {
                  const Icon = activeReport.icon;
                  return (
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
                      <Icon size={18} style={{ color: "var(--accent)" }} />
                    </div>
                  );
                })()}
                <div>
                  <h2 className="font-bold text-sm" style={{ color: "var(--text)" }}>
                    {activeReport.title}
                  </h2>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {formatDateRange()}
                  </p>
                </div>
              </div>
              <span
                className="badge badge-info text-xs"
                style={{ color: "var(--accent)", background: "var(--accent-soft)" }}
              >
                Preview
              </span>
            </div>

            {/* Sections preview */}
            <div className="space-y-2 mb-6">
              <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--text-muted)" }}>
                Report Sections
              </p>
              
              {/* Enhanced Cash Flow Preview */}
              {selected === "cash-flow" && (
                <div className="space-y-3 mb-4">
                  {/* Operating Activities */}
                  <div
                    className="p-4 rounded-lg"
                    style={{ background: "var(--bg)", border: "1px solid var(--border)" }}
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <ArrowUpCircle size={16} style={{ color: "var(--success)" }} />
                      <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                        Operating Activities
                      </span>
                    </div>
                    <div className="space-y-2 pl-6">
                      <div className="flex justify-between text-xs">
                        <span style={{ color: "var(--text-muted)" }}>Cash Inflows (Revenue, Sales)</span>
                        <span className="font-mono" style={{ color: "var(--success)" }}>+$XX,XXX</span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span style={{ color: "var(--text-muted)" }}>Cash Outflows (Operating Expenses)</span>
                        <span className="font-mono" style={{ color: "var(--danger)" }}>-$XX,XXX</span>
                      </div>
                      <div className="flex justify-between text-xs font-semibold pt-2 border-t" style={{ borderColor: "var(--border)" }}>
                        <span style={{ color: "var(--text)" }}>Net Operating Cash Flow</span>
                        <span className="font-mono" style={{ color: "var(--text)" }}>$XX,XXX</span>
                      </div>
                    </div>
                  </div>

                  {/* Investing Activities */}
                  <div
                    className="p-4 rounded-lg"
                    style={{ background: "var(--bg)", border: "1px solid var(--border)" }}
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <TrendingUp size={16} style={{ color: "var(--info)" }} />
                      <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                        Investing Activities
                      </span>
                    </div>
                    <div className="space-y-2 pl-6">
                      <div className="flex justify-between text-xs">
                        <span style={{ color: "var(--text-muted)" }}>Capital Expenditures, Investments</span>
                        <span className="font-mono" style={{ color: "var(--text-dim)" }}>$XX,XXX</span>
                      </div>
                    </div>
                  </div>

                  {/* Financing Activities */}
                  <div
                    className="p-4 rounded-lg"
                    style={{ background: "var(--bg)", border: "1px solid var(--border)" }}
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <DollarSign size={16} style={{ color: "var(--warning)" }} />
                      <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                        Financing Activities
                      </span>
                    </div>
                    <div className="space-y-2 pl-6">
                      <div className="flex justify-between text-xs">
                        <span style={{ color: "var(--text-muted)" }}>Loans, Equity Funding</span>
                        <span className="font-mono" style={{ color: "var(--text-dim)" }}>$XX,XXX</span>
                      </div>
                    </div>
                  </div>

                  {/* Summary */}
                  <div
                    className="p-4 rounded-lg"
                    style={{ background: "var(--accent-soft)", border: "1px solid var(--accent)44" }}
                  >
                    <div className="space-y-2">
                      <div className="flex justify-between text-xs">
                        <span style={{ color: "var(--text-muted)" }}>Beginning Cash Balance</span>
                        <span className="font-mono" style={{ color: "var(--text)" }}>$XX,XXX</span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span style={{ color: "var(--text-muted)" }}>Net Change in Cash</span>
                        <span className="font-mono" style={{ color: "var(--text)" }}>$XX,XXX</span>
                      </div>
                      <div className="flex justify-between text-sm font-bold pt-2 border-t" style={{ borderColor: "var(--accent)44" }}>
                        <span style={{ color: "var(--accent)" }}>Ending Cash Balance</span>
                        <span className="font-mono" style={{ color: "var(--accent)" }}>$XX,XXX</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Standard sections list for other reports */}
              {selected !== "cash-flow" && activeReport.sections.map((section, i) => (
                <div
                  key={section}
                  className="flex items-center gap-3 py-2.5 px-3 rounded-lg"
                  style={{
                    background: "var(--bg)",
                    border: "1px solid var(--border)",
                    animationDelay: `${i * 0.05}s`,
                  }}
                >
                  <div
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: "50%",
                      background: "var(--accent)",
                      flexShrink: 0,
                    }}
                  />
                  <span className="text-sm" style={{ color: "var(--text)" }}>
                    {section}
                  </span>
                </div>
              ))}
            </div>

            {/* Disclaimer */}
            <div
              className="p-3 rounded-lg flex items-start gap-2 mb-5"
              style={{
                background: "var(--warning-soft)",
                border: "1px solid var(--warning)22",
              }}
            >
              <AlertCircle size={14} style={{ color: "var(--warning)", marginTop: 2, flexShrink: 0 }} />
              <p className="text-xs" style={{ color: "var(--warning)" }}>
                This report is generated for internal planning purposes. Consult a qualified accountant for official financial statements.
              </p>
            </div>

            {/* Export buttons */}
            {exportStatus === "done" ? (
              <div
                className="flex items-center gap-2 p-4 rounded-lg"
                style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
              >
                <CheckCircle size={16} />
                <span className="text-sm font-medium">Report ready! Download started.</span>
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-3">
                {[
                  { format: "pdf" as ExportFormat, label: "Export PDF", icon: FileText, primary: true },
                  { format: "csv" as ExportFormat, label: "Export CSV", icon: Download, primary: false },
                  { format: "email" as ExportFormat, label: "Send Email", icon: Mail, primary: false },
                ].map(({ format, label, icon: Icon, primary }) => (
                  <button
                    key={format}
                    onClick={() => handleExport(format)}
                    disabled={exportStatus === "loading"}
                    className={primary ? "btn-primary flex items-center justify-center gap-2" : "btn-ghost flex items-center justify-center gap-2"}
                  >
                    {exportStatus === "loading" && primary ? (
                      <div
                        className="animate-spin"
                        style={{
                          width: 14,
                          height: 14,
                          border: "2px solid var(--bg)",
                          borderTopColor: "transparent",
                          borderRadius: "50%",
                        }}
                      />
                    ) : (
                      <Icon size={14} />
                    )}
                    {exportStatus === "loading" && primary ? "Generating…" : label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Email modal (inline) */}
          {showEmail && (
            <div
              className="glass p-5"
              style={{ borderColor: "var(--info)22" }}
            >
              <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text)" }}>
                Send Report via Email
              </h3>
              <div className="flex gap-3">
                <input
                  type="email"
                  placeholder="recipient@company.com"
                  value={emailTarget}
                  onChange={(e) => setEmailTarget(e.target.value)}
                  className="flex-1"
                />
                <button onClick={handleEmailSend} className="btn-primary">
                  Send
                </button>
                <button onClick={() => setShowEmail(false)} className="btn-ghost">
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
