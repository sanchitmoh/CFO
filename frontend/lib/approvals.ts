import type { ApprovalPolicy, Transaction } from "./types";

function normalizeCategory(value?: string | null) {
  return (value ?? "").trim().replace(/\s+/g, " ").toLocaleLowerCase();
}

export function findMatchingPolicy(
  policies: ApprovalPolicy[],
  transaction: Pick<Transaction, "amount" | "category" | "type">,
) {
  if (transaction.type !== "expense") {
    return null;
  }

  const normalizedTransactionCategory = normalizeCategory(transaction.category);

  return [...policies]
    .filter((policy) => policy.is_active)
    .sort((left, right) => right.min_amount - left.min_amount)
    .find((policy) => {
      const withinMin = transaction.amount >= policy.min_amount;
      const withinMax = policy.max_amount == null || transaction.amount <= policy.max_amount;
      if (!withinMin || !withinMax) {
        return false;
      }

      if (!policy.categories.length) {
        return true;
      }

      return policy.categories.some(
        (category) => normalizeCategory(category) === normalizedTransactionCategory,
      );
    }) ?? null;
}

export function parsePolicyCategories(input: string) {
  return Array.from(
    new Set(
      input
        .split(",")
        .map((value) => value.trim().replace(/\s+/g, " "))
        .filter(Boolean),
    ),
  );
}
