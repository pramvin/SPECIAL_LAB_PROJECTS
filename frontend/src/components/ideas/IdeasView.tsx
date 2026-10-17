import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Card, SectionLabel } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { NoticeBanner } from "@/components/ui/NoticeBanner";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { SentimentBadge } from "./SentimentBadge";
import { SocialSentiment } from "./SocialSentiment";
import { TopNews } from "./TopNews";
import {
  HORIZONS,
  type TopNewsItem,
  type Horizon,
  type LlmAnalysis,
  type Recommendation,
} from "@/lib/recommendations";

const usd = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });

const SECTOR_LABEL: Record<string, string> = {
  tech: "Technology",
  healthcare: "Healthcare",
  finance: "Finance",
  energy: "Energy",
  consumer: "Consumer",
};

function Level({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="flex flex-col">
      <SectionLabel>{label}</SectionLabel>
      <span className={`font-title-md text-title-md ${tone ?? "text-on-surface"}`}>
        {value}
      </span>
    </div>
  );
}

// The model sometimes writes "Headline [1091]" or "Headlines 12 and 15" in a reason; turn those ids into links.
const ID_REF = /(\[\d+\]|\bHeadlines?\s+\d+(?:\s*(?:,|and)\s*\d+)*)/;

function ReasonText({ text, cited }: { text: string; cited: LlmAnalysis["cited"] }) {
  const byId = new Map(cited.map((c) => [String(c.id), c]));
  return (
    <>
      {text.split(ID_REF).map((part, i) => {
        if (i % 2 === 0) return part;
        const links = (part.match(/\d+/g) ?? []).map((id) => byId.get(id));
        if (links.every((c) => !c)) return part;
        return (
          <span key={i}>
            {links.map((c, k) =>
              c ? (
                <a
                  key={c.id}
                  href={c.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={c.title}
                  className="text-tertiary-accent hover:underline"
                >
                  [{k + 1}]
                </a>
              ) : null,
            )}
          </span>
        );
      })}
    </>
  );
}

function LlmBlock({ llm }: { llm: LlmAnalysis }) {
  const dir = { up: "Up", down: "Down", none: "No clear view" }[llm.direction];
  return (
    <div className="mt-space-lg flex flex-col gap-space-xs">
      <div className="flex flex-wrap items-center gap-space-xs">
        <SectionLabel>AI reading of the news</SectionLabel>
        <ProvenanceBadge provenance="ai" label="AI · Not validated" />
      </div>
      <p className="font-body-sm text-body-sm text-on-surface">
        {dir}
        {llm.direction !== "none" && ` · ${llm.magnitude} · confidence ${Math.round(llm.confidence * 100)}%`}
        <span className="text-on-surface-variant"> · {llm.model}, {llm.as_of}. Does not change the score.</span>
      </p>
      <ul className="list-disc pl-5 font-body-sm text-body-sm text-on-surface">
        {llm.reasons.map((x) => (
          <li key={x}>
            <ReasonText text={x} cited={llm.cited} />
          </li>
        ))}
      </ul>
      {llm.caveats.length > 0 && (
        <ul className="list-disc pl-5 font-body-sm text-body-sm text-on-surface-variant">
          {llm.caveats.map((x) => (
            <li key={x}>
              <ReasonText text={x} cited={llm.cited} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function IdeaCard({ r, rank }: { r: Recommendation; rank: number }) {
  return (
    <Card as="article" className="flex flex-col gap-space-md">
      <div className="flex flex-wrap items-start justify-between gap-space-sm">
        <div className="flex items-center gap-space-sm">
          <span className="flex h-9 w-9 items-center justify-center rounded-md bg-surface-container-low font-label-code text-label-code text-on-surface-variant">
            {rank}
          </span>
          <div className="flex flex-col">
            <div className="flex items-center gap-space-xs">
              <h2 className="font-headline-sm text-headline-sm text-on-surface">
                {r.ticker}
              </h2>
              <Badge tone="success" icon="trending_up">
                {r.action}
              </Badge>
              {r.matches_interest && <Badge tone="info">Your sector</Badge>}
            </div>
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              {r.name} · {SECTOR_LABEL[r.sector] ?? r.sector}
            </span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className="font-title-md text-title-md text-on-surface">
            Score {r.score}
          </span>
          {r.is_example ? (
            <ProvenanceBadge provenance="example" />
          ) : (
            <ProvenanceBadge provenance="ai" label="Rule-based" />
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-space-md sm:grid-cols-4">
        <Level label="Entry" value={usd(r.entry)} />
        <Level label="Stop" value={usd(r.stop)} tone="text-error" />
        <Level label="Target" value={usd(r.target)} tone="text-primary" />
        <Level label="Position" value={`${r.position_pct}% of capital`} />
      </div>
      <p className="font-body-sm text-body-sm text-on-surface-variant">
        Upside {r.upside_pct}% · Stop {r.stop_distance_pct}% below entry · If the
        stop is hit you lose about {r.loss_at_stop_pct}% of your capital.
      </p>

      <details open className="group rounded-md bg-surface-container-low p-space-md">
        <summary className="flex cursor-pointer items-center gap-space-xs font-title-md text-title-md text-on-surface">
          <Icon name="expand_more" className="text-[20px] transition-transform group-open:rotate-180" />
          Why this stock · related news
        </summary>
        <div className="mt-space-md grid gap-space-lg sm:grid-cols-2">
          <div className="flex flex-col gap-space-xs">
            <SectionLabel>Reasons</SectionLabel>
            <ul className="list-disc pl-5 font-body-sm text-body-sm text-on-surface">
              {r.reasons.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          </div>
          <div className="flex flex-col gap-space-xs">
            <SectionLabel>News</SectionLabel>
            <ul className="flex flex-col gap-space-xs font-body-sm text-body-sm text-on-surface">
              {r.news.length === 0 && (
                <li className="text-on-surface-variant">
                  No recent headlines found.
                </li>
              )}
              {r.news.map((n) => (
                <li key={n.title}>
                  {n.url ? (
                    <a
                      href={n.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-tertiary-accent hover:underline"
                    >
                      {n.title}
                    </a>
                  ) : (
                    n.title
                  )}
                  <span className="mt-0.5 flex flex-wrap items-center gap-space-xs text-on-surface-variant">
                    <SentimentBadge sentiment={n.sentiment} />
                    {n.source}
                    {n.published ? ` · ${n.published}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
        {r.llm && <LlmBlock llm={r.llm} />}
        <div className="mt-space-lg">
          <SocialSentiment ticker={r.ticker} priceScore={r.score} />
        </div>
      </details>
    </Card>
  );
}

export function IdeasView({
  horizon,
  items,
  topNews,
}: {
  horizon: Horizon;
  items: Recommendation[] | null;
  topNews: TopNewsItem[];
}) {
  return (
    <div className="flex flex-col gap-space-lg">
      <div className="flex flex-col gap-1">
        <h1 className="font-headline-md text-headline-md text-on-surface">
          Trade ideas
        </h1>
        <p className="font-body-md text-body-md text-on-surface-variant">
          S&amp;P 500 stocks, buy-only (no shorting, no futures), ranked for your
          holding period and risk profile.
        </p>
      </div>

      <TopNews items={topNews} />

      <nav aria-label="Holding period" className="flex gap-space-xs">
        {HORIZONS.map((h) => (
          <Link
            key={h.value}
            href={`/?h=${h.value}`}
            aria-current={h.value === horizon ? "page" : undefined}
            className={`rounded-md px-space-md py-2 font-body-sm text-body-sm font-medium transition-colors ${
              h.value === horizon
                ? "bg-primary-container text-on-primary"
                : "bg-surface-container-low text-on-surface hover:bg-surface-container-high"
            }`}
          >
            {h.label}
          </Link>
        ))}
      </nav>

      {items?.some((r) => r.is_example) ? (
        <NoticeBanner icon="info" tone="warning" title="Example data only">
          Prices, scores and news below are placeholders until the live data
          pipeline is connected. This is not investment advice and nothing here
          is a guaranteed outcome.
        </NoticeBanner>
      ) : (
        <NoticeBanner
          icon="info"
          tone="neutral"
          title={`Based on daily prices as of ${items?.[0]?.as_of ?? "—"}`}
        >
          Ideas come from simple price-trend rules and have not been backtested.
          Headlines are shown for context only and do not affect the score; fundamentals are not connected yet. This is not investment
          advice and nothing here is a guaranteed outcome.
        </NoticeBanner>
      )}

      {items === null && (
        <p className="font-body-md text-body-md text-error">
          Could not load trade ideas. Is the backend running?
        </p>
      )}
      {items?.length === 0 && (
        <p className="font-body-md text-body-md text-on-surface-variant">
          No ideas for this holding period right now.
        </p>
      )}
      {items?.map((r, i) => (
        <IdeaCard key={r.ticker} r={r} rank={i + 1} />
      ))}
    </div>
  );
}
