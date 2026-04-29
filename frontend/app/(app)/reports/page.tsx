"use client";

import { useState } from "react";
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
} from "lucide-react";

type ReportType =
  | "cash-flow"
  | "business-summary"
  | "investor-update"
  | "budget-actuals";

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
    description: "Monthly cash in/out with ending balance. Standard financial format.",
    icon: TrendingUp,
    tags: ["Standard", "Monthly"],
    sections: ["Cash Inflows by Category", "Cash Outflows by Category", "Net Cash Flow", "Ending Cash Balance"],
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

type ExportFormat = "pdf" | "csv" | "email";
type ExportStatus = "idle" | "loading" | "done" | "error";

export default function ReportsPage() {
  const [selected, setSelected] = useState<ReportType>("business-summary");
  const [period, setPeriod] = useState("2025-01");
  const [exportStatus, setExportStatus] = useState<ExportStatus>("idle");
  const [emailTarget, setEmailTarget] = useState("");
  const [showEmail, setShowEmail] = useState(false);

  const activeReport = REPORTS.find((r) => r.id === selected)!;

  const handleExport = async (format: ExportFormat) => {
    if (format === "email") {
      setShowEmail(true);
      return;
    }

    setExportStatus("loading");

    // Compute date range from selected month
    const startDate = `${period}-01`;
    const endMonth = new Date(startDate);
    endMonth.setMonth(endMonth.getMonth() + 1);
    const endDate = endMonth.toISOString().slice(0, 10);

    try {
      if (format === "pdf") {
        await reportsApi.exportPdf(startDate, endDate);
      } else {
        await reportsApi.exportCsv(startDate, endDate);
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
          {/* Period selector */}
          <div className="glass p-4 flex items-center gap-4">
            <label className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
              Period
            </label>
            <input
              type="month"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="flex-1"
              style={{ maxWidth: 200 }}
            />
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
                    Luna Bakery · {new Date(period + "-01").toLocaleDateString("en-US", { month: "long", year: "numeric" })}
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
              {activeReport.sections.map((section, i) => (
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
