import { Card, CardHeader } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { SentimentBadge } from "./SentimentBadge";
import type { TopNewsItem } from "@/lib/recommendations";

function timeAgo(iso: string): string {
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 60) return `${mins}m ago`;
  if (mins < 60 * 24) return `${Math.floor(mins / 60)}h ago`;
  return `${Math.floor(mins / 1440)}d ago`;
}

const usd = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });

function PriceChip({ n }: { n: TopNewsItem }) {
  if (n.price === null || n.change === null || n.change_pct === null) {
    return null;
  }
  const up = n.change >= 0;
  const tone = up ? "text-provenance-input-text" : "text-error";
  const sign = up ? "+" : "−";
  return (
    <span
      title={`Last close${n.price_date ? ` on ${n.price_date}` : ""}`}
      className="inline-flex shrink-0 items-center gap-2 rounded-full bg-surface-container-low px-3 py-1.5 font-body-sm text-body-sm tabular-nums"
    >
      <span className="font-medium text-tertiary-accent">{n.ticker}</span>
      <span className="text-on-surface">{usd(n.price)}</span>
      <span className={tone}>
        {sign}
        {Math.abs(n.change_pct).toFixed(2)}%
      </span>
    </span>
  );
}

export function TopNews({ items }: { items: TopNewsItem[] }) {
  if (items.length === 0) return null;
  const priceDate = items.find((i) => i.price_date)?.price_date;

  return (
    <Card>
      <CardHeader
        title="Latest news"
        icon="newspaper"
        subtitle={`Headlines on stocks in your ideas${
          priceDate
            ? ` · prices are the last close on ${priceDate}, not a reaction to the headline`
            : ""
        }`}
      />
      <ul className="mt-6 flex flex-col divide-y divide-surface-container-high">
        {items.map((n) => (
          <li
            key={n.ticker}
            className="flex flex-col gap-2 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-start sm:justify-between sm:gap-6"
          >
            <div className="flex min-w-0 flex-col gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-body-sm text-body-sm font-medium text-tertiary-accent">
                  {n.ticker}
                </span>
                <SentimentBadge sentiment={n.sentiment} />
              </div>
              {n.url ? (
                <a
                  href={n.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-title-md text-title-md leading-snug text-on-surface transition-colors hover:text-tertiary-accent"
                >
                  {n.title}
                </a>
              ) : (
                <span className="font-title-md text-title-md leading-snug text-on-surface">
                  {n.title}
                </span>
              )}
              <span className="flex flex-wrap items-center gap-1.5 font-body-sm text-body-sm text-on-surface-variant">
                <Icon name="schedule" className="text-[15px]" />
                {n.source} · {timeAgo(n.published_at)}
              </span>
            </div>
            <div className="sm:pt-1">
              <PriceChip n={n} />
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}
