"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { RefreshButton } from "./RefreshButton";
import type { DataStatus as DataStatusData } from "@/lib/recommendations";

function formatTime(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatUtc(iso: string | null): string | undefined {
  if (!iso) return undefined;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return undefined;
  return `${date.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

/**
 * Quiet status line for Trade Ideas. The old fixed two-row bar was visually
 * heavy; this keeps the same information in the page flow.
 */
export function DataStatus({ status }: { status: DataStatusData | null }) {
  const [now, setNow] = useState<Date | null>(
    status ? new Date(status.server_time) : null,
  );

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const nowIso = now ? now.toISOString() : null;

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 font-body-sm text-body-sm text-on-surface-variant">
      <span className="inline-flex items-center gap-2">
        <span className="h-2 w-2 animate-pulse rounded-full bg-tertiary-accent" />
        <span>
          Now{" "}
          <span
            suppressHydrationWarning
            title={formatUtc(nowIso)}
            className="tabular-nums text-on-surface"
          >
            {formatTime(nowIso)}
          </span>
        </span>
      </span>
      <span className="hidden h-4 w-px bg-surface-container-high sm:block" />
      <span className="inline-flex items-center gap-1.5">
        <Icon name="update" className="text-[15px]" />
        News{" "}
        <span
          suppressHydrationWarning
          title={formatUtc(status?.news_updated_at ?? null)}
          className="tabular-nums text-on-surface"
        >
          {formatTime(status?.news_updated_at ?? null)}
        </span>
        {status && status.news_count > 0 && (
          <span className="text-on-surface-variant/70">
            · {status.news_count} headlines
          </span>
        )}
      </span>
      <span className="hidden h-4 w-px bg-surface-container-high sm:block" />
      <span className="inline-flex items-center gap-1.5">
        <Icon name="auto_awesome" className="text-[15px]" />
        Sentiment{" "}
        {status?.sentiment_updated_at ? (
          <span
            suppressHydrationWarning
            title={formatUtc(status.sentiment_updated_at)}
            className="tabular-nums text-on-surface"
          >
            {formatTime(status.sentiment_updated_at)}
          </span>
        ) : (
          <span className="text-on-surface">not scored yet</span>
        )}
      </span>
      <div className="ml-auto">
        <RefreshButton />
      </div>
    </div>
  );
}
