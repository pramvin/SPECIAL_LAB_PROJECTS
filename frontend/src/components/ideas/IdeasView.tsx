import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Card, SectionLabel } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { NoticeBanner } from "@/components/ui/NoticeBanner";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { SentimentBadge } from "./SentimentBadge";
import { NewsSentiment } from "./NewsSentiment";
import { TopNews } from "./TopNews";
import { DataStatus as DataStatusBar } from "./DataStatus";
import {
  HORIZONS,
  type TopNewsItem,
  type Horizon,
  type LlmAnalysis,
  type Quote,
  type Recommendation,
  type TickerNewsSentiment,
  type DataStatus as DataStatusData,
} from "@/lib/recommendations";

const usd = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });

const SECTOR_LABEL: Record<string, string> = {
  tech: "Technology",
  communication: "Communication",
  healthcare: "Healthcare",
  finance: "Finance",
  energy: "Energy",
  consumer_discretionary: "Consumer Discretionary",
  consumer_staples: "Consumer Staples",
  industrials: "Industrials",
  materials: "Materials",
  real_estate: "Real Estate",
  utilities: "Utilities",
};

const CHART_INTERVAL: Record<Horizon, { value: string; label: string }> = {
  "1w": { value: "240", label: "4-hour" },
  "1m": { value: "1D", label: "daily" },
  "3m": { value: "1D", label: "daily" },
};

function quoteTime(iso: string) {
  return (
    new Date(iso).toLocaleString("en-US", {
      timeZone: "America/New_York",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }) + " ET"
  );
}

function tradingViewChartUrl(ticker: string, horizon: Horizon) {
  const params = new URLSearchParams({
    symbol: ticker,
    interval: CHART_INTERVAL[horizon].value,
  });
  return `https://www.tradingview.com/chart/?${params.toString()}`;
}

function Level({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="font-body-sm text-body-sm text-on-surface-variant">
        {label}
      </span>
      <span
        className={`font-metric-md text-metric-md tabular-nums ${tone ?? "text-on-surface"}`}
      >
        {value}
      </span>
    </div>
  );
}

// The model sometimes writes "Headline [1091]" or "Headlines 12 and 15" in a reason; turn those ids into links.
const ID_REF = /(\[\d+\]|\bHeadlines?\s+\d+(?:\s*(?:,|and)\s*\d+)*)/;

