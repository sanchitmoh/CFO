"use client";

import { useEffect, useState, useCallback } from "react";
import { anomalyApi } from "@/lib/api";
import type { Anomaly as ApiAnomaly, ScanResult } from "@/lib/types";
import {
  AlertTriangle,
  ShieldAlert,
  CheckCircle,
  RefreshCw,
  TrendingUp,
  Eye,
} from "lucide-react";

import { useCurrency } from "@/components/CurrencyContext";

const scoreColor = (score: number) => {
  if (score >= 3.0) return "var(--danger)";
  if (score >= 2.5) return "var(--warning)";
  return "var(--info)";
};

const scoreBg = (score: number) => {
  if (score >= 3.0) return "var(--danger-soft)";
  if (score >= 2.5) return "var(--warning-soft)";
  return "var(--info-soft)";
};

const scoreLabel = (score: number) => {
  if (score >= 3.0) return "High Risk";
  if (score >= 2.5) return "Medium Risk";
  return "Low Risk";
};

type StatusFilter = "all" | "flagged" | "reviewed" | "dismissed";
type UiAnomaly = ApiAnomaly & { status: StatusFilter };

const toUiAnomaly = (anomaly: ApiAnomaly): UiAnomaly => ({
  ...anomaly,
  status: "flagged",
});

