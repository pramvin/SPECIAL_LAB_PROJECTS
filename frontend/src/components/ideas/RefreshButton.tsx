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
      className={`inline-flex h-8 w-8 shrink-0 items-center justify-center gap-1.5 rounded-md bg-primary-container px-0 font-medium text-on-primary transition-all duration-200 hover:bg-primary-hover active:scale-95 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto sm:px-space-md ${className}`}
    >
      <Icon
        name="refresh"
        className={`text-[18px] ${pending ? "animate-spin" : ""}`}
      />
      <span className="hidden sm:inline">
        {pending ? "Refreshing…" : "Refresh"}
      </span>
    </button>
  );
}
