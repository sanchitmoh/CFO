"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useUser, useClerk } from "@clerk/nextjs";
import {
  LayoutDashboard,
  ArrowLeftRight,
  Wallet,
  Bell,
  TrendingUp,
  MessageSquare,
  LogOut,
  Bot,
  ShieldAlert,
  Settings,
  Calculator,
  FileText,
  ClipboardList,
  Users,
  Eye,
  Target,
} from "lucide-react";

const NAV_PRIMARY = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "AI Chat", icon: MessageSquare },
  { href: "/forecasting", label: "Forecasting", icon: TrendingUp },
];

const NAV_MANAGE = [
  { href: "/transactions", label: "Transactions", icon: ArrowLeftRight },
  { href: "/budgets", label: "Budgets", icon: Wallet },
  { href: "/goals", label: "Goals", icon: Target },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/anomalies", label: "Anomalies", icon: ShieldAlert },
];

const NAV_TOOLS = [
  { href: "/calculator", label: "Afford Calculator", icon: Calculator },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/audit", label: "Audit Trail", icon: ClipboardList },
];

const NAV_ADMIN = [
  { href: "/users", label: "Team & Roles", icon: Users },
  { href: "/investor", label: "Investor View", icon: Eye },
  { href: "/settings", label: "Settings", icon: Settings },
];

function NavGroup({ title, items, path }: { title: string; items: typeof NAV_PRIMARY; path: string }) {
  return (
    <>
      <p className="text-xs uppercase tracking-widest font-semibold px-3 pt-4 pb-1" style={{ color: "var(--text-dim)" }}>
        {title}
      </p>
      {items.map(({ href, label, icon: Icon }) => {
        const active = path === href;
        return (
          <Link key={href} href={href}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm no-underline transition-all duration-200"
            style={{ background: active ? "var(--accent-soft)" : "transparent", color: active ? "var(--accent)" : "var(--text-muted)", fontWeight: active ? 600 : 400 }}
          >
            <Icon size={16} />{label}
          </Link>
        );
      })}
    </>
  );
}

export default function Sidebar() {
  const path = usePathname();
  const { user } = useUser();
  const { signOut } = useClerk();

  return (
    <aside
      className="fixed left-0 top-0 bottom-0 flex flex-col justify-between py-6 px-4"
      style={{
        width: 240,
        background: "var(--bg)",
        borderRight: "1px solid var(--border)",
        zIndex: 50,
      }}
    >
      {/* Brand */}
      <div>
        <Link
          href="/dashboard"
          className="flex items-center gap-3 px-3 mb-8 no-underline"
        >
          <div
            className="flex items-center justify-center"
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background:
                "linear-gradient(135deg, var(--accent), var(--accent)88)",
            }}
          >
            <Bot size={20} style={{ color: "var(--bg)" }} />
          </div>
          <div>
            <div
              className="font-bold text-sm"
              style={{ color: "var(--text)", letterSpacing: "0.04em" }}
            >
              AI CFO
            </div>
            <div className="text-xs" style={{ color: "var(--text-dim)" }}>
              Financial Intelligence
            </div>
          </div>
        </Link>

        {/* Nav links */}
        <nav className="flex flex-col gap-0.5 overflow-y-auto" style={{ maxHeight: "calc(100vh - 200px)" }}>
          <NavGroup title="Overview" items={NAV_PRIMARY} path={path} />
          <NavGroup title="Finances" items={NAV_MANAGE} path={path} />
          <NavGroup title="Tools" items={NAV_TOOLS} path={path} />
          <NavGroup title="Admin" items={NAV_ADMIN} path={path} />
        </nav>
      </div>

      {/* User + Logout */}
      {user && (
        <div
          className="flex items-center justify-between px-3 py-3 rounded-lg"
          style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
        >
          <div className="min-w-0">
            <div
              className="text-xs font-medium truncate"
              style={{ color: "var(--text)" }}
            >
              {user.fullName || user.firstName || "User"}
            </div>
            <div
              className="text-xs truncate"
              style={{ color: "var(--text-dim)" }}
            >
              {user.primaryEmailAddress?.emailAddress || ""}
            </div>
          </div>
          <button
            onClick={() => signOut({ redirectUrl: "/sign-in" })}
            className="ml-2 p-1.5 rounded-md transition-colors"
            style={{ color: "var(--text-dim)" }}
            title="Sign out"
          >
            <LogOut size={16} />
          </button>
        </div>
      )}
    </aside>
  );
}
