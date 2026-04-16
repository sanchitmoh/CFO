"use client";

import { useState, useRef } from "react";
import { api } from "@/lib/api";
import {
  Upload,
  CheckCircle,
  AlertCircle,
  Database,
  Link2,
  Bell,
  MessageSquare,
  Mail,
  FileSpreadsheet,
  Zap,
  Clock,
} from "lucide-react";

type UploadStatus = "idle" | "loading" | "success" | "error";

interface AlertSettings {
  emailEnabled: boolean;
  emailAddress: string;
  slackEnabled: boolean;
  slackWebhook: string;
  lowCashThreshold: number;
  overspendPercent: number;
  revenueDrop: number;
}

export default function SettingsPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
  const [imported, setImported] = useState<number | null>(null);
  const [uploadError, setUploadError] = useState("");

  const [alertSettings, setAlertSettings] = useState<AlertSettings>({
    emailEnabled: true,
    emailAddress: "",
    slackEnabled: false,
    slackWebhook: "",
    lowCashThreshold: 10000,
    overspendPercent: 20,
    revenueDrop: 15,
  });
  const [saved, setSaved] = useState(false);

  const handleFile = async (file: File) => {
    if (!file.name.endsWith(".csv")) {
      setUploadStatus("error");
      setUploadError("Only CSV files are supported.");
      return;
    }
    setUploadStatus("loading");
    setUploadError("");
    try {
      const result = await api.uploadCSV(file);
      setImported(result.imported);
      setUploadStatus("success");
    } catch (err: unknown) {
      setUploadStatus("error");
      setUploadError(err instanceof Error ? err.message : "Upload failed.");
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const saveAlerts = () => {
    // In production: POST /api/settings/alerts
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="animate-fade-up">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>
          Settings & Integrations
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          Connect data sources and configure notification preferences
        </p>
      </div>

      {/* ── CSV Upload ── */}
      <section className="glass p-6 animate-fade-up delay-1">
        <div className="flex items-center gap-3 mb-5">
          <div
            className="flex items-center justify-center"
            style={{ width: 36, height: 36, borderRadius: 10, background: "var(--accent-soft)" }}
          >
            <FileSpreadsheet size={18} style={{ color: "var(--accent)" }} />
          </div>
          <div>
            <h2 className="font-semibold text-sm" style={{ color: "var(--text)" }}>
              CSV Upload
            </h2>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Import transactions from your bank or QuickBooks export
            </p>
          </div>
        </div>

        {/* Drop zone */}
        <div
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          className="cursor-pointer rounded-xl flex flex-col items-center justify-center gap-3 transition-all"
          style={{
            border: `2px dashed ${dragOver ? "var(--accent)" : "var(--border)"}`,
            background: dragOver ? "var(--accent-soft)" : "var(--bg)",
            padding: "40px 24px",
          }}
        >
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 12,
              background: dragOver ? "var(--accent)" : "var(--surface)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Upload size={22} style={{ color: dragOver ? "var(--bg)" : "var(--accent)" }} />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium" style={{ color: "var(--text)" }}>
              Drop your CSV here or click to browse
            </p>
            <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              Supports bank statements, QuickBooks exports, and custom CSVs
            </p>
          </div>
        </div>

        <input
          ref={fileRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={onFileChange}
        />

        {/* Status */}
        {uploadStatus === "loading" && (
          <div className="mt-4 flex items-center gap-2" style={{ color: "var(--accent)" }}>
            <div className="animate-spin" style={{ width: 16, height: 16, border: "2px solid var(--accent)", borderTopColor: "transparent", borderRadius: "50%" }} />
            <span className="text-sm">Parsing and importing transactions…</span>
          </div>
        )}
        {uploadStatus === "success" && imported !== null && (
          <div className="mt-4 flex items-center gap-2 p-3 rounded-lg" style={{ background: "var(--accent-soft)", color: "var(--accent)" }}>
            <CheckCircle size={16} />
            <span className="text-sm font-medium">
              Successfully imported {imported} transaction{imported !== 1 ? "s" : ""}!
            </span>
          </div>
        )}
        {uploadStatus === "error" && (
          <div className="mt-4 flex items-center gap-2 p-3 rounded-lg" style={{ background: "var(--danger-soft)", color: "var(--danger)" }}>
            <AlertCircle size={16} />
            <span className="text-sm">{uploadError}</span>
          </div>
        )}

        {/* CSV format hint */}
        <div className="mt-4 p-3 rounded-lg text-xs" style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text-muted)" }}>
          <strong style={{ color: "var(--text)" }}>Expected columns:</strong>{" "}
          <code style={{ color: "var(--accent)" }}>date, description, amount, type (income/expense), category</code>
          <br />
          QuickBooks exports are auto-detected and column-mapped automatically.
        </div>
      </section>

      {/* ── Integration Tiers ── */}
      <section className="glass p-6 animate-fade-up delay-2">
        <div className="flex items-center gap-3 mb-5">
          <div
            className="flex items-center justify-center"
            style={{ width: 36, height: 36, borderRadius: 10, background: "var(--info-soft)" }}
          >
            <Link2 size={18} style={{ color: "var(--info)" }} />
          </div>
          <div>
            <h2 className="font-semibold text-sm" style={{ color: "var(--text)" }}>
              Connected Integrations
            </h2>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Live bank and accounting integrations (Phase 2)
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { name: "Plaid (Bank Connections)", phase: "Phase 2", icon: Database, status: "coming" },
            { name: "QuickBooks API", phase: "Phase 2", icon: Zap, status: "coming" },
            { name: "Xero API", phase: "Phase 2", icon: Zap, status: "coming" },
            { name: "Stripe Revenue", phase: "Phase 3", icon: Zap, status: "future" },
          ].map(({ name, phase, icon: Icon, status }) => (
            <div
              key={name}
              className="flex items-center justify-between p-4 rounded-lg"
              style={{ background: "var(--bg)", border: "1px solid var(--border)" }}
            >
              <div className="flex items-center gap-3">
                <Icon size={16} style={{ color: "var(--text-dim)" }} />
                <div>
                  <p className="text-sm font-medium" style={{ color: "var(--text)" }}>{name}</p>
                  <p className="text-xs" style={{ color: "var(--text-dim)" }}>{phase}</p>
                </div>
              </div>
              <span
                className="badge"
                style={{
                  background: status === "coming" ? "var(--warning-soft)" : "var(--surface)",
                  color: status === "coming" ? "var(--warning)" : "var(--text-dim)",
                }}
              >
                {status === "coming" ? "Coming Soon" : "Future"}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* ── Alert Settings ── */}
      <section className="glass p-6 animate-fade-up delay-3">
        <div className="flex items-center gap-3 mb-5">
          <div
            className="flex items-center justify-center"
            style={{ width: 36, height: 36, borderRadius: 10, background: "var(--warning-soft)" }}
          >
            <Bell size={18} style={{ color: "var(--warning)" }} />
          </div>
          <div>
            <h2 className="font-semibold text-sm" style={{ color: "var(--text)" }}>
              Alert Thresholds
            </h2>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Configure when the system notifies you
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div>
            <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
              Low Cash Threshold ($)
            </label>
            <input
              type="number"
              value={alertSettings.lowCashThreshold}
              onChange={(e) => setAlertSettings((s) => ({ ...s, lowCashThreshold: Number(e.target.value) }))}
              className="w-full"
              min={0}
            />
          </div>
          <div>
            <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
              Overspend Alert (%)
            </label>
            <input
              type="number"
              value={alertSettings.overspendPercent}
              onChange={(e) => setAlertSettings((s) => ({ ...s, overspendPercent: Number(e.target.value) }))}
              className="w-full"
              min={0}
            />
          </div>
          <div>
            <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
              Revenue Drop Alert (%)
            </label>
            <input
              type="number"
              value={alertSettings.revenueDrop}
              onChange={(e) => setAlertSettings((s) => ({ ...s, revenueDrop: Number(e.target.value) }))}
              className="w-full"
              min={0}
            />
          </div>
        </div>

        {/* Notification Channels */}
        <h3 className="text-xs font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>
          Notification Channels
        </h3>
        <div className="space-y-4">
          {/* Email */}
          <div
            className="p-4 rounded-lg"
            style={{ background: "var(--bg)", border: "1px solid var(--border)" }}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Mail size={16} style={{ color: "var(--info)" }} />
                <span className="text-sm font-medium" style={{ color: "var(--text)" }}>Email Alerts</span>
              </div>
              <button
                onClick={() => setAlertSettings((s) => ({ ...s, emailEnabled: !s.emailEnabled }))}
                className="relative rounded-full transition-all"
                style={{
                  width: 40,
                  height: 22,
                  background: alertSettings.emailEnabled ? "var(--accent)" : "var(--border)",
                }}
              >
                <span
                  className="absolute top-1 transition-all rounded-full"
                  style={{
                    width: 14,
                    height: 14,
                    background: "white",
                    left: alertSettings.emailEnabled ? 22 : 4,
                  }}
                />
              </button>
            </div>
            {alertSettings.emailEnabled && (
              <input
                type="email"
                placeholder="your@email.com"
                value={alertSettings.emailAddress}
                onChange={(e) => setAlertSettings((s) => ({ ...s, emailAddress: e.target.value }))}
                className="w-full"
              />
            )}
          </div>

          {/* Slack */}
          <div
            className="p-4 rounded-lg"
            style={{ background: "var(--bg)", border: "1px solid var(--border)" }}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <MessageSquare size={16} style={{ color: "#4A154B" }} />
                <span className="text-sm font-medium" style={{ color: "var(--text)" }}>Slack Alerts</span>
                <span className="badge badge-info">Webhook</span>
              </div>
              <button
                onClick={() => setAlertSettings((s) => ({ ...s, slackEnabled: !s.slackEnabled }))}
                className="relative rounded-full transition-all"
                style={{
                  width: 40,
                  height: 22,
                  background: alertSettings.slackEnabled ? "var(--accent)" : "var(--border)",
                }}
              >
                <span
                  className="absolute top-1 transition-all rounded-full"
                  style={{
                    width: 14,
                    height: 14,
                    background: "white",
                    left: alertSettings.slackEnabled ? 22 : 4,
                  }}
                />
              </button>
            </div>
            {alertSettings.slackEnabled && (
              <input
                type="url"
                placeholder="https://hooks.slack.com/services/..."
                value={alertSettings.slackWebhook}
                onChange={(e) => setAlertSettings((s) => ({ ...s, slackWebhook: e.target.value }))}
                className="w-full"
              />
            )}
          </div>
        </div>

        <button
          onClick={saveAlerts}
          className="btn-primary mt-5 flex items-center gap-2"
        >
          {saved ? <CheckCircle size={15} /> : <Clock size={15} />}
          {saved ? "Saved!" : "Save Settings"}
        </button>
      </section>

      <p className="text-xs text-center animate-fade-up delay-5" style={{ color: "var(--text-dim)" }}>
        CSV import is the recommended approach for demos and early use. Live API integrations are coming in Phase 2.
      </p>
    </div>
  );
}
