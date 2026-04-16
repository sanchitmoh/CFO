"use client";

import { useState } from "react";
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
    color: "#A855F7",
    bg: "#A855F718",
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

const DEMO_TEAM: TeamMember[] = [
  { id: 1, name: "Sarah Johnson", email: "admin@lunabakery.com", role: "admin", status: "active", joinedAt: "2024-09-01" },
  { id: 2, name: "Raj Patel", email: "cfo@lunabakery.com", role: "cfo", status: "active", joinedAt: "2024-11-15" },
  { id: 3, name: "Priya Agarwal", email: "accountant@lunabakery.com", role: "accountant", status: "active", joinedAt: "2024-12-01" },
  { id: 4, name: "Mark Chen", email: "investor@venturecap.com", role: "investor", status: "invited", joinedAt: "2025-01-10" },
  { id: 5, name: "Lisa Kumar", email: "ops@lunabakery.com", role: "employee", status: "active", joinedAt: "2025-01-05" },
];

export default function UsersPage() {
  const [team, setTeam] = useState<TeamMember[]>(DEMO_TEAM);
  const [showInvite, setShowInvite] = useState(false);
  const [inviteForm, setInviteForm] = useState({ name: "", email: "", role: "accountant" as Role });
  const [inviteSent, setInviteSent] = useState(false);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);

  const handleInvite = (e: React.FormEvent) => {
    e.preventDefault();
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

  const removeUser = (id: number) => {
    setTeam((t) => t.filter((m) => m.id !== id));
  };

  const updateRole = (id: number, role: Role) => {
    setTeam((t) => t.map((m) => (m.id === id ? { ...m, role } : m)));
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between animate-fade-up">
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
          className="btn-primary flex items-center gap-2"
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

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
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
            <form onSubmit={handleInvite} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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
              <div className="sm:col-span-3 flex gap-3 mt-1">
                <button type="submit" className="btn-primary flex items-center gap-2">
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
