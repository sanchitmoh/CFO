"use client";

import { useEffect, useRef, useState } from "react";
import { api, settingsApi } from "@/lib/api";
import { useCurrency } from "@/components/CurrencyContext";
import {
  Activity,
  AlertCircle,
  Bell,
  Briefcase,
  CheckCircle2,
  Clock3,
  Database,
  FileSpreadsheet,
  Link2,
  Mail,
  MessageSquare,
  Save,
  Send,
  Upload,
  Zap,
} from "lucide-react";

type UploadStatus = "idle" | "loading" | "success" | "error";
type RequestState = "idle" | "loading" | "success" | "error";
type TestChannel = "email" | "slack";

interface AlertSettingsResponse {
  low_cash_threshold: number;
  high_expense_threshold: number;
  anomaly_sensitivity: number;
  email_enabled: boolean;
  email_addresses: string[];
  slack_enabled: boolean;
  slack_webhook_url: string | null;
}

interface AlertSettingsForm {
  emailEnabled: boolean;
  emailAddressInput: string;
  slackEnabled: boolean;
  slackWebhook: string;
  lowCashThreshold: number;
  largeExpenseThreshold: number;
  anomalySensitivity: number;
}

interface ChannelStatus {
  state: RequestState;
  message: string;
}

const SUPPORTED_CURRENCIES = [
  { code: "USD", name: "US Dollar (USD)" },
  { code: "EUR", name: "Euro (EUR)" },
  { code: "GBP", name: "British Pound (GBP)" },
  { code: "INR", name: "Indian Rupee (INR)" },
  { code: "CAD", name: "Canadian Dollar (CAD)" },
  { code: "AUD", name: "Australian Dollar (AUD)" },
  { code: "JPY", name: "Japanese Yen (JPY)" },
];

const DEFAULT_ALERT_SETTINGS: AlertSettingsForm = {
  emailEnabled: false,
  emailAddressInput: "",
  slackEnabled: false,
  slackWebhook: "",
  lowCashThreshold: 5000,
  largeExpenseThreshold: 10000,
  anomalySensitivity: 2.5,
};

function mapAlertSettings(data: AlertSettingsResponse): AlertSettingsForm {
  return {
    emailEnabled: data.email_enabled,
    emailAddressInput: (data.email_addresses ?? []).join(", "),
    slackEnabled: data.slack_enabled,
    slackWebhook: data.slack_webhook_url ?? "",
    lowCashThreshold: data.low_cash_threshold,
    largeExpenseThreshold: data.high_expense_threshold,
    anomalySensitivity: data.anomaly_sensitivity,
  };
}

function parseEmailRecipients(value: string): string[] {
  return value
    .split(",")
    .map((email) => email.trim())
    .filter(Boolean);
}

function looksLikeSlackWebhook(value: string): boolean {
  const trimmed = value.trim();
  return trimmed.startsWith("https://hooks.slack.com/services/");
}

function formatTriggerSummary(settings: AlertSettingsForm, currencyCode: string): string {
  return `${currencyCode} ${Math.round(settings.lowCashThreshold).toLocaleString()} cash floor | ${currencyCode} ${Math.round(settings.largeExpenseThreshold).toLocaleString()} large expense | ${settings.anomalySensitivity.toFixed(1)}x anomaly`;
}

function Toggle({
  checked,
  onChange,
  disabled = false,
}: {
  checked: boolean;
  onChange: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      aria-pressed={checked}
      disabled={disabled}
      onClick={onChange}
      className="relative rounded-full transition-all"
      style={{
        width: 46,
        height: 26,
        background: checked ? "var(--accent)" : "rgba(255,255,255,0.12)",
        border: `1px solid ${checked ? "rgba(201,169,98,0.55)" : "var(--border)"}`,
        opacity: disabled ? 0.6 : 1,
      }}
    >
      <span
        className="absolute top-[3px] transition-all rounded-full"
        style={{
          width: 18,
          height: 18,
          left: checked ? 24 : 4,
          background: checked ? "#0b0b0b" : "#ffffff",
        }}
      />
    </button>
  );
}

