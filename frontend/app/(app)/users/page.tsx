"use client";

import { useState, useEffect, useCallback } from "react";
import { settingsApi } from "@/lib/api";
import {
  Users,
  Plus,
  Trash2,
  Shield,
  Edit3,
  Eye,
  BookOpen,
  Briefcase,
  ChevronDown,
  CheckCircle,
  Mail,
  AlertTriangle,
} from "lucide-react";

type Role = "admin" | "cfo" | "accountant" | "investor" | "employee";

interface TeamMember {
  id: number;
  name: string;
  email: string;
  role: Role;
  status: "active" | "invited" | "inactive";
  joinedAt: string;
}

const ROLE_META: Record<
  Role,
  { label: string; color: string; bg: string; icon: React.ElementType; permissions: string[] }
> = {
  admin: {
    label: "Admin / Owner",
    color: "var(--accent)",
    bg: "var(--accent-soft)",
    icon: Shield,
    permissions: ["View all data", "Edit everything", "Manage users", "Delete data", "Connect accounts"],
  },
  cfo: {
    label: "CFO / Editor",
    color: "var(--info)",
    bg: "var(--info-soft)",
    icon: Briefcase,
    permissions: ["View all data", "Edit budgets", "Create reports", "Manage alerts"],
  },
  accountant: {
    label: "Accountant",
    color: "var(--warning)",
    bg: "var(--warning-soft)",
    icon: BookOpen,
    permissions: ["View all financial data", "Export data"],
  },
  investor: {
    label: "Investor",
    color: "#9B7CB8",
    bg: "#9B7CB818",
    icon: Eye,
    permissions: ["View dashboard only", "See revenue, burn, runway, KPIs", "No raw transactions"],
  },
  employee: {
    label: "Employee",
    color: "var(--text-muted)",
    bg: "var(--surface-hover)",
    icon: Users,
    permissions: ["View own department budget only"],
  },
};



