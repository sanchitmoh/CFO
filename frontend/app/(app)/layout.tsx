"use client";

import { useEffect, useRef } from "react";
import { useUser } from "@clerk/nextjs";
import Sidebar from "@/components/Sidebar";
import { onboardingApi } from "@/lib/api";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { isLoaded, isSignedIn } = useUser();
  const provisionedRef = useRef(false);

  // Provision workspace + user on first authenticated render.
  // Idempotent — the backend returns "already_exists" on subsequent calls.
  useEffect(() => {
    if (isLoaded && isSignedIn && !provisionedRef.current) {
      provisionedRef.current = true;
      onboardingApi.provision().catch((err) => {
        console.error("[onboarding] Provision failed:", err);
        provisionedRef.current = false; // allow retry on next render
      });
    }
  }, [isLoaded, isSignedIn]);

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