function ReasonText({
  text,
  cited,
}: {
  text: string;
  cited: LlmAnalysis["cited"];
}) {
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
    <div className="flex flex-col gap-3 rounded-[20px] bg-surface-container-low p-5 md:p-6">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-title-md text-title-md text-on-surface">
          AI reading of the news
        </span>
        <ProvenanceBadge provenance="ai" label="AI · Not validated" />
      </div>
      <p className="font-body-sm text-body-sm text-on-surface">
        {dir}
        {llm.direction !== "none" &&
          ` · ${llm.magnitude} · confidence ${Math.round(llm.confidence * 100)}%`}
        <span className="text-on-surface-variant">
          {" "}
          · {llm.model}, {llm.as_of}. Does not change the score.
        </span>
      </p>
      <ul className="flex list-disc flex-col gap-2 pl-5 font-body-sm text-body-sm text-on-surface">
        {llm.reasons.map((x) => (
          <li key={x}>
            <ReasonText text={x} cited={llm.cited} />
          </li>
        ))}
      </ul>
      {llm.caveats.length > 0 && (
        <ul className="flex list-disc flex-col gap-2 pl-5 font-body-sm text-body-sm text-on-surface-variant">
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

function IdeaCard({
  r,
  rank,
  horizon,
  news,
  quote,
}: {
  r: Recommendation;
  rank: number;
  horizon: Horizon;
  news?: TickerNewsSentiment | null;
  quote?: Quote | null;
}) {
  const chartInterval = CHART_INTERVAL[horizon];

  return (
    <Card as="article" className="flex flex-col gap-8">
      <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
        <div className="flex items-start gap-4">
          <span className="pt-1 font-body-sm text-body-sm font-medium tabular-nums text-on-surface-variant">
            {String(rank).padStart(2, "0")}
          </span>
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="font-headline-md text-[32px] font-semibold leading-tight tracking-[-0.02em] text-on-surface">
                <a
                  href={tradingViewChartUrl(r.ticker, horizon)}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`View ${r.ticker} chart on TradingView with ${chartInterval.label} candles (opens in a new tab)`}
                  className="underline-offset-4 hover:text-tertiary-accent hover:underline"
                >
                  {r.ticker}
                </a>
              </h2>
              <Badge tone="success" icon="trending_up">
                {r.action}
              </Badge>
              {r.matches_interest && <Badge tone="info">Your sector</Badge>}
            </div>
            <p className="font-body-md text-body-md text-on-surface-variant">
              {r.name} · {SECTOR_LABEL[r.sector] ?? r.sector}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 md:flex-col md:items-end">
          <span className="font-metric-md text-metric-md tabular-nums text-on-surface">
            Score {r.score}
          </span>
          {r.is_example ? (
            <ProvenanceBadge provenance="example" />
          ) : (
            <ProvenanceBadge provenance="ai" label="Rule-based" />
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6 border-y border-surface-container-high py-6 sm:grid-cols-4">
        <Level label="Entry" value={usd(r.entry)} />
        <Level label="Stop" value={usd(r.stop)} tone="text-error" />
        <Level label="Target" value={usd(r.target)} tone="text-tertiary-accent" />
        <Level label="Position" value={`${r.position_pct}%`} />
      </div>

      <div className="flex flex-col gap-2 font-body-sm text-body-sm text-on-surface-variant">
        <p>
          Upside {r.upside_pct}% · Stop {r.stop_distance_pct}% below entry · If
          the stop is hit you lose about {r.loss_at_stop_pct}% of your capital.
        </p>
        {r.bigmove_p !== null && (
          <p>
            <span className="font-medium text-on-surface">
              Big-move chance {Math.round(r.bigmove_p * 100)}%
            </span>{" "}
            (typical 20%) — chance of moving more than most S&amp;P 500 stocks
            over the next 5 trading days, up or down. Not a direction forecast.
          </p>
        )}
        {!r.is_example && (
          <p>
            Entry is the {r.as_of ?? "latest"} daily close (Yahoo Finance), not
            a live price.{" "}
            {quote ? (
              <>
                Latest price{" "}
                <span className="font-medium text-on-surface">
                  {usd(quote.price)}
                </span>{" "}
                · {quoteTime(quote.quote_time)} · delayed
              </>
            ) : (
              "Latest price unavailable. Open the chart for current prices."
            )}
          </p>
        )}
      </div>

      <details className="group border-t border-surface-container-high pt-6">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-title-md text-title-md text-on-surface">
          <span>Why this stock and the news</span>
          <Icon
            name="expand_more"
            className="text-[22px] text-on-surface-variant transition-transform group-open:rotate-180"
          />
        </summary>
        <div className="mt-8 grid gap-8 md:grid-cols-2">
          <div className="flex flex-col gap-3">
            <SectionLabel>Reasons</SectionLabel>
            <ul className="flex list-disc flex-col gap-2 pl-5 font-body-md text-body-md text-on-surface">
              {[...r.match_reasons, ...r.reasons].map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          </div>
          <div className="flex flex-col gap-3">
            <SectionLabel>News</SectionLabel>
            <ul className="flex flex-col gap-3 font-body-sm text-body-sm text-on-surface">
              {r.news.length === 0 && (
                <li className="text-on-surface-variant">
                  No recent headlines found.
                </li>
              )}
              {r.news.map((n) => (
                <li key={n.title} className="flex flex-col gap-1">
                  {n.url ? (
                    <a
                      href={n.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-body-md text-body-md leading-snug text-on-surface hover:text-tertiary-accent"
                    >
                      {n.title}
                    </a>
                  ) : (
                    n.title
                  )}
                  <span className="flex flex-wrap items-center gap-2 text-on-surface-variant">
                    <SentimentBadge sentiment={n.sentiment} />
                    {n.source}
                    {n.published ? ` · ${n.published}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="mt-8 flex flex-col gap-6">
          {r.llm && <LlmBlock llm={r.llm} />}
          <NewsSentiment ticker={r.ticker} data={news} />
        </div>
      </details>
    </Card>
  );
}

export function IdeasView({
  horizon,
  items,
  topNews,
  newsSentiment,
  quotes,
  dataStatus,
}: {
  horizon: Horizon;
  items: Recommendation[] | null;
  topNews: TopNewsItem[];
  newsSentiment: Record<string, TickerNewsSentiment>;
  quotes: Record<string, Quote>;
  dataStatus: DataStatusData | null;
}) {
  return (
    <div className="flex flex-col gap-12 lg:gap-20">
      <header className="flex flex-col gap-6">
        <DataStatusBar status={dataStatus} />
        <div className="flex flex-col gap-4">
          <h1 className="max-w-3xl font-headline-lg text-headline-lg-mobile tracking-tight text-on-surface sm:text-headline-lg">
            Trade ideas
          </h1>
          <p className="max-w-2xl font-body-lg text-body-lg text-on-surface-variant">
            S&amp;P 500 stocks, buy-only, ranked for your holding period and
            risk profile. Open a card to see the reasons, the news, and the AI
            reading.
          </p>
        </div>
        <nav aria-label="Holding period" className="flex flex-wrap items-center gap-2">
          {HORIZONS.map((h) => (
            <Link
              key={h.value}
              href={`/?h=${h.value}`}
              aria-current={h.value === horizon ? "page" : undefined}
              className={`rounded-full px-5 py-2.5 font-body-sm text-body-sm font-medium transition-colors ${
                h.value === horizon
                  ? "bg-on-surface text-white"
                  : "bg-surface-container-low text-on-surface hover:bg-surface-container-high"
              }`}
            >
              {h.label}
            </Link>
          ))}
        </nav>
      </header>

      <TopNews items={topNews} />

      {items?.some((r) => r.is_example) ? (
        <NoticeBanner icon="info" tone="neutral" title="Example prices and scores">
          Prices, scores and position sizes below are placeholders until the
          live data pipeline is connected. Headlines are real (Google News), and
          sentiment labels, when shown, are AI-generated and not validated. This
          is not investment advice.
        </NoticeBanner>
      ) : (
        <NoticeBanner
          icon="info"
          tone="neutral"
          title={`Based on daily closing prices as of ${items?.[0]?.as_of ?? "—"}`}
        >
          Entry prices are Yahoo Finance end-of-day closes. The latest price on
          each card is a delayed Yahoo quote, not real-time. Ideas come from
          simple price-trend rules and have not been backtested. Headlines are
          for context only and do not affect the score.
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

      {items && items.length > 0 && (
        <section className="flex flex-col gap-6">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <h2 className="font-headline-sm text-headline-sm text-on-surface">
              Ideas for {HORIZONS.find((h) => h.value === horizon)?.label}
            </h2>
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              {items.length} {items.length === 1 ? "idea" : "ideas"}
            </span>
          </div>
          <div className="flex flex-col gap-6">
            {items.map((r, i) => (
              <IdeaCard
                key={r.ticker}
                r={r}
                rank={i + 1}
                horizon={horizon}
                news={newsSentiment[r.ticker] ?? null}
                quote={quotes[r.ticker] ?? null}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