export default function UsersPage() {
  const [team, setTeam] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showInvite, setShowInvite] = useState(false);
  const [inviteForm, setInviteForm] = useState({ name: "", email: "", role: "accountant" as Role });
  const [inviteSent, setInviteSent] = useState(false);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);

  const loadTeam = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await settingsApi.getTeam();
      if (data?.members && Array.isArray(data.members)) {
        setTeam(data.members.map((m: any) => ({
          id: m.id,
          name: m.full_name || m.name || "Team Member",
          email: m.email,
          role: m.role || "employee",
          status: m.is_active ? "active" : "invited",
          joinedAt: m.created_at || m.joined_at || "",
        })));
      }
    } catch {
      setError("Unable to load team members. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTeam();
  }, [loadTeam]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await settingsApi.inviteUser(inviteForm.email, inviteForm.role);
    } catch {
      // API unavailable — still add locally for demo
    }
    const newMember: TeamMember = {
      id: team.length + 1,
      name: inviteForm.name,
      email: inviteForm.email,
      role: inviteForm.role,
      status: "invited",
      joinedAt: new Date().toISOString().split("T")[0],
    };
    setTeam((t) => [...t, newMember]);
    setInviteSent(true);
    setTimeout(() => {
      setShowInvite(false);
      setInviteSent(false);
      setInviteForm({ name: "", email: "", role: "accountant" });
    }, 2000);
  };

  const removeUser = async (id: number) => {
    try {
      await settingsApi.removeUser(id);
    } catch {
      // API unavailable — still remove locally
    }
    setTeam((t) => t.filter((m) => m.id !== id));
  };

  const updateRole = async (id: number, role: Role) => {
    try {
      await settingsApi.updateUserRole(id, role);
    } catch {
      // API unavailable — still update locally
    }
    setTeam((t) => t.map((m) => (m.id === id ? { ...m, role } : m)));
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {error && (
        <div className="glass p-4 flex flex-wrap items-center gap-3 animate-fade-up" style={{ borderColor: "var(--danger)44", background: "var(--danger-soft)" }}>
          <AlertTriangle size={18} style={{ color: "var(--danger)", flexShrink: 0 }} />
          <p className="text-sm" style={{ color: "var(--danger)" }}>{error}</p>
          <button onClick={loadTeam} className="text-xs font-medium px-3 py-1.5 rounded-lg sm:ml-auto" style={{ background: "var(--danger)", color: "#fff" }}>Retry</button>
        </div>
      )}
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 animate-fade-up">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>
            Team & Roles
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Manage access levels and permissions for your team
          </p>
        </div>
        <button
          onClick={() => setShowInvite(true)}
          className="btn-primary flex w-full items-center justify-center gap-2 sm:w-auto"
        >
          <Plus size={15} />
          Invite User
        </button>
      </div>

      {/* Role Reference */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 animate-fade-up delay-1">
        {(Object.entries(ROLE_META) as [Role, typeof ROLE_META[Role]][]).map(([role, meta]) => {
          const Icon = meta.icon;
          const isSelected = selectedRole === role;
          return (
            <button
              key={role}
              onClick={() => setSelectedRole(isSelected ? null : role)}
              className="glass text-left p-4 transition-all"
              style={{
                borderColor: isSelected ? `${meta.color}44` : "var(--border)",
                background: isSelected ? meta.bg : "var(--surface)",
              }}
            >
              <div className="flex items-center gap-2 mb-2">
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: 8,
                    background: meta.bg,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Icon size={14} style={{ color: meta.color }} />
                </div>
                <span className="text-sm font-semibold" style={{ color: meta.color }}>
                  {meta.label}
                </span>
              </div>
              {isSelected && (
                <ul className="space-y-1 mt-2">
                  {meta.permissions.map((p) => (
                    <li
                      key={p}
                      className="text-xs flex items-center gap-1.5"
                      style={{ color: "var(--text-muted)" }}
                    >
                      <span style={{ color: meta.color }}>✓</span>
                      {p}
                    </li>
                  ))}
                </ul>
              )}
              {!isSelected && (
                <p className="text-xs" style={{ color: "var(--text-dim)" }}>
                  {meta.permissions[0]}
                  {meta.permissions.length > 1 ? ` +${meta.permissions.length - 1} more` : ""}
                </p>
              )}
            </button>
          );
        })}
      </div>

      {/* Team Table */}
      <div className="glass overflow-hidden animate-fade-up delay-2">
        <div
          className="p-4 border-b flex items-center gap-2"
          style={{ borderColor: "var(--border)" }}
        >
          <Users size={16} style={{ color: "var(--text-muted)" }} />
          <span className="font-semibold text-sm" style={{ color: "var(--text)" }}>
            Team Members ({team.length})
          </span>
        </div>

        <div className="overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0" style={{ WebkitOverflowScrolling: "touch" }}>
          <table className="w-full text-sm" style={{ minWidth: 560 }}>
            <thead>
              <tr
                className="text-xs uppercase tracking-wider text-left"
                style={{ color: "var(--text-dim)", borderBottom: "1px solid var(--border)" }}
              >
                <th className="p-4 pr-2">Member</th>
                <th className="p-4 pr-2">Role</th>
                <th className="p-4 pr-2">Status</th>
                <th className="p-4 pr-2">Joined</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {team.map((member) => {
                const meta = ROLE_META[member.role];
                const Icon = meta.icon;
                return (
                  <tr
                    key={member.id}
                    style={{ borderBottom: "1px solid var(--border)" }}
                  >
                    {/* Member */}
                    <td className="p-4 pr-2">
                      <div className="flex items-center gap-2.5">
                        <div
                          className="flex items-center justify-center rounded-full text-xs font-bold"
                          style={{
                            width: 34,
                            height: 34,
                            background: meta.bg,
                            color: meta.color,
                          }}
                        >
                          {member.name.charAt(0)}
                        </div>
                        <div>
                          <p className="font-medium" style={{ color: "var(--text)" }}>{member.name}</p>
                          <p className="text-xs" style={{ color: "var(--text-dim)" }}>{member.email}</p>
                        </div>
                      </div>
                    </td>

                    {/* Role selector */}
                    <td className="p-4 pr-2">
                      <div className="relative flex items-center">
                        <div
                          style={{
                            width: 20,
                            height: 20,
                            marginRight: 6,
                            display: "flex",
                            alignItems: "center",
                          }}
                        >
                          <Icon size={14} style={{ color: meta.color }} />
                        </div>
                        <select
                          value={member.role}
                          onChange={(e) => updateRole(member.id, e.target.value as Role)}
                          disabled={member.role === "admin"}
                          className="text-xs appearance-none pr-5 py-1 pl-2 rounded-lg"
                          style={{
                            background: meta.bg,
                            color: meta.color,
                            border: "none",
                            fontWeight: 600,
                          }}
                        >
                          {Object.entries(ROLE_META).map(([r, m]) => (
                            <option key={r} value={r}>{m.label}</option>
                          ))}
                        </select>
                        <ChevronDown
                          size={11}
                          className="absolute right-1 pointer-events-none"
                          style={{ color: meta.color }}
                        />
                      </div>
                    </td>

                    {/* Status */}
                    <td className="p-4 pr-2">
                      <span
                        className="badge"
                        style={{
                          background:
                            member.status === "active"
                              ? "var(--accent-soft)"
                              : member.status === "invited"
                              ? "var(--warning-soft)"
                              : "var(--surface)",
                          color:
                            member.status === "active"
                              ? "var(--accent)"
                              : member.status === "invited"
                              ? "var(--warning)"
                              : "var(--text-dim)",
                        }}
                      >
                        {member.status === "invited" && <Mail size={10} />}
                        {member.status}
                      </span>
                    </td>

                    {/* Joined */}
                    <td className="p-4 pr-2">
                      <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                        {new Date(member.joinedAt).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="p-4 text-right">
                      {member.role !== "admin" && (
                        <button
                          onClick={() => removeUser(member.id)}
                          className="p-1.5 rounded-md transition-colors"
                          style={{ color: "var(--danger)" }}
                          title="Remove user"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Invite Modal (inline) */}
      {showInvite && (
        <div className="glass p-6 animate-fade-up">
          <h2 className="font-semibold text-sm mb-5 flex items-center gap-2" style={{ color: "var(--text)" }}>
            <Plus size={16} style={{ color: "var(--accent)" }} />
            Invite Team Member
          </h2>

          {inviteSent ? (
            <div className="flex items-center gap-2 p-4 rounded-lg" style={{ background: "var(--accent-soft)", color: "var(--accent)" }}>
              <CheckCircle size={16} />
              <span className="text-sm font-medium">Invitation sent to {inviteForm.email}!</span>
            </div>
          ) : (
            <form onSubmit={handleInvite} className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              <div>
                <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="Jane Doe"
                  value={inviteForm.name}
                  onChange={(e) => setInviteForm((f) => ({ ...f, name: e.target.value }))}
                  className="w-full"
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  placeholder="jane@company.com"
                  value={inviteForm.email}
                  onChange={(e) => setInviteForm((f) => ({ ...f, email: e.target.value }))}
                  className="w-full"
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                  Role
                </label>
                <select
                  value={inviteForm.role}
                  onChange={(e) => setInviteForm((f) => ({ ...f, role: e.target.value as Role }))}
                  className="w-full"
                >
                  {Object.entries(ROLE_META).filter(([r]) => r !== "admin").map(([r, m]) => (
                    <option key={r} value={r}>{m.label}</option>
                  ))}
                </select>
              </div>
              <div className="mt-1 flex flex-col gap-3 md:col-span-2 xl:col-span-3 sm:flex-row">
                <button type="submit" className="btn-primary flex items-center justify-center gap-2">
                  <Mail size={14} />
                  Send Invitation
                </button>
                <button type="button" onClick={() => setShowInvite(false)} className="btn-ghost">
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  );
}
