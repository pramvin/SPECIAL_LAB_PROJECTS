import { Badge } from "@/components/ui/Badge";
import { SectionLabel } from "@/components/ui/Card";
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
    <section className="flex flex-col gap-space-md rounded-md border border-outline-variant bg-surface-container-lowest p-space-md">
      <div className="flex flex-wrap items-center gap-space-sm">
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
            <div className="flex flex-col gap-space-xs">
              <SectionLabel>Sentiment direction (scored headlines)</SectionLabel>
              <div
                className="flex h-3 overflow-hidden rounded-full"
                role="img"
                aria-label={`Positive ${pct(dist.positive, total)}%, neutral ${pct(dist.neutral, total)}%, negative ${pct(dist.negative, total)}%`}
              >
                <div
                  className="bg-primary-fixed-dim"
                  style={{ width: `${pct(dist.positive, total)}%` }}
                />
                <div
                  className="bg-outline-variant"
                  style={{ width: `${pct(dist.neutral, total)}%` }}
                />
                <div
                  className="bg-error/70"
                  style={{ width: `${pct(dist.negative, total)}%` }}
                />
              </div>
              <div className="flex flex-wrap gap-space-md font-label-code text-label-code text-on-surface-variant">
                <span>Positive {pct(dist.positive, total)}%</span>
                <span>Neutral {pct(dist.neutral, total)}%</span>
                <span>Negative {pct(dist.negative, total)}%</span>
              </div>
              <p className="font-body-sm text-body-sm text-on-surface-variant">
                From {total} scored headlines · Google News
              </p>
            </div>
          ) : (
            <div className="flex items-start gap-space-sm rounded-md bg-surface-container-low p-space-sm font-body-sm text-body-sm text-on-surface-variant">
              <Icon name="info" className="mt-0.5 text-[18px]" />
              <span>
                Real headlines, but sentiment is not scored yet. The scoring
                step (Laya/LLM) has not run on these headlines, so no
                positive/neutral/negative split is shown.
              </span>
            </div>
          )}

          <div className="flex flex-col gap-space-xs">
            <SectionLabel>Headlines picked by the system</SectionLabel>
            <ul className="flex flex-col divide-y divide-surface-container-high">
              {items.map((h) => (
                <li
                  key={h.url || h.title}
                  className="flex flex-col gap-1 py-space-sm first:pt-0 last:pb-0"
                >
                  <a
                    href={h.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-body-md text-body-md text-on-surface hover:text-tertiary-accent hover:underline"
                  >
                    {h.title}
                  </a>
                  <div className="flex flex-wrap items-center gap-space-xs font-label-code text-label-code text-on-surface-variant">
                    <span>{h.source}</span>
                    <span>·</span>
                    <span>{h.published_at.slice(0, 10)}</span>
                    <SentimentBadge sentiment={h.sentiment} />
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <p className="font-body-sm text-body-sm text-on-surface-variant">
            Headlines are real and come from Google News. Sentiment labels, when
            shown, are AI-generated and not validated on our own headlines. This
            does not change the score of this stock.
          </p>
        </>
      )}
    </section>
  );
}
