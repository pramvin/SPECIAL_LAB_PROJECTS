import { Card, CardHeader } from "@/components/ui/Card";
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
  const tone = up ? "text-primary" : "text-error";
  const sign = up ? "+" : "−";
  return (
    <span
      title={`Last close${n.price_date ? ` on ${n.price_date}` : ""}`}
      className="inline-flex shrink-0 items-center gap-space-xs rounded-md border border-outline-variant bg-surface-container-low px-space-sm py-1 font-label-code text-label-code"
    >
      <span className="font-semibold text-tertiary-accent">{n.ticker}</span>
      <span className="text-on-surface">{usd(n.price)}</span>
      <span className={tone}>
        {sign}${Math.abs(n.change).toFixed(2)} ({sign}
        {Math.abs(n.change_pct).toFixed(2)}%)
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
        title="Top news"
        icon="newspaper"
        subtitle={`Latest headlines on stocks in your ideas${priceDate ? ` · prices are the last close, ${priceDate}, and are not a reaction to the headline` : ""}. AI labels are not validated yet.`}
      />
      <ul className="mt-space-md flex flex-col divide-y divide-surface-container-high">
        {items.map((n) => (
          <li
            key={n.ticker}
            className="flex flex-col gap-space-xs py-space-sm first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between sm:gap-space-md"
          >
            <div className="flex min-w-0 flex-col">
              {n.url ? (
                <a
                  href={n.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-title-md text-title-md text-on-surface hover:underline"
                >
                  {n.title}
                </a>
              ) : (
                <span className="font-title-md text-title-md text-on-surface">
                  {n.title}
                </span>
              )}
              <span className="mt-0.5 flex flex-wrap items-center gap-space-xs font-body-sm text-body-sm text-on-surface-variant">
                <SentimentBadge sentiment={n.sentiment} />
                {n.source} · {timeAgo(n.published_at)}
              </span>
            </div>
            <PriceChip n={n} />
          </li>
        ))}
      </ul>
    </Card>
  );
}
