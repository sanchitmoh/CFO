"use client";

import { useEffect, useRef, useState } from "react";
import { useUser, useAuth } from "@clerk/nextjs";
import Sidebar from "@/components/Sidebar";
import { onboardingApi, setTokenProvider } from "@/lib/api";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const provisionedRef = useRef(false);
  const [isProvisioning, setIsProvisioning] = useState(true);
  const [provisionError, setProvisionError] = useState<string | null>(null);

  // ⚡ Register Clerk's getToken SYNCHRONOUSLY during render.
  // This MUST happen before children mount, not in useEffect (which
  // fires bottom-up — children's effects run before parent's).
  if (isLoaded && isSignedIn) {
    setTokenProvider(getToken);
  }

  // Provision workspace + user on first authenticated render.
  // Idempotent — the backend returns "already_exists" on subsequent calls.
  useEffect(() => {
    if (isLoaded && isSignedIn && !provisionedRef.current) {
      provisionedRef.current = true;
      setIsProvisioning(true);
      setProvisionError(null);
      
      onboardingApi
        .provision()
        .then(() => {
          console.log("[onboarding] Provision successful");
          setIsProvisioning(false);
        })
        .catch((err) => {
          console.error("[onboarding] Provision failed:", err);
          setProvisionError(err instanceof Error ? err.message : "Provisioning failed");
          setIsProvisioning(false);
          provisionedRef.current = false; // allow retry on next render
        });
    } else if (isLoaded && isSignedIn && provisionedRef.current) {
      // Already provisioned in a previous render
      setIsProvisioning(false);
    }
  }, [isLoaded, isSignedIn]);

  if (!isLoaded || isProvisioning) {
    return (
      <div
        className="flex items-center justify-center"
        style={{ height: "100vh", background: "var(--bg-deep)" }}
      >
        <div
          className="animate-pulse text-sm font-medium"
          style={{ color: "var(--text-muted)" }}
        >
          {!isLoaded ? "Loading…" : "Setting up your workspace…"}
        </div>
      </div>
    );
  }

  if (provisionError) {
    return (
      <div
        className="flex items-center justify-center"
        style={{ height: "100vh", background: "var(--bg-deep)" }}
      >
        <div className="text-center">
          <div
            className="text-sm font-medium mb-2"
            style={{ color: "var(--danger)" }}
          >
            Failed to set up workspace
          </div>
          <div
            className="text-xs mb-4"
            style={{ color: "var(--text-muted)" }}
          >
            {provisionError}
          </div>
          <button
            onClick={() => {
              provisionedRef.current = false;
              setProvisionError(null);
              setIsProvisioning(true);
            }}
            className="btn btn-primary"
          >
            Retry
          </button>
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
