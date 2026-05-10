"use client";

import React, { createContext, useContext, useEffect, useState, useMemo } from "react";
import { api } from "@/lib/api";

interface CurrencyContextType {
  currencyCode: string;
  setCurrencyCode: (code: string) => void;
  formatAmount: (value: number) => string;
  isLoading: boolean;
}

const CurrencyContext = createContext<CurrencyContextType | undefined>(undefined);

export function CurrencyProvider({ children }: { children: React.ReactNode }) {
  const [currencyCode, setCurrencyCode] = useState<string>("USD");
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    // Fetch workspace settings to get the currency
    api.settings.getWorkspace()
      .then((workspace) => {
        if (workspace.currency) {
          setCurrencyCode(workspace.currency.toUpperCase());
        }
      })
      .catch((err) => {
        console.error("Failed to fetch workspace currency:", err);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  const formatAmount = useMemo(() => {
    return (value: number) => {
      try {
        return new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: currencyCode,
          minimumFractionDigits: 0,
        }).format(value);
      } catch (e) {
        // Fallback if currency code is somehow invalid
        return new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: "USD",
          minimumFractionDigits: 0,
        }).format(value);
      }
    };
  }, [currencyCode]);

  return (
    <CurrencyContext.Provider value={{ currencyCode, setCurrencyCode, formatAmount, isLoading }}>
      {children}
    </CurrencyContext.Provider>
  );
}

export function useCurrency() {
  const context = useContext(CurrencyContext);
  if (context === undefined) {
    throw new Error("useCurrency must be used within a CurrencyProvider");
  }
  return context;
}
