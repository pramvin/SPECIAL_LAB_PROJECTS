"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { Icon } from "@/components/ui/Icon";

/**
 * Refreshes the Trade Ideas server render so recommendations, top news, and
 * news sentiment are all re-fetched (all reads are no-store).
 */
export function RefreshButton({ className = "" }: { className?: string }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  return (
    <button
      type="button"
      onClick={() => startTransition(() => router.refresh())}
      disabled={pending}
      aria-label="Refresh all trade ideas data"
      title="Re-fetch recommendations, top news and news sentiment"
      className={`inline-flex h-9 items-center justify-center gap-2 rounded-full bg-surface-container-low px-4 font-body-sm text-body-sm font-medium text-on-surface transition-colors hover:bg-surface-container-high disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
    >
      <Icon
        name="refresh"
        className={`text-[18px] ${pending ? "animate-spin" : ""}`}
      />
      <span>{pending ? "Refreshing…" : "Refresh"}</span>
    </button>
  );
}
