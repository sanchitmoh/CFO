"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import type { Alert } from "@/lib/types";
import {
  AlertTriangle,
  Bell,
  CheckCircle,
  Info,
  XCircle,
} from "lucide-react";

const SEV_CONFIG: Record<
  string,
  { icon: typeof AlertTriangle; color: string; bg: string; badge: string }
> = {
  critical: { icon: XCircle, color: "var(--danger)", bg: "var(--danger-soft)", badge: "badge-critical" },
  high: { icon: AlertTriangle, color: "var(--warning)", bg: "var(--warning-soft)", badge: "badge-warning" },
  medium: { icon: Info, color: "var(--info)", bg: "var(--info-soft)", badge: "badge-info" },
  low: { icon: Info, color: "var(--text-muted)", bg: "var(--accent-soft)", badge: "badge-income" },
};

export default function AlertsPage() {
  const { getToken } = useAuth();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const token = await getToken();
      const data = await api.getAlerts(false, token);
      setAlerts(data);
    } catch {
      /* show empty state */
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    load();
  }, [load]);

  const dismiss = async (id: string) => {
    try {
      const token = await getToken();
      await api.dismissAlert(id, token);
      setAlerts((prev) => prev.filter((a) => a.id !== id));
    } catch {
      /* ignore */
    }
  };

  const active = alerts.filter((a) => !a.is_dismissed);
  const dismissed = alerts.filter((a) => a.is_dismissed);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="animate-fade-up">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>Alerts</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          {active.length} active alert{active.length !== 1 ? "s" : ""}
        </p>
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 80 }} />
          ))}
        </div>
      ) : alerts.length === 0 ? (
        <div className="glass p-12 text-center">
          <CheckCircle size={40} className="mx-auto mb-3" style={{ color: "var(--accent)" }} />
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>All clear! No alerts at this time.</p>
        </div>
      ) : (
        <>
          {active.length > 0 && (
            <div className="space-y-3">
              {active.map((a, i) => {
                const sev = SEV_CONFIG[a.severity] ?? SEV_CONFIG.medium;
                const Icon = sev.icon;
                return (
                  <div
                    key={a.id}
                    className={`glass glass-hover p-5 flex items-start gap-4 animate-fade-up delay-${(i % 6) + 1}`}
                    style={{ borderLeft: `3px solid ${sev.color}` }}
                  >
                    <div className="flex items-center justify-center shrink-0" style={{ width: 36, height: 36, borderRadius: 8, background: sev.bg }}>
                      <Icon size={18} style={{ color: sev.color }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>{a.title}</span>
                        <span className={`badge ${sev.badge}`}>{a.severity}</span>
                      </div>
                      <p className="text-sm" style={{ color: "var(--text-muted)" }}>{a.message}</p>
                      <p className="text-xs mt-1" style={{ color: "var(--text-dim)" }}>
                        {new Date(a.created_at).toLocaleString()}
                      </p>
                    </div>
                    <button onClick={() => dismiss(a.id)} className="btn-ghost text-xs py-1.5 px-3 shrink-0">Dismiss</button>
                  </div>
                );
              })}
            </div>
          )}

          {dismissed.length > 0 && (
            <div>
              <h3 className="text-xs font-medium uppercase tracking-wider mb-3" style={{ color: "var(--text-dim)" }}>
                Dismissed ({dismissed.length})
              </h3>
              <div className="space-y-2">
                {dismissed.slice(0, 5).map((a) => (
                  <div key={a.id} className="glass p-4 flex items-center gap-3 opacity-50">
                    <Bell size={14} style={{ color: "var(--text-dim)" }} />
                    <span className="text-sm" style={{ color: "var(--text-dim)" }}>{a.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