export default function AnomaliesPage() {
  const { formatAmount: fmt } = useCurrency();
  const [anomalies, setAnomalies] = useState<UiAnomaly[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [scanSummary, setScanSummary] = useState<Pick<ScanResult, "scanned" | "anomalies_found"> | null>(null);

  const loadAnomalies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await anomalyApi.list();
      setAnomalies(Array.isArray(data) ? data.map(toUiAnomaly) : []);
    } catch {
      setAnomalies([]);
      setError("Unable to load anomalies. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  const runScan = useCallback(async () => {
    setScanning(true);
    setError(null);
    try {
      const result = await anomalyApi.scan(undefined, 365);
      setScanSummary({
        scanned: result.scanned,
        anomalies_found: result.anomalies_found,
      });
      setAnomalies(result.anomalies.map(toUiAnomaly));
    } catch {
      setError("Unable to complete the scan right now. Existing flagged anomalies are still shown below.");
      // scan failed — keep existing data
    } finally {
      setScanning(false);
    }
  }, []);

  useEffect(() => {
    loadAnomalies();
  }, [loadAnomalies]);

  const dismiss = (id: string) => {
    setAnomalies((prev) =>
      prev.map((a) => (a.id === id ? { ...a, status: "dismissed" } : a))
    );
  };

  const markReviewed = (id: string) => {
    setAnomalies((prev) =>
      prev.map((a) => (a.id === id ? { ...a, status: "reviewed" } : a))
    );
  };

  const filtered =
    filter === "all" ? anomalies : anomalies.filter((a) => a.status === filter);

  const counts = {
    flagged: anomalies.filter((a) => a.status === "flagged").length,
    reviewed: anomalies.filter((a) => a.status === "reviewed").length,
    dismissed: anomalies.filter((a) => a.status === "dismissed").length,
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {error && (
        <div className="glass p-4 flex flex-wrap items-center gap-3 animate-fade-up" style={{ borderColor: "var(--danger)44", background: "var(--danger-soft)" }}>
          <AlertTriangle size={18} style={{ color: "var(--danger)", flexShrink: 0 }} />
          <p className="text-sm" style={{ color: "var(--danger)" }}>{error}</p>
          <button onClick={loadAnomalies} className="text-xs font-medium px-3 py-1.5 rounded-lg sm:ml-auto" style={{ background: "var(--danger)", color: "#fff" }}>Retry</button>
        </div>
      )}
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between animate-fade-up">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>
            Anomaly Detection
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Statistical detection of unusual financial patterns — powered by adaptive Z-Score analysis
          </p>
        </div>
        <button
          onClick={runScan}
          disabled={scanning}
          className="btn-primary flex w-full items-center justify-center gap-2 sm:w-auto"
        >
          <RefreshCw size={15} className={scanning ? "animate-spin" : ""} />
          {scanning ? "Scanning…" : "Run Scan"}
        </button>
      </div>

      {scanSummary && (
        <div className="glass p-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between animate-fade-up delay-1">
          <div>
            <p className="text-sm font-medium" style={{ color: "var(--text)" }}>
              Latest scan summary
            </p>
            <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              Scanned {scanSummary.scanned} expense transactions and flagged {scanSummary.anomalies_found} anomalies.
            </p>
          </div>
          <span className="badge badge-info">365-day window</span>
        </div>
      )}

      {/* Stat Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 animate-fade-up delay-1">
        {[
          { label: "Flagged", count: counts.flagged, color: "var(--danger)", bg: "var(--danger-soft)", icon: ShieldAlert },
          { label: "Reviewed", count: counts.reviewed, color: "var(--warning)", bg: "var(--warning-soft)", icon: Eye },
          { label: "Dismissed", count: counts.dismissed, color: "var(--text-muted)", bg: "var(--surface)", icon: CheckCircle },
        ].map(({ label, count, color, bg, icon: Icon }) => (
          <div key={label} className="glass p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                {label}
              </span>
              <div className="flex items-center justify-center" style={{ width: 32, height: 32, borderRadius: 8, background: bg }}>
                <Icon size={16} style={{ color }} />
              </div>
            </div>
            <div className="text-3xl font-bold" style={{ color }}>{count}</div>
          </div>
        ))}
      </div>

      {/* Algorithm Info */}
      <div
        className="glass p-4 flex items-start gap-4 animate-fade-up delay-2"
        style={{ borderColor: "var(--info)22" }}
      >
        <TrendingUp size={20} style={{ color: "var(--info)", marginTop: 2, flexShrink: 0 }} />
        <div>
          <p className="text-sm font-medium" style={{ color: "var(--text)" }}>
            Adaptive Z-Score Analysis Active
          </p>
          <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
            Analyzing per-category spend variance with auto-calibrated thresholds based on your data volume.
            Transactions exceeding the calibrated threshold are flagged for review. Anomalies are suggestions — not automatic actions.
          </p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap gap-2 animate-fade-up delay-2">
        {(["all", "flagged", "reviewed", "dismissed"] as StatusFilter[]).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className="px-4 py-2 rounded-lg text-sm font-medium capitalize transition-all"
            style={{
              background: filter === f ? "var(--accent-soft)" : "var(--surface)",
              color: filter === f ? "var(--accent)" : "var(--text-muted)",
              border: `1px solid ${filter === f ? "var(--accent)44" : "var(--border)"}`,
            }}
          >
            {f === "all" ? `All (${anomalies.length})` : `${f.charAt(0).toUpperCase() + f.slice(1)} (${counts[f as keyof typeof counts]})`}
          </button>
        ))}
      </div>

      {/* Anomaly List */}
      <div className="space-y-3 animate-fade-up delay-3">
        {filtered.length === 0 && (
          <div className="glass p-12 text-center">
            <CheckCircle size={40} className="mx-auto mb-3" style={{ color: "var(--accent)" }} />
            <p className="text-sm font-medium" style={{ color: "var(--text)" }}>
              No anomalies in this filter
            </p>
          </div>
        )}

        {filtered.map((anomaly) => (
          <div
            key={anomaly.id}
            className="glass p-5 transition-all"
            style={{
              borderColor:
                anomaly.status === "flagged"
                  ? `${scoreColor(anomaly.anomaly_score)}22`
                  : "var(--border)",
              opacity: anomaly.status === "dismissed" ? 0.6 : 1,
            }}
          >
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              {/* Left */}
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-1">
                  <AlertTriangle
                    size={16}
                    style={{ color: scoreColor(anomaly.anomaly_score), flexShrink: 0 }}
                  />
                  <span className="font-semibold text-sm" style={{ color: "var(--text)" }}>
                    {anomaly.description}
                  </span>
                  <span
                    className="badge"
                    style={{
                      background: scoreBg(anomaly.anomaly_score),
                      color: scoreColor(anomaly.anomaly_score),
                    }}
                  >
                    {scoreLabel(anomaly.anomaly_score)}
                  </span>
                  {anomaly.status !== "flagged" && (
                    <span
                      className="badge"
                      style={{
                        background: "var(--surface-hover)",
                        color: "var(--text-muted)",
                      }}
                    >
                      {anomaly.status}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-4 text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                  <span>{new Date(anomaly.date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</span>
                  <span className="badge badge-info">{anomaly.category}</span>
                  <span className="font-semibold" style={{ color: "var(--danger)" }}>
                    {fmt(anomaly.amount)}
                  </span>
                </div>

                {/* Score bar */}
                <div className="flex items-center gap-2 mt-3">
                  <span className="text-xs" style={{ color: "var(--text-dim)", width: 90 }}>
                    Anomaly score
                  </span>
                  <div
                    style={{
                      flex: 1,
                      height: 6,
                      borderRadius: 3,
                      background: "var(--surface-hover)",
                      maxWidth: 200,
                    }}
                  >
                    <div
                      style={{
                        width: `${Math.min((anomaly.anomaly_score / 4) * 100, 100)}%`,
                        height: "100%",
                        borderRadius: 3,
                        background: scoreColor(anomaly.anomaly_score),
                        transition: "width 0.5s ease",
                      }}
                    />
                  </div>
                  <span className="text-xs font-bold" style={{ color: scoreColor(anomaly.anomaly_score) }}>
                    {anomaly.anomaly_score.toFixed(1)}σ
                  </span>
                </div>
              </div>

              {/* Actions */}
              {anomaly.status === "flagged" && (
                <div className="flex flex-col gap-2 shrink-0">
                  <button
                    onClick={() => markReviewed(anomaly.id)}
                    className="btn-ghost text-xs px-3 py-1.5 flex items-center gap-1"
                    style={{ color: "var(--warning)" }}
                  >
                    <Eye size={13} /> Mark Reviewed
                  </button>
                  <button
                    onClick={() => dismiss(anomaly.id)}
                    className="btn-ghost text-xs px-3 py-1.5"
                  >
                    Hide in View
                  </button>
                </div>
              )}
            </div>

            {/* Explanation (expandable) */}
            <button
              className="text-xs mt-3 flex items-center gap-1 transition-colors"
              style={{ color: "var(--accent)" }}
              onClick={() =>
                setExpanded(expanded === anomaly.id ? null : anomaly.id)
              }
            >
              {expanded === anomaly.id ? "▲" : "▼"} Why was this flagged?
            </button>

            {expanded === anomaly.id && (
              <div
                className="mt-3 p-3 rounded-lg text-sm"
                style={{
                  background: "var(--bg)",
                  border: "1px solid var(--border)",
                  color: "var(--text-muted)",
                }}
              >
                {anomaly.reason}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Disclaimer */}
      <p className="text-xs text-center animate-fade-up delay-5" style={{ color: "var(--text-dim)" }}>
        Anomaly detection is advisory only. All flagged items require human review before action. Review and hide actions on this page are local to the current browser view.
        The ML model evaluates patterns — it does not make financial decisions.
      </p>
    </div>
  );
}
