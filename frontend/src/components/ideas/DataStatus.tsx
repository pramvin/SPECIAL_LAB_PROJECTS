"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { RefreshButton } from "./RefreshButton";
import type { DataStatus as DataStatusData } from "@/lib/recommendations";

function sameLocalDay(d: Date): boolean {
  const n = new Date();
  return (
    d.getFullYear() === n.getFullYear() &&
    d.getMonth() === n.getMonth() &&
    d.getDate() === n.getDate()
  );
}

function fmtLocal(iso: string | null, withSeconds = false): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    ...(withSeconds ? { second: "2-digit" } : {}),
    hour12: false,
    timeZoneName: "short",
  });
}

function fmtUtc(iso: string | null, withSeconds = false): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const t = d.toISOString();
  const localDay = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate(),
  ).padStart(2, "0")}`;
  const time = `${t.slice(11, withSeconds ? 19 : 16)} UTC`;
  // Show the date only when UTC falls on a different calendar day.
  return localDay === t.slice(0, 10)
    ? time
    : `${t.slice(5, 10).replace("-", "/")} ${time}`;
}

/** Compact variant for phones: omits the date when it is today. */
function fmtLocalCompact(iso: string | null, withSeconds = false): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const time = d.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    ...(withSeconds ? { second: "2-digit" } : {}),
    hour12: false,
    timeZoneName: "short",
  });
  if (sameLocalDay(d)) return time;
  const date = d.toLocaleDateString(undefined, {
    month: "2-digit",
    day: "2-digit",
  });
  return `${date} ${time}`;
}

function fmtUtcCompact(iso: string | null, withSeconds = false): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const t = d.toISOString();
  const time = `${t.slice(11, withSeconds ? 19 : 16)} UTC`;
  const today = new Date().toISOString().slice(0, 10);
  return t.slice(0, 10) === today
    ? time
    : `${t.slice(5, 10).replace("-", "/")} ${time}`;
}

function TimeBlock({
  iso,
  seconds,
}: {
  iso: string | null;
  seconds?: boolean;
}) {
  return (
    <>
      <span className="inline-flex items-center gap-1.5 whitespace-nowrap sm:hidden">
        <span className="tabular-nums text-on-surface" suppressHydrationWarning>
          {fmtLocalCompact(iso, seconds)}
        </span>
        <span className="tabular-nums opacity-70" suppressHydrationWarning>
          · {fmtUtcCompact(iso, seconds)}
        </span>
      </span>
      <span className="hidden items-center gap-1.5 whitespace-nowrap sm:inline-flex">
        <span className="tabular-nums text-on-surface" suppressHydrationWarning>
          {fmtLocal(iso, seconds)}
        </span>
        <span className="tabular-nums opacity-70" suppressHydrationWarning>
          ({fmtUtc(iso, seconds)})
        </span>
      </span>
    </>
  );
}

/**
 * Fixed status + refresh bar.
 * Phones: row 1 = Now + Refresh, row 2 = News + Sentiment (full width).
 * sm+: single row with Refresh pushed to the right.
 * Measures itself so the in-flow spacer always reserves the right height.
 */
export function DataStatus({ status }: { status: DataStatusData | null }) {
  const [now, setNow] = useState<Date | null>(
    status ? new Date(status.server_time) : null,
  );
  const barRef = useRef<HTMLDivElement>(null);
  const [barHeight, setBarHeight] = useState(68);

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const el = barRef.current;
    if (!el) return;
    const observer = new ResizeObserver(() => {
      setBarHeight(el.getBoundingClientRect().height);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const nowIso = now ? now.toISOString() : null;

  return (
    <>
      <div
        ref={barRef}
        className="fixed inset-x-0 top-16 z-30 border-b border-surface-container-high bg-surface lg:left-72 lg:top-16"
      >
        <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-1 px-space-md py-space-sm font-label-code text-[10px] leading-4 text-on-surface-variant sm:flex-row sm:flex-wrap sm:items-center sm:gap-space-md sm:px-space-lg sm:leading-normal lg:px-space-xl">
          {/* Phone row 1: Now + Refresh. On sm+, contents flatten into one row. */}
          <div className="flex items-center gap-space-sm sm:contents">
            <span className="flex min-w-0 flex-1 items-center gap-1.5 whitespace-nowrap sm:flex-none">
              <span className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-primary-container" />
              <span>Now</span>
              <TimeBlock iso={nowIso} seconds />
            </span>
            <div className="ml-auto sm:hidden">
              <RefreshButton />
            </div>
          </div>

          {/* Phone row 2: News + Sentiment, with the full width available. */}
          <div className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 sm:contents">
            <span className="inline-flex flex-wrap items-center gap-x-1.5 gap-y-0.5 sm:flex-nowrap sm:whitespace-nowrap">
              <Icon name="update" className="shrink-0 text-[14px]" />
              <span>
                News<span className="hidden sm:inline"> updated</span>
              </span>
              <TimeBlock iso={status?.news_updated_at ?? null} />
              {status && status.news_count > 0 && (
                <span className="hidden sm:inline">
                  ({status.news_count} headlines)
                </span>
              )}
            </span>

            <span className="inline-flex items-center gap-1.5 sm:shrink-0 sm:whitespace-nowrap">
              <Icon
                name="auto_awesome"
                className="hidden shrink-0 text-[14px] sm:inline"
              />
              <span>
                Sent<span className="hidden sm:inline">iment</span>
              </span>
              {status?.sentiment_updated_at ? (
                <TimeBlock iso={status.sentiment_updated_at} />
              ) : (
                <span className="text-on-surface">
                  <span className="sm:hidden">unscored</span>
                  <span className="hidden sm:inline">not scored yet</span>
                </span>
              )}
            </span>
          </div>

          {/* Desktop / tablet: Refresh stays at the far right of the single row. */}
          <div className="hidden sm:ml-auto sm:block">
            <RefreshButton />
          </div>
        </div>
      </div>

      {/* Reserves space in the page flow; height follows the fixed bar. */}
      <div aria-hidden style={{ height: barHeight }} />
    </>
  );
}
