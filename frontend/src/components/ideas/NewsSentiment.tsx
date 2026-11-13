import { Badge } from "@/components/ui/Badge";
import { SectionLabel } from "@/components/ui/Card";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import type { TickerNewsSentiment } from "@/lib/recommendations";

const SMALL_SAMPLE = 5;

function pct(part: number, total: number): number {
  return total > 0 ? Math.round((part / total) * 100) : 0;
}

/**
 * Summary of how the ML model labeled this ticker's Google News headlines
 * (`news_scores`). The headlines themselves are listed once, in the card's
 * News column, so this panel only shows the split. It renders nothing when
 * the ticker has no scored headlines: no empty frame, no invented labels.
 */
export function NewsSentiment({
  ticker,
  data,
}: {
  ticker: string;
  data?: TickerNewsSentiment | null;
}) {
  const dist = data?.distribution ?? null;
  const total = dist?.scored ?? 0;
  if (!dist || total === 0) return null;

  const parts = [
    {
      key: "positive",
      label: "Positive",
      count: dist.positive,
      bar: "bg-provenance-input-text/80",
    },
    {
      key: "neutral",
      label: "Neutral",
      count: dist.neutral,
      bar: "bg-outline-variant",
    },
    {
      key: "negative",
      label: "Negative",
      count: dist.negative,
      bar: "bg-error/80",
    },
  ] as const;

  return (
    <section className="flex flex-col gap-4 rounded-[20px] bg-surface-container-low p-4 md:p-5">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-title-md text-title-md text-on-surface">
          News mood · {ticker}
        </h3>
        <Badge tone="neutral" icon="public">
          Google News
        </Badge>
        <ProvenanceBadge provenance="ai" label="ML · Not validated" />
      </div>

      <div className="flex flex-col gap-2">
        <SectionLabel>How the headlines were labeled</SectionLabel>
        <div
          className="flex h-2.5 overflow-hidden rounded-full bg-surface-container-high"
          role="img"
          aria-label={parts
            .map((p) => `${p.label} ${pct(p.count, total)}%`)
            .join(", ")}
        >
          {parts.map((p) => (
            <div
              key={p.key}
              className={p.bar}
              style={{ width: `${(p.count / total) * 100}%` }}
            />
          ))}
        </div>
        <ul className="flex flex-wrap gap-x-4 gap-y-1 font-body-sm text-body-sm text-on-surface-variant">
          {parts.map((p) => (
            <li key={p.key} className="flex items-center gap-1.5">
              <span
                aria-hidden
                className={`inline-block size-2.5 rounded-full ${p.bar}`}
              />
              {p.label} {pct(p.count, total)}% ({p.count})
            </li>
          ))}
        </ul>
      </div>

      <p className="font-body-sm text-body-sm text-on-surface-variant">
        {total < SMALL_SAMPLE
          ? `Only ${total} scored headline${total === 1 ? "" : "s"} so far, so treat this as a rough guide. `
          : `From ${total} scored headlines. `}
        Labels come from an ML model trained on positive/negative word lists and
        have not been checked against human labels. They do not change the
        score of this stock.
      </p>
    </section>
  );
}
