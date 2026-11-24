"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardHeader } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { SentimentBadge } from "./SentimentBadge";
import type { LatestNews as LatestNewsData } from "@/lib/recommendations";

const REFRESH_MS = 60_000;

const usd = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });

function timeAgo(iso: string): string {
  const mins = Math.max(
    0,
    Math.round((Date.now() - new Date(iso).getTime()) / 60000),
  );
  if (mins < 60) return `${mins}m ago`;
  if (mins < 60 * 24) return `${Math.floor(mins / 60)}h ago`;
  return `${Math.floor(mins / 1440)}d ago`;
}

function Change({ item }: { item: LatestNewsData["items"][number] }) {
  if (item.price === null) return null;
  const up = (item.change_pct ?? item.change ?? 0) >= 0;
  return (
    <span
      title={item.price_date ? `Last close on ${item.price_date}` : "Last close"}
      className="flex flex-col items-end tabular-nums"
    >
      <span className="font-body-md text-body-md font-semibold text-on-surface">
        {usd(item.price)}
      </span>
      {item.change !== null && item.change_pct !== null && (
        <span
          className={`font-body-sm text-body-sm ${up ? "text-green-700" : "text-error"}`}
        >
          {up ? "+" : "−"}
          {usd(Math.abs(item.change))} ({up ? "+" : "−"}
          {Math.abs(item.change_pct).toFixed(2)}%)
        </span>
      )}
    </span>
  );
}

/**
 * Latest headlines for the served stocks. Refetches itself every minute so the
 * home page stays fresh without a full reload; no rows are invented when the
 * endpoint fails.
 */
export function LatestNews({ initial }: { initial: LatestNewsData | null }) {
  const [data, setData] = useState(initial);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const id = setInterval(async () => {
      try {
        const res = await fetch("/api/latest-news?limit=10", {
          cache: "no-store",
        });
        if (!res.ok) throw new Error(`Request failed (${res.status})`);
        const next = (await res.json()) as LatestNewsData;
        if (!cancelled) {
          setData(next);
          setFailed(false);
        }
      } catch {
        if (!cancelled) setFailed(true);
      }
    }, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <Card>
      <CardHeader
        title="Latest news"
        icon="newspaper"
        subtitle="Newest headlines for the stocks in your ideas. Prices are the last daily close, not a reaction to the headline. Refreshes every minute."
      />

      {data === null ? (
        <p className="mt-6 font-body-md text-body-md text-error">
          Could not load the latest news. Is the backend running?
        </p>
      ) : data.items.length === 0 ? (
        <p className="mt-6 font-body-md text-body-md text-on-surface-variant">
          No headlines yet. They appear as soon as the news refresh finds some.
        </p>
      ) : (
        <ul className="mt-6 flex flex-col divide-y divide-surface-container-high">
          {data.items.map((n) => (
            <li
              key={n.url || `${n.ticker}-${n.title}`}
              className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-start sm:justify-between sm:gap-6"
            >
              <div className="flex min-w-0 flex-col gap-1">
                <span className="font-title-md text-title-md text-on-surface">
                  {n.title}
                </span>
                <span className="flex flex-wrap items-center gap-2 font-body-sm text-body-sm text-on-surface-variant">
                  <SentimentBadge sentiment={n.sentiment} />
                  {n.source} ·{" "}
                  <span suppressHydrationWarning>{timeAgo(n.published_at)}</span>
                </span>
              </div>

              <div className="flex shrink-0 items-center gap-3">
                <Change item={n} />
                <Link
                  href={`/stock/${encodeURIComponent(n.ticker)}?h=1w`}
                  className="rounded-full border border-surface-container-high bg-white px-3 py-1.5 font-label-code text-label-code font-semibold text-on-surface hover:bg-surface-container-low"
                >
                  {n.ticker}
                </Link>
                {n.url && (
                  <a
                    href={n.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`Open this headline at ${n.source} in a new tab`}
                    title={`Open at ${n.source}`}
                    className="inline-flex items-center gap-1 rounded-full border border-surface-container-high bg-white px-3 py-1.5 font-body-sm text-body-sm font-semibold text-on-surface hover:bg-surface-container-low"
                  >
                    Source
                    <Icon name="open_in_new" className="text-[14px]" />
                  </a>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {failed && data !== null && (
        <p className="mt-4 font-body-sm text-body-sm text-error">
          Could not refresh the news just now. Showing the last headlines.
        </p>
      )}
    </Card>
  );
}