export default function SettingsPage() {
  const { currencyCode, setCurrencyCode, isLoading } = useCurrency();
  const fileRef = useRef<HTMLInputElement>(null);

  const [dragOver, setDragOver] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
  const [imported, setImported] = useState<number | null>(null);
  const [uploadError, setUploadError] = useState("");

  const [loadingSettings, setLoadingSettings] = useState(true);
  const [alertSettings, setAlertSettings] = useState<AlertSettingsForm>(DEFAULT_ALERT_SETTINGS);
  const [saveState, setSaveState] = useState<RequestState>("idle");
  const [saveMessage, setSaveMessage] = useState("");
  const [workspaceState, setWorkspaceState] = useState<RequestState>("idle");
  const [workspaceMessage, setWorkspaceMessage] = useState("");
  const [channelStatus, setChannelStatus] = useState<Record<TestChannel, ChannelStatus>>({
    email: { state: "idle", message: "" },
    slack: { state: "idle", message: "" },
  });

  const emailRecipients = parseEmailRecipients(alertSettings.emailAddressInput);
  const slackReady = alertSettings.slackEnabled && looksLikeSlackWebhook(alertSettings.slackWebhook);
  const emailReady = alertSettings.emailEnabled && emailRecipients.length > 0;
  const readyChannelCount = Number(emailReady) + Number(slackReady);

  const validationErrors: string[] = [];
  if (alertSettings.lowCashThreshold < 0) {
    validationErrors.push("Low cash threshold cannot be negative.");
  }
  if (alertSettings.largeExpenseThreshold < 0) {
    validationErrors.push("Large expense threshold cannot be negative.");
  }
  if (alertSettings.anomalySensitivity < 1) {
    validationErrors.push("Anomaly sensitivity should be at least 1.0x.");
  }
  if (alertSettings.emailEnabled && emailRecipients.length === 0) {
    validationErrors.push("Add at least one email recipient when email alerts are enabled.");
  }
  if (alertSettings.slackEnabled && !looksLikeSlackWebhook(alertSettings.slackWebhook)) {
    validationErrors.push("Slack alerts need a valid Incoming Webhook URL.");
  }

  useEffect(() => {
    let mounted = true;

    settingsApi.getAlertSettings()
      .then((data) => {
        if (!mounted) return;
        setAlertSettings(mapAlertSettings(data));
      })
      .catch(() => {
        if (!mounted) return;
        setSaveMessage("Using default alert settings until the backend returns saved preferences.");
      })
      .finally(() => {
        if (mounted) {
          setLoadingSettings(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  const handleFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".csv")) {
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
    } catch (error: unknown) {
      setUploadStatus("error");
      setUploadError(error instanceof Error ? error.message : "Upload failed.");
    }
  };

  const saveWorkspaceSettings = async () => {
    setWorkspaceState("loading");
    setWorkspaceMessage("");

    try {
      await settingsApi.updateWorkspace({ currency: currencyCode });
      setWorkspaceState("success");
      setWorkspaceMessage(`Workspace currency saved as ${currencyCode}.`);
    } catch (error) {
      setWorkspaceState("error");
      setWorkspaceMessage(error instanceof Error ? error.message : "Unable to save workspace preferences.");
    }
  };

  const persistAlertSettings = async (options?: { silent?: boolean }) => {
    if (validationErrors.length > 0) {
      if (!options?.silent) {
        setSaveState("error");
        setSaveMessage(validationErrors[0]);
      }
      return false;
    }

    if (!options?.silent) {
      setSaveState("loading");
      setSaveMessage("");
    }

    try {
      const response = await settingsApi.updateAlertSettings({
        low_cash_threshold: alertSettings.lowCashThreshold,
        high_expense_threshold: alertSettings.largeExpenseThreshold,
        anomaly_sensitivity: alertSettings.anomalySensitivity,
        email_enabled: alertSettings.emailEnabled,
        email_addresses: emailRecipients,
        slack_enabled: alertSettings.slackEnabled,
        slack_webhook_url: alertSettings.slackWebhook.trim() || null,
      });

      setAlertSettings(mapAlertSettings(response));

      if (!options?.silent) {
        setSaveState("success");
        setSaveMessage("Alert settings saved to the backend. In-app alerts, email, and Slack now share the same config.");
      }
      return true;
    } catch (error) {
      if (!options?.silent) {
        setSaveState("error");
        setSaveMessage(error instanceof Error ? error.message : "Unable to save alert settings.");
      }
      return false;
    }
  };

  const runChannelTest = async (channel: TestChannel) => {
    setChannelStatus((current) => ({
      ...current,
      [channel]: { state: "loading", message: "Saving latest settings before sending a test alert..." },
    }));

    const savedOk = await persistAlertSettings({ silent: true });
    if (!savedOk) {
      setChannelStatus((current) => ({
        ...current,
        [channel]: { state: "error", message: validationErrors[0] || "Save failed before test could run." },
      }));
      return;
    }

    try {
      const response = await settingsApi.testAlertChannel(channel);
      setChannelStatus((current) => ({
        ...current,
        [channel]: { state: "success", message: response.message },
      }));
    } catch (error) {
      setChannelStatus((current) => ({
        ...current,
        [channel]: {
          state: "error",
          message: error instanceof Error ? error.message : `Unable to send ${channel} test alert.`,
        },
      }));
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <section
        className="glass overflow-hidden"
        style={{
          background: `
            radial-gradient(circle at top left, rgba(201, 169, 98, 0.16), transparent 34%),
            radial-gradient(circle at top right, rgba(94, 158, 126, 0.14), transparent 26%),
            linear-gradient(180deg, rgba(14,14,14,0.98), rgba(8,8,8,0.98))
          `,
        }}
      >
        <div className="grid grid-cols-1 xl:grid-cols-[1.25fr_0.75fr] gap-5 p-5 md:p-6">
          <div>
            <div
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-semibold uppercase tracking-[0.18em]"
              style={{
                background: "rgba(201, 169, 98, 0.12)",
                color: "var(--accent)",
                border: "1px solid rgba(201, 169, 98, 0.24)",
              }}
            >
              <Bell size={12} />
              Alert Control Center
            </div>
            <h1 className="text-2xl md:text-3xl font-semibold mt-4" style={{ color: "var(--text)" }}>
              Settings that actually drive delivery, not just toggles.
            </h1>
            <p className="text-sm mt-3 max-w-2xl" style={{ color: "var(--text-muted)", lineHeight: 1.7 }}>
              The settings page now reflects the backend contract for alert thresholds and notification channels. In-app alerts remain the source of truth, while email and Slack mirror the same workspace rules once enabled.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-5">
              <div className="rounded-2xl p-3" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)" }}>
                <div className="text-[10px] uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>Base Currency</div>
                <div className="text-sm font-semibold mt-2" style={{ color: "var(--text)" }}>
                  {isLoading ? "Loading..." : currencyCode}
                </div>
              </div>
              <div className="rounded-2xl p-3" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)" }}>
                <div className="text-[10px] uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>Channels Ready</div>
                <div className="text-sm font-semibold mt-2" style={{ color: "var(--text)" }}>
                  {readyChannelCount} / 2
                </div>
              </div>
              <div className="rounded-2xl p-3" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)" }}>
                <div className="text-[10px] uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>Trigger Profile</div>
                <div className="text-xs font-medium mt-2" style={{ color: "var(--text)" }}>
                  {formatTriggerSummary(alertSettings, currencyCode)}
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-3xl p-4 md:p-5 h-full" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)" }}>
            <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: "var(--text)" }}>
              <Activity size={16} style={{ color: "var(--info)" }} />
              Wiring Status
            </div>
            <div className="space-y-3 mt-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-medium" style={{ color: "var(--text)" }}>Alert settings API</div>
                  <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                    Email recipients, Slack enablement, and webhook URL are now part of the shared backend contract.
                  </div>
                </div>
                <CheckCircle2 size={16} style={{ color: "var(--success)" }} />
              </div>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-medium" style={{ color: "var(--text)" }}>Threshold logic</div>
                  <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                    Low-cash, large-expense, and anomaly rules are aligned with backend calculations instead of mislabeled form fields.
                  </div>
                </div>
                <CheckCircle2 size={16} style={{ color: "var(--success)" }} />
              </div>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-medium" style={{ color: "var(--text)" }}>Delivery verification</div>
                  <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                    Save-and-test actions now hit backend endpoints so we can validate email and Slack from this page.
                  </div>
                </div>
                <CheckCircle2 size={16} style={{ color: "var(--success)" }} />
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 xl:grid-cols-[0.9fr_1.1fr] gap-5">
        <section className="glass p-5 md:p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div
                className="flex items-center justify-center rounded-2xl"
                style={{ width: 42, height: 42, background: "var(--accent-soft)" }}
              >
                <Briefcase size={18} style={{ color: "var(--accent)" }} />
              </div>
              <div>
                <h2 className="text-sm font-semibold" style={{ color: "var(--text)" }}>Workspace Preferences</h2>
                <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                  Keep the workspace currency aligned with reporting, exports, and alert copy.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={saveWorkspaceSettings}
              disabled={workspaceState === "loading"}
              className="px-3 py-2 rounded-xl text-xs font-medium flex items-center gap-2"
              style={{
                border: "1px solid var(--border)",
                color: "var(--text)",
                background: workspaceState === "success" ? "var(--accent-soft)" : "var(--surface-hover)",
              }}
            >
              {workspaceState === "loading" ? <Clock3 size={14} className="animate-spin" /> : <Save size={14} />}
              {workspaceState === "loading" ? "Saving..." : "Save Workspace"}
            </button>
          </div>

          <div className="mt-5">
            <label className="block text-[11px] font-semibold uppercase tracking-[0.16em] mb-2" style={{ color: "var(--text-muted)" }}>
              Base Currency
            </label>
            <select
              value={currencyCode}
              onChange={(event) => setCurrencyCode(event.target.value)}
              className="w-full rounded-2xl px-4 py-3 text-sm"
              style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)" }}
            >
              {SUPPORTED_CURRENCIES.map((currency) => (
                <option key={currency.code} value={currency.code}>
                  {currency.name}
                </option>
              ))}
            </select>
            <p className="text-xs mt-2" style={{ color: "var(--text-dim)" }}>
              This is the display and reporting currency used across dashboards, reports, and alert messaging.
            </p>
          </div>

          {workspaceMessage && (
            <div
              className="mt-4 rounded-2xl px-4 py-3 text-xs"
              style={{
                background: workspaceState === "error" ? "var(--danger-soft)" : "var(--accent-soft)",
                color: workspaceState === "error" ? "var(--danger)" : "var(--accent)",
                border: `1px solid ${workspaceState === "error" ? "rgba(199,80,80,0.25)" : "rgba(201,169,98,0.25)"}`,
              }}
            >
              {workspaceMessage}
            </div>
          )}
        </section>

        <section className="glass p-5 md:p-6">
          <div className="flex items-start gap-3">
            <div
              className="flex items-center justify-center rounded-2xl"
              style={{ width: 42, height: 42, background: "var(--info-soft)" }}
            >
              <FileSpreadsheet size={18} style={{ color: "var(--info)" }} />
            </div>
            <div>
              <h2 className="text-sm font-semibold" style={{ color: "var(--text)" }}>CSV Import</h2>
              <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                Upload bank exports or bookkeeping data. Alerts update after new transactions are ingested.
              </p>
            </div>
          </div>

          <div
            onClick={() => fileRef.current?.click()}
            onDragOver={(event) => {
              event.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragOver(false);
              const file = event.dataTransfer.files[0];
              if (file) {
                handleFile(file);
              }
            }}
            className="cursor-pointer rounded-3xl flex flex-col items-center justify-center gap-3 mt-5 transition-all"
            style={{
              border: `2px dashed ${dragOver ? "var(--accent)" : "var(--border)"}`,
              background: dragOver ? "rgba(201,169,98,0.08)" : "var(--bg)",
              padding: "36px 24px",
            }}
          >
            <div
              className="rounded-2xl flex items-center justify-center"
              style={{
                width: 52,
                height: 52,
                background: dragOver ? "var(--accent)" : "var(--surface)",
              }}
            >
              <Upload size={22} style={{ color: dragOver ? "#0a0a0a" : "var(--accent)" }} />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium" style={{ color: "var(--text)" }}>
                Drop a CSV here or click to browse
              </p>
              <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                Expected columns: date, description, amount, type, category
              </p>
            </div>
          </div>

          <input
            ref={fileRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) {
                handleFile(file);
              }
            }}
          />

          {uploadStatus !== "idle" && (
            <div
              className="mt-4 rounded-2xl px-4 py-3 text-sm flex items-center gap-2"
              style={{
                background:
                  uploadStatus === "success"
                    ? "var(--accent-soft)"
                    : uploadStatus === "error"
                      ? "var(--danger-soft)"
                      : "rgba(107,142,194,0.12)",
                color:
                  uploadStatus === "success"
                    ? "var(--accent)"
                    : uploadStatus === "error"
                      ? "var(--danger)"
                      : "var(--info)",
              }}
            >
              {uploadStatus === "loading" ? (
                <Clock3 size={15} className="animate-spin" />
              ) : uploadStatus === "success" ? (
                <CheckCircle2 size={15} />
              ) : (
                <AlertCircle size={15} />
              )}
              <span>
                {uploadStatus === "loading"
                  ? "Parsing and importing transactions..."
                  : uploadStatus === "success"
                    ? `Imported ${imported ?? 0} transaction${imported === 1 ? "" : "s"} successfully.`
                    : uploadError}
              </span>
            </div>
          )}
        </section>
      </div>

      <section className="glass p-5 md:p-6">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="flex items-start gap-3">
            <div
              className="flex items-center justify-center rounded-2xl"
              style={{ width: 42, height: 42, background: "var(--warning-soft)" }}
            >
              <Bell size={18} style={{ color: "var(--warning)" }} />
            </div>
            <div>
              <h2 className="text-sm font-semibold" style={{ color: "var(--text)" }}>Alert Automation</h2>
              <p className="text-xs mt-1 max-w-2xl" style={{ color: "var(--text-muted)", lineHeight: 1.7 }}>
                These settings feed the backend alert engine. In-app alerts are always created first; email and Slack act as delivery mirrors when their channel is enabled and passes the test action below.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => void persistAlertSettings()}
            disabled={loadingSettings || saveState === "loading"}
            className="px-4 py-2.5 rounded-2xl text-sm font-medium flex items-center justify-center gap-2"
            style={{
              background: "linear-gradient(135deg, rgba(201,169,98,1), rgba(214,148,90,0.92))",
              color: "#0b0b0b",
              opacity: loadingSettings ? 0.7 : 1,
            }}
          >
            {saveState === "loading" ? <Clock3 size={15} className="animate-spin" /> : <Save size={15} />}
            {saveState === "loading" ? "Saving..." : "Save Alert Settings"}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-5">
          <div className="rounded-2xl p-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
            <div className="text-[10px] uppercase tracking-[0.16em]" style={{ color: "var(--text-dim)" }}>Low Cash Threshold</div>
            <div className="text-lg font-semibold mt-2" style={{ color: "var(--text)" }}>
              {currencyCode} {Math.round(alertSettings.lowCashThreshold).toLocaleString()}
            </div>
            <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              Triggers when estimated cash balance falls beneath this floor.
            </div>
          </div>
          <div className="rounded-2xl p-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
            <div className="text-[10px] uppercase tracking-[0.16em]" style={{ color: "var(--text-dim)" }}>Large Expense Floor</div>
            <div className="text-lg font-semibold mt-2" style={{ color: "var(--text)" }}>
              {currencyCode} {Math.round(alertSettings.largeExpenseThreshold).toLocaleString()}
            </div>
            <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              Candidate amount for large-spend anomaly review.
            </div>
          </div>
          <div className="rounded-2xl p-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
            <div className="text-[10px] uppercase tracking-[0.16em]" style={{ color: "var(--text-dim)" }}>Anomaly Sensitivity</div>
            <div className="text-lg font-semibold mt-2" style={{ color: "var(--text)" }}>
              {alertSettings.anomalySensitivity.toFixed(1)}x
            </div>
            <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              Transaction must exceed this multiple of its category baseline.
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          <div>
            <label className="block text-[11px] font-semibold uppercase tracking-[0.16em] mb-2" style={{ color: "var(--text-muted)" }}>
              Low Cash Threshold ({currencyCode})
            </label>
            <input
              type="number"
              min={0}
              value={alertSettings.lowCashThreshold}
              onChange={(event) =>
                setAlertSettings((current) => ({
                  ...current,
                  lowCashThreshold: Number(event.target.value || 0),
                }))
              }
              className="w-full rounded-2xl px-4 py-3 text-sm"
              style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)" }}
            />
          </div>
          <div>
            <label className="block text-[11px] font-semibold uppercase tracking-[0.16em] mb-2" style={{ color: "var(--text-muted)" }}>
              Large Expense Floor ({currencyCode})
            </label>
            <input
              type="number"
              min={0}
              value={alertSettings.largeExpenseThreshold}
              onChange={(event) =>
                setAlertSettings((current) => ({
                  ...current,
                  largeExpenseThreshold: Number(event.target.value || 0),
                }))
              }
              className="w-full rounded-2xl px-4 py-3 text-sm"
              style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)" }}
            />
          </div>
          <div>
            <label className="block text-[11px] font-semibold uppercase tracking-[0.16em] mb-2" style={{ color: "var(--text-muted)" }}>
              Anomaly Sensitivity (x)
            </label>
            <input
              type="number"
              min={1}
              step="0.1"
              value={alertSettings.anomalySensitivity}
              onChange={(event) =>
                setAlertSettings((current) => ({
                  ...current,
                  anomalySensitivity: Number(event.target.value || 0),
                }))
              }
              className="w-full rounded-2xl px-4 py-3 text-sm"
              style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)" }}
            />
          </div>
        </div>

        <div className="rounded-2xl px-4 py-3 text-xs mt-4" style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-muted)" }}>
          Revenue decline alerts stay enabled in the backend and compare the current month against the trailing prior months. The settings above control low cash, large-expense screening, and anomaly sensitivity.
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mt-6">
          <div className="rounded-3xl p-5" style={{ background: "var(--bg)", border: "1px solid var(--border)" }}>
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div
                  className="flex items-center justify-center rounded-2xl"
                  style={{ width: 38, height: 38, background: "rgba(107,142,194,0.15)" }}
                >
                  <Mail size={17} style={{ color: "var(--info)" }} />
                </div>
                <div>
                  <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>Email Alerts</div>
                  <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                    Sends formatted alert summaries to the saved recipient list.
                  </div>
                </div>
              </div>
              <Toggle
                checked={alertSettings.emailEnabled}
                onChange={() =>
                  setAlertSettings((current) => ({
                    ...current,
                    emailEnabled: !current.emailEnabled,
                  }))
                }
              />
            </div>

            <div className="mt-4">
              <label className="block text-[11px] font-semibold uppercase tracking-[0.16em] mb-2" style={{ color: "var(--text-muted)" }}>
                Recipient List
              </label>
              <textarea
                rows={3}
                value={alertSettings.emailAddressInput}
                onChange={(event) =>
                  setAlertSettings((current) => ({
                    ...current,
                    emailAddressInput: event.target.value,
                  }))
                }
                placeholder="finance@example.com, founder@example.com"
                className="w-full rounded-2xl px-4 py-3 text-sm resize-none"
                style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)" }}
              />
              <p className="text-xs mt-2" style={{ color: "var(--text-dim)" }}>
                Separate multiple addresses with commas.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3 mt-4">
              <button
                type="button"
                onClick={() => void runChannelTest("email")}
                disabled={!alertSettings.emailEnabled || saveState === "loading"}
                className="px-3 py-2 rounded-xl text-xs font-medium flex items-center gap-2"
                style={{
                  background: "var(--surface-hover)",
                  border: "1px solid var(--border)",
                  color: "var(--text)",
                  opacity: alertSettings.emailEnabled ? 1 : 0.6,
                }}
              >
                {channelStatus.email.state === "loading" ? <Clock3 size={14} className="animate-spin" /> : <Send size={14} />}
                {channelStatus.email.state === "loading" ? "Testing..." : "Save and Test Email"}
              </button>
              <span
                className="px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase tracking-[0.14em]"
                style={{
                  background: emailReady ? "rgba(94,158,126,0.14)" : "rgba(255,255,255,0.06)",
                  color: emailReady ? "var(--success)" : "var(--text-dim)",
                }}
              >
                {emailReady ? "Ready" : "Needs setup"}
              </span>
            </div>

            {channelStatus.email.message && (
              <div
                className="mt-4 rounded-2xl px-4 py-3 text-xs"
                style={{
                  background: channelStatus.email.state === "error" ? "var(--danger-soft)" : "rgba(94,158,126,0.12)",
                  color: channelStatus.email.state === "error" ? "var(--danger)" : "var(--success)",
                }}
              >
                {channelStatus.email.message}
              </div>
            )}
          </div>

          <div className="rounded-3xl p-5" style={{ background: "var(--bg)", border: "1px solid var(--border)" }}>
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div
                  className="flex items-center justify-center rounded-2xl"
                  style={{ width: 38, height: 38, background: "rgba(201,169,98,0.15)" }}
                >
                  <MessageSquare size={17} style={{ color: "var(--accent)" }} />
                </div>
                <div>
                  <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>Slack Alerts</div>
                  <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                    Mirrors workspace alerts to a Slack Incoming Webhook endpoint.
                  </div>
                </div>
              </div>
              <Toggle
                checked={alertSettings.slackEnabled}
                onChange={() =>
                  setAlertSettings((current) => ({
                    ...current,
                    slackEnabled: !current.slackEnabled,
                  }))
                }
              />
            </div>

            <div className="mt-4">
              <label className="block text-[11px] font-semibold uppercase tracking-[0.16em] mb-2" style={{ color: "var(--text-muted)" }}>
                Webhook URL
              </label>
              <input
                type="url"
                value={alertSettings.slackWebhook}
                onChange={(event) =>
                  setAlertSettings((current) => ({
                    ...current,
                    slackWebhook: event.target.value,
                  }))
                }
                placeholder="https://hooks.slack.com/services/..."
                className="w-full rounded-2xl px-4 py-3 text-sm"
                style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)" }}
              />
              <p className="text-xs mt-2" style={{ color: "var(--text-dim)" }}>
                Paste the Incoming Webhook URL for the channel that should receive finance alerts.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3 mt-4">
              <button
                type="button"
                onClick={() => void runChannelTest("slack")}
                disabled={!alertSettings.slackEnabled || saveState === "loading"}
                className="px-3 py-2 rounded-xl text-xs font-medium flex items-center gap-2"
                style={{
                  background: "var(--surface-hover)",
                  border: "1px solid var(--border)",
                  color: "var(--text)",
                  opacity: alertSettings.slackEnabled ? 1 : 0.6,
                }}
              >
                {channelStatus.slack.state === "loading" ? <Clock3 size={14} className="animate-spin" /> : <Send size={14} />}
                {channelStatus.slack.state === "loading" ? "Testing..." : "Save and Test Slack"}
              </button>
              <span
                className="px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase tracking-[0.14em]"
                style={{
                  background: slackReady ? "rgba(94,158,126,0.14)" : "rgba(255,255,255,0.06)",
                  color: slackReady ? "var(--success)" : "var(--text-dim)",
                }}
              >
                {slackReady ? "Ready" : "Needs setup"}
              </span>
            </div>

            {channelStatus.slack.message && (
              <div
                className="mt-4 rounded-2xl px-4 py-3 text-xs"
                style={{
                  background: channelStatus.slack.state === "error" ? "var(--danger-soft)" : "rgba(94,158,126,0.12)",
                  color: channelStatus.slack.state === "error" ? "var(--danger)" : "var(--success)",
                }}
              >
                {channelStatus.slack.message}
              </div>
            )}
          </div>
        </div>

        {loadingSettings && (
          <div className="mt-4 text-xs" style={{ color: "var(--text-dim)" }}>
            Loading saved alert settings...
          </div>
        )}

        {(saveMessage || validationErrors.length > 0) && (
          <div
            className="mt-5 rounded-3xl p-4"
            style={{
              background:
                validationErrors.length > 0 || saveState === "error"
                  ? "var(--danger-soft)"
                  : saveState === "success"
                    ? "rgba(94,158,126,0.12)"
                    : "rgba(255,255,255,0.05)",
              border: `1px solid ${
                validationErrors.length > 0 || saveState === "error"
                  ? "rgba(199,80,80,0.25)"
                  : saveState === "success"
                    ? "rgba(94,158,126,0.24)"
                    : "var(--border)"
              }`,
            }}
          >
            {validationErrors.length > 0 ? (
              <div className="space-y-1 text-xs" style={{ color: "var(--danger)" }}>
                {validationErrors.map((error) => (
                  <div key={error}>{error}</div>
                ))}
              </div>
            ) : (
              <div className="text-xs" style={{ color: saveState === "success" ? "var(--success)" : "var(--text-muted)" }}>
                {saveMessage}
              </div>
            )}
          </div>
        )}
      </section>

      <section className="glass p-5 md:p-6">
        <div className="flex items-start gap-3">
          <div
            className="flex items-center justify-center rounded-2xl"
            style={{ width: 42, height: 42, background: "rgba(107,142,194,0.12)" }}
          >
            <Link2 size={18} style={{ color: "var(--info)" }} />
          </div>
          <div>
            <h2 className="text-sm font-semibold" style={{ color: "var(--text)" }}>Integration Roadmap</h2>
            <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              CSV upload is production-ready for this workspace. Live sync options remain staged separately.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 mt-5">
          {[
            { name: "Plaid bank sync", icon: Database, phase: "Phase 2", state: "Planned" },
            { name: "QuickBooks API", icon: Zap, phase: "Phase 2", state: "Planned" },
            { name: "Xero API", icon: Zap, phase: "Phase 2", state: "Planned" },
            { name: "Direct webhook automations", icon: Activity, phase: "Phase 3", state: "Later" },
          ].map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.name}
                className="rounded-2xl p-4"
                style={{ background: "var(--bg)", border: "1px solid var(--border)" }}
              >
                <div className="flex items-center gap-2">
                  <Icon size={15} style={{ color: "var(--text-dim)" }} />
                  <span className="text-sm font-medium" style={{ color: "var(--text)" }}>{item.name}</span>
                </div>
                <div className="text-xs mt-3" style={{ color: "var(--text-muted)" }}>{item.phase}</div>
                <div className="text-[11px] mt-2 uppercase tracking-[0.14em]" style={{ color: "var(--text-dim)" }}>{item.state}</div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
