"use client";

import { useState, useEffect, useCallback } from "react";
import { auditApi } from "@/lib/api";
import {
  ClipboardList,
  Filter,
  Calendar,
  User,
  FileText,
  TrendingUp,
  Bell,
  Upload,
  Download,
  Settings,
  ChevronDown,
  AlertTriangle,
} from "lucide-react";

interface AuditEntry {
  id: number;
  timestamp: string;
  user: string;
  action: string;
  category: string;
  detail: string;
  before?: string;
  after?: string;
}

const CATEGORIES = ["all", "budget", "forecast", "alert", "upload", "export", "settings"];

const CATEGORY_ICONS: Record<string, React.ElementType> = {
  budget: TrendingUp,
  forecast: TrendingUp,
  alert: Bell,
  upload: Upload,
  export: Download,
  settings: Settings,
  default: FileText,
};

const CATEGORY_COLORS: Record<string, string> = {
  budget: "var(--warning)",
  forecast: "var(--accent)",
  alert: "var(--danger)",
  upload: "var(--info)",
  export: "var(--info)",
  settings: "var(--text-muted)",
};



function fmtDate(ts: string) {
  const d = new Date(ts);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [userFilter, setUserFilter] = useState("all");
  const [expanded, setExpanded] = useState<number | null>(null);

  const loadAuditLog = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await auditApi.list({ days: 90 });
      if (data?.items?.length) {
        setEntries(
          data.items.map((log: any) => ({
            id: log.id,
            timestamp: log.created_at || log.timestamp,
            user: log.user_email || log.user || "system",
            action: log.action || log.event_type || "",
            category: log.entity_type || "default",
            detail: log.detail || log.description || "",
            before: log.old_value,
            after: log.new_value,
          }))
        );
      }
    } catch {
      setError("Unable to load audit trail. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAuditLog();
  }, [loadAuditLog]);

  const users = ["all", ...Array.from(new Set(entries.map((e) => e.user)))];

  const filtered = entries.filter((e) => {
    if (categoryFilter !== "all" && e.category !== categoryFilter) return false;
    if (userFilter !== "all" && e.user !== userFilter) return false;
    return true;
  });

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {error && (
        <div className="glass p-4 flex items-center gap-3 animate-fade-up" style={{ borderColor: "var(--danger)44", background: "var(--danger-soft)" }}>
          <AlertTriangle size={18} style={{ color: "var(--danger)", flexShrink: 0 }} />
          <p className="text-sm" style={{ color: "var(--danger)" }}>{error}</p>
          <button onClick={loadAuditLog} className="ml-auto text-xs font-medium px-3 py-1.5 rounded-lg" style={{ background: "var(--danger)", color: "#fff" }}>Retry</button>
        </div>
      )}
      {/* Header */}
      <div className="animate-fade-up">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>
          Audit Trail
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          Complete log of every significant action — who did what, when, and what changed
        </p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-4 gap-4 animate-fade-up delay-1">
        {[
          { label: "Total Events", value: entries.length, color: "var(--text)" },
          { label: "Budget Changes", value: entries.filter(e => e.category === "budget").length, color: "var(--warning)" },
          { label: "Uploads", value: entries.filter(e => e.category === "upload").length, color: "var(--info)" },
          { label: "Exports", value: entries.filter(e => e.category === "export").length, color: "var(--accent)" },
        ].map(({ label, value, color }) => (
          <div key={label} className="glass p-4">
            <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "var(--text-muted)" }}>
              {label}
            </p>
            <p className="text-2xl font-bold" style={{ color }}>{value}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="glass p-4 flex flex-wrap items-center gap-4 animate-fade-up delay-2">
        <Filter size={15} style={{ color: "var(--text-muted)" }} />

        {/* Category filter */}
        <div className="flex gap-2 flex-wrap">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className="px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all"
              style={{
                background: categoryFilter === cat ? "var(--accent-soft)" : "var(--surface)",
                color: categoryFilter === cat ? "var(--accent)" : "var(--text-muted)",
                border: `1px solid ${categoryFilter === cat ? "var(--accent)44" : "var(--border)"}`,
              }}
            >
              {cat === "all" ? "All Events" : cat}
            </button>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <User size={14} style={{ color: "var(--text-muted)" }} />
          <div className="relative">
            <select
              value={userFilter}
              onChange={(e) => setUserFilter(e.target.value)}
              className="text-sm appearance-none pr-7"
              style={{ background: "var(--surface)", paddingRight: 28 }}
            >
              {users.map((u) => (
                <option key={u} value={u}>
                  {u === "all" ? "All Users" : u}
                </option>
              ))}
            </select>
            <ChevronDown
              size={12}
              className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none"
              style={{ color: "var(--text-muted)" }}
            />
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="space-y-2 animate-fade-up delay-3">
        {filtered.length === 0 && (
          <div className="glass p-10 text-center">
            <ClipboardList size={32} className="mx-auto mb-2" style={{ color: "var(--text-dim)" }} />
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>No events match your filters</p>
          </div>
        )}

        {filtered.map((entry) => {
          const CatIcon = CATEGORY_ICONS[entry.category] || CATEGORY_ICONS.default;
          const catColor = CATEGORY_COLORS[entry.category] || "var(--text-muted)";
          const isExpanded = expanded === entry.id;

          return (
            <div
              key={entry.id}
              className="glass transition-all"
              style={{ borderColor: isExpanded ? `${catColor}33` : "var(--border)" }}
            >
              <button
                className="w-full text-left p-4 flex items-start justify-between gap-4"
                onClick={() => setExpanded(isExpanded ? null : entry.id)}
              >
                <div className="flex items-start gap-3 flex-1">
                  {/* Icon */}
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: 8,
                      background: `${catColor}18`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      marginTop: 2,
                    }}
                  >
                    <CatIcon size={14} style={{ color: catColor }} />
                  </div>

                  {/* Content */}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                        {entry.action}
                      </span>
                      <span
                        className="badge capitalize"
                        style={{ background: `${catColor}18`, color: catColor }}
                      >
                        {entry.category}
                      </span>
                      {entry.before && entry.after && (
                        <span className="text-xs flex items-center gap-1" style={{ color: "var(--text-muted)" }}>
                          <span style={{ color: "var(--danger)" }}>{entry.before}</span>
                          <span>→</span>
                          <span style={{ color: "var(--accent)" }}>{entry.after}</span>
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-xs" style={{ color: "var(--text-dim)" }}>
                      <span className="flex items-center gap-1">
                        <User size={11} />
                        {entry.user}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar size={11} />
                        {fmtDate(entry.timestamp)}
                      </span>
                    </div>
                  </div>
                </div>

                <ChevronDown
                  size={16}
                  style={{
                    color: "var(--text-dim)",
                    transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
                    transition: "transform 0.2s",
                    flexShrink: 0,
                    marginTop: 4,
                  }}
                />
              </button>

              {isExpanded && (
                <div
                  className="px-4 pb-4"
                  style={{ borderTop: "1px solid var(--border)" }}
                >
                  <div
                    className="mt-3 p-3 rounded-lg text-sm"
                    style={{ background: "var(--bg)", color: "var(--text-muted)" }}
                  >
                    <strong style={{ color: "var(--text)" }}>Detail: </strong>
                    {entry.detail}
                  </div>
                  <p className="text-xs mt-2" style={{ color: "var(--text-dim)" }}>
                    Event ID: #{entry.id} · Full timestamp: {new Date(entry.timestamp).toISOString()}
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <p className="text-xs text-center animate-fade-up delay-5" style={{ color: "var(--text-dim)" }}>
        All actions are logged automatically. Audit trail cannot be modified or deleted.
      </p>
    </div>
  );
}
