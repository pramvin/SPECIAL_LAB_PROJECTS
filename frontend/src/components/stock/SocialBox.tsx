import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { SentimentBadge } from "@/components/ideas/SentimentBadge";
import { BlockUnavailable } from "./BlockUnavailable";
import { ModelNote } from "./ModelNote";
import type { SocialDirection, SocialRead } from "@/lib/analysis";

const DIRECTION: Record<
  SocialDirection,
  { label: string; tone: "success" | "danger" | "neutral" }
> = {
  positive: { label: "Leans positive", tone: "success" },
  neutral: { label: "Neutral", tone: "neutral" },
  negative: { label: "Leans negative", tone: "danger" },
  mixed: { label: "Mixed", tone: "neutral" },
  no_data: { label: "No data", tone: "neutral" },
};

const SOURCE_LABEL: Record<string, string> = {
  stocktwits: "StockTwits",
  reddit: "Reddit",
};

const MAX_ITEMS = 5;

/** What people post about the stock: direction, sources, and a few example posts. */
export function SocialBox({ block }: { block: SocialRead }) {
  const direction = DIRECTION[block.direction] ?? DIRECTION.no_data;
  const items = block.items.slice(0, MAX_ITEMS);

  return (
    <Card as="section">
      <CardHeader
        title="Social media"
        icon="forum"
        subtitle="Posts pulled by the backend while the analysis ran. Not a sample of all investors."
        badge={<ProvenanceBadge provenance="ai" label="Model labels" />}
        action={<Badge tone={direction.tone}>{direction.label}</Badge>}
      />

      {block.status === "unavailable" || block.status === "skipped" ? (
        <div className="mt-5">
          <BlockUnavailable status={block.status} reason={block.reason} />
        </div>
      ) : (
        <>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {Object.entries(block.sources).map(([source, info]) => (
              <span
                key={source}
                title={`Status: ${info.status}`}
                className="inline-flex items-center gap-1.5 rounded-full border border-surface-container-high bg-surface-container-low px-3 py-1 font-body-sm text-[12px] text-on-surface-variant"
              >
                {SOURCE_LABEL[source] ?? source}
                <span className="font-semibold text-on-surface">
                  {info.status === "ok"
                    ? `${info.count} ${info.count === 1 ? "post" : "posts"}`
                    : info.status}
                </span>
              </span>
            ))}
          </div>

          {block.summary && (
            <p className="mt-3 font-body-md text-body-md text-on-surface">
              {block.summary}
            </p>
          )}

          {items.length === 0 ? (
            <p className="mt-3 font-body-md text-body-md text-on-surface-variant">
              No posts were returned for this stock.
            </p>
          ) : (
            <ul className="mt-3 flex flex-col divide-y divide-surface-container-high">
              {items.map((item, i) => (
                <li
                  key={`${item.source}-${i}`}
                  className="flex flex-col gap-1 py-2.5 first:pt-0 last:pb-0"
                >
                  <span className="flex flex-wrap items-center gap-2 font-body-sm text-body-sm text-on-surface">
                    <SentimentBadge sentiment={item.sentiment} />
                    <span className="min-w-0">{item.text}</span>
                  </span>
                  <span className="flex items-center gap-2 font-body-sm text-body-sm text-on-surface-variant">
                    {SOURCE_LABEL[item.source] ?? item.source}
                    {item.url && (
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-0.5 font-medium text-tertiary-accent hover:underline"
                      >
                        Open
                        <Icon name="open_in_new" className="text-[13px]" />
                      </a>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          )}

          {block.items.length > MAX_ITEMS && (
            <p className="mt-2 font-body-sm text-body-sm text-on-surface-variant">
              Showing {MAX_ITEMS} of {block.items.length} posts.
            </p>
          )}
        </>
      )}

      <div className="mt-4">
        <ModelNote />
      </div>
    </Card>
  );
}
