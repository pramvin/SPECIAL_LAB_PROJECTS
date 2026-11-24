import { Card, CardHeader } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { BlockUnavailable } from "./BlockUnavailable";
import { ModelNote } from "./ModelNote";
import { SentimentBadge } from "@/components/ideas/SentimentBadge";
import type { NewsRead } from "@/lib/analysis";

function shortDate(iso: string) {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

/** The 3 to 5 newest headlines used by the analysis, with their source links. */
export function NewsList({ block }: { block: NewsRead }) {
  const items = block.items.slice(0, 5);
  return (
    <Card as="section">
      <CardHeader
        title="Latest news"
        icon="newspaper"
        subtitle="Headlines from the last 7 days that the analysis used."
        badge={<ProvenanceBadge provenance="ai" label="Model labels" />}
      />

      {block.status === "unavailable" ? (
        <div className="mt-5">
          <BlockUnavailable status="unavailable" reason={block.reason} />
        </div>
      ) : items.length === 0 ? (
        <p className="mt-5 font-body-md text-body-md text-on-surface-variant">
          No recent headlines were found for this stock.
        </p>
      ) : (
        <ul className="mt-5 flex flex-col divide-y divide-surface-container-high">
          {items.map((n) => (
            <li
              key={n.url || n.title}
              className="flex flex-col gap-2 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-start sm:justify-between sm:gap-6"
            >
              <div className="flex min-w-0 flex-col gap-1">
                <span className="font-title-md text-title-md text-on-surface">
                  {n.title}
                </span>
                <span className="flex flex-wrap items-center gap-2 font-body-sm text-body-sm text-on-surface-variant">
                  <SentimentBadge sentiment={n.sentiment} />
                  {n.source}
                  {shortDate(n.published_at) && <> · {shortDate(n.published_at)}</>}
                </span>
              </div>
              {n.url && (
                <a
                  href={n.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`Open this headline at ${n.source} in a new tab`}
                  title={`Open at ${n.source}`}
                  className="inline-flex w-fit shrink-0 items-center gap-1 rounded-full border border-surface-container-high bg-white px-3 py-1.5 font-body-sm text-body-sm font-semibold text-on-surface hover:bg-surface-container-low"
                >
                  Source
                  <Icon name="open_in_new" className="text-[14px]" />
                </a>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4">
        <ModelNote />
      </div>
    </Card>
  );
}
