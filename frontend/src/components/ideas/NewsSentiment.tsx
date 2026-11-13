import { Badge } from "@/components/ui/Badge";
import { Icon } from "@/components/ui/Icon";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { SentimentBadge } from "./SentimentBadge";
import type { TickerNewsSentiment } from "@/lib/recommendations";

function pct(part: number, total: number): number {
  return total > 0 ? Math.round((part / total) * 100) : 0;
}

/**
 * Real news for a ticker, from the Google News pipeline (`news_items`).
 * Sentiment is shown only when the scoring model has produced `news_scores`;
 * otherwise the panel says so and does not invent labels.
 */
export function NewsSentiment({
  ticker,
  data,
}: {
  ticker: string;
  data?: TickerNewsSentiment | null;
}) {
  const items = data?.items ?? [];
  const dist = data?.distribution ?? null;
  const total = dist?.scored ?? 0;

  return (
    <section className="flex flex-col gap-5 rounded-[20px] bg-surface-container-low p-5 md:p-6">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-title-md text-title-md text-on-surface">
          News sentiment · {ticker}
        </h3>
        <Badge tone="neutral" icon="public">
          Google News
        </Badge>
        {dist && <ProvenanceBadge provenance="ai" label="AI · Not validated" />}
      </div>

      {items.length === 0 ? (
        <p className="font-body-sm text-body-sm text-on-surface-variant">
          No recent headlines for {ticker}.
        </p>
      ) : (
        <>
          {dist ? (
            <div className="flex flex-col gap-3">
              <span className="font-body-sm text-body-sm font-medium text-on-surface-variant">
                Sentiment direction ({total} scored headlines)
              </span>
              <div
                className="flex h-2 overflow-hidden rounded-full bg-surface-container-high"
                role="img"
                aria-label={`Positive ${pct(dist.positive, total)}%, neutral ${pct(dist.neutral, total)}%, negative ${pct(dist.negative, total)}%`}
              >
                <div
                  className="bg-primary-container"
                  style={{ width: `${pct(dist.positive, total)}%` }}
                />
                <div
                  className="bg-surface-container-highest"
                  style={{ width: `${pct(dist.neutral, total)}%` }}
                />
                <div
                  className="bg-error/80"
                  style={{ width: `${pct(dist.negative, total)}%` }}
                />
              </div>
              <div className="flex flex-wrap gap-x-5 gap-y-1 font-body-sm text-body-sm text-on-surface-variant">
                <span>Positive {pct(dist.positive, total)}%</span>
                <span>Neutral {pct(dist.neutral, total)}%</span>
                <span>Negative {pct(dist.negative, total)}%</span>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-3 rounded-xl bg-surface-container-lowest p-4 font-body-sm text-body-sm text-on-surface-variant">
              <Icon name="info" className="mt-0.5 text-[18px]" />
              <span>
                Real headlines, but sentiment is not scored yet. The scoring
                step (Laya/LLM) has not run on these headlines, so no
                positive/neutral/negative split is shown.
              </span>
            </div>
          )}

          <div className="flex flex-col gap-1">
            <span className="font-body-sm text-body-sm font-medium text-on-surface-variant">
              Headlines picked by the system
            </span>
            <ul className="flex flex-col divide-y divide-surface-container-high">
              {items.map((h) => (
                <li
                  key={h.url || h.title}
                  className="flex flex-col gap-1 py-3 first:pt-1 last:pb-0"
                >
                  <a
                    href={h.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-body-md text-body-md leading-snug text-on-surface hover:text-tertiary-accent"
                  >
                    {h.title}
                  </a>
                  <div className="flex flex-wrap items-center gap-2 font-body-sm text-body-sm text-on-surface-variant">
                    <span>{h.source}</span>
                    <span>·</span>
                    <span>{h.published_at.slice(0, 10)}</span>
                    <SentimentBadge sentiment={h.sentiment} />
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </section>
  );
}
