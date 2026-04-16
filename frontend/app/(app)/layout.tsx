"use client";

import { useUser } from "@clerk/nextjs";
import Sidebar from "@/components/Sidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { isLoaded, isSignedIn } = useUser();

  if (!isLoaded) {
    return (
      <div
        className="flex items-center justify-center"
        style={{ height: "100vh", background: "var(--bg-deep)" }}
      >
        <div
          className="animate-pulse text-sm font-medium"
          style={{ color: "var(--text-muted)" }}
        >
          Loading…
        </div>
      </div>
    );
  }

  if (!isSignedIn) return null;

  return (
    <div className="flex min-h-screen" style={{ background: "var(--bg-deep)" }}>
      <Sidebar />
      <main
        className="flex-1 p-8 overflow-y-auto"
        style={{ marginLeft: 240, minHeight: "100vh" }}
      >
        {children}
      </main>
    </div>
  );
}
