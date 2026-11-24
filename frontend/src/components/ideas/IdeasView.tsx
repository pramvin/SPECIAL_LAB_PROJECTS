import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { NoticeBanner } from "@/components/ui/NoticeBanner";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { TradeRow, WatchButton } from "./CardActions";
import { LatestNews } from "./LatestNews";
import { SentimentBadge } from "./SentimentBadge";
import { DataStatus as DataStatusBar } from "./DataStatus";
import type { Portfolio } from "@/lib/wallet";
import {
  HORIZONS,
  type Horizon,
  type LatestNews as LatestNewsData,
  type Quote,
  type Recommendation,
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

function Level({
  label,
  value,
  hint,
  note,
}: {
  label: string;
  value: string;
  hint?: string;
  note?: string;
}) {
  return (
    <div className="flex flex-col gap-1 rounded-[16px] bg-surface-container-low px-4 py-3">
      <span className="flex items-center gap-1 font-body-sm text-body-sm text-on-surface-variant">
        {label}
        {hint && (
          <span title={hint} aria-label={hint} className="inline-flex">
            <Icon name="schedule" className="text-[14px]" />
          </span>
        )}
      </span>
      <span className="font-metric-md text-metric-md tabular-nums text-on-surface">
        {value}
      </span>
      {note && (
        <span className="text-[12px] text-on-surface-variant">{note}</span>
      )}
    </div>
  );
}

function IdeaCard({
  r,
  rank,
  horizon,
  quote,
  portfolio,
  watching,
}: {
  r: Recommendation;
  rank: number;
  horizon: Horizon;
  quote?: Quote | null;
  portfolio: Portfolio | null;
  watching: boolean;
}) {
  const trade = portfolio !== null && !r.is_example;
  const headlines = r.news.slice(0, 3);

  return (
    <Card as="article" className="flex flex-col gap-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="flex items-start gap-4">
          <span className="pt-1 font-body-sm text-body-sm font-medium tabular-nums text-on-surface-variant">
            {String(rank).padStart(2, "0")}
          </span>
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="font-headline-md text-[32px] font-semibold leading-tight tracking-[-0.02em] text-on-surface">
                <Link
                  href={`/stock/${r.ticker}?h=${horizon}`}
                  className="underline-offset-4 hover:text-tertiary-accent hover:underline"
                >
                  {r.ticker}
                </Link>
              </h2>
              {r.bigmove_p !== null && (
                <Badge tone="neutral" icon="bolt">
                  Big-move chance {Math.round(r.bigmove_p * 100)}%
                </Badge>
              )}
              {r.matches_interest && <Badge tone="info">Your sector</Badge>}
            </div>
            <p className="font-body-md text-body-md text-on-surface-variant">
              {r.name} · {SECTOR_LABEL[r.sector] ?? r.sector}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3 md:flex-col md:items-end">
          <span className="font-metric-md text-metric-md tabular-nums text-on-surface">
            Score {r.score}
          </span>
          <div className="flex flex-wrap items-center gap-2 md:justify-end">
            {trade && <WatchButton ticker={r.ticker} watching={watching} />}
            {r.is_example && <ProvenanceBadge provenance="example" />}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Level
          label="Current price"
          value={quote ? usd(quote.price) : "—"}
          hint="Nearly real-time: Yahoo Finance quote, can be a few minutes behind"
          note={quote ? quoteTime(quote.quote_time) : "Unavailable"}
        />
        <Level label="Entry" value={usd(r.entry)} />
      </div>

      <div className="flex flex-col gap-2 font-body-sm text-body-sm text-on-surface-variant">
        {r.bigmove_p !== null && (
          <p>
            Big-move chance is the chance of moving more than most S&amp;P 500
            stocks over the next 5 trading days, up or down (typical 20%). Not a
            direction forecast.
          </p>
        )}
        {!r.is_example && (
          <p>
            Entry is the {r.as_of ?? "latest"} daily close (Yahoo Finance), not
            a live price.
          </p>
        )}
      </div>

      {headlines.length > 0 && (
        <div className="flex flex-col gap-2 border-t border-surface-container-high pt-4">
          <span className="font-body-sm text-body-sm font-medium text-on-surface-variant">
            Latest news
          </span>
          <ul className="flex flex-col gap-2">
            {headlines.map((n) => (
              <li
                key={n.url || n.title}
                className="flex flex-wrap items-center gap-2 font-body-sm text-body-sm"
              >
                <SentimentBadge sentiment={n.sentiment} />
                {n.url ? (
                  <a
                    href={n.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="min-w-0 text-on-surface underline-offset-2 hover:underline"
                  >
                    {n.title}
                  </a>
                ) : (
                  <span className="min-w-0 text-on-surface">{n.title}</span>
                )}
                <span className="text-on-surface-variant">{n.source}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {trade && (
        <TradeRow
          ticker={r.ticker}
          entry={r.entry}
          balance={portfolio.balance}
          position={
            portfolio.positions.find((p) => p.ticker === r.ticker) ?? null
          }
          livePrice={quote?.price ?? null}
        />
      )}
    </Card>
  );
}

export function IdeasView({
  horizon,
  items,
  latestNews,
  quotes,
  dataStatus,
  portfolio,
  watchlist,
}: {
  horizon: Horizon;
  items: Recommendation[] | null;
  latestNews: LatestNewsData | null;
  quotes: Record<string, Quote>;
  dataStatus: DataStatusData | null;
  portfolio: Portfolio | null;
  watchlist: Set<string>;
}) {
  return (
    <div className="flex flex-col gap-8 lg:gap-10">
      <header className="flex flex-col gap-4">
        <DataStatusBar status={dataStatus} />
        <div className="flex flex-col gap-3">
          <h1 className="max-w-3xl font-headline-lg text-headline-lg-mobile tracking-tight text-on-surface sm:text-headline-lg">
            Trade ideas
          </h1>
          <p className="max-w-2xl font-body-lg text-body-lg text-on-surface-variant">
            S&amp;P 500 stocks, buy-only, ranked for your holding period and
            risk profile. Open a ticker for this week&rsquo;s news, chart and
            social read.
          </p>
        </div>
        <nav
          aria-label="Holding period"
          className="flex flex-wrap items-center gap-2"
        >
          {HORIZONS.map((h) =>
            h.value === "1w" ? (
              <Link
                key={h.value}
                href="/?h=1w"
                aria-current={h.value === horizon ? "page" : undefined}
                className={`rounded-full px-5 py-2.5 font-body-sm text-body-sm font-medium transition-colors ${
                  h.value === horizon
                    ? "bg-on-surface text-white"
                    : "bg-surface-container-low text-on-surface hover:bg-surface-container-high"
                }`}
              >
                {h.label}
              </Link>
            ) : (
              <span
                key={h.value}
                aria-disabled="true"
                title={`${h.label} is coming soon`}
                className="inline-flex cursor-not-allowed items-center gap-2 rounded-full bg-surface-container-low px-5 py-2.5 font-body-sm text-body-sm font-medium text-on-surface-variant opacity-60"
              >
                {h.label}
                <span className="rounded-full border border-surface-container-high bg-white px-2 py-0.5 text-[11px] font-semibold">
                  Coming soon
                </span>
              </span>
            ),
          )}
        </nav>
      </header>

      <LatestNews initial={latestNews} />

      {items?.some((r) => r.is_example) ? (
        <NoticeBanner icon="info" tone="neutral" title="Example prices and scores">
          Prices, scores and position sizes below are placeholders until the
          live data pipeline is connected. Headlines are real (Yahoo Finance), and
          sentiment labels are model guesses and can be wrong. This is not
          investment advice.
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
          for context only and do not affect the score. Not investment advice.
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
        <section className="flex flex-col gap-5">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <h2 className="font-headline-sm text-headline-sm text-on-surface">
              Ideas for {HORIZONS.find((h) => h.value === horizon)?.label}
            </h2>
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              {items.length} {items.length === 1 ? "idea" : "ideas"}
            </span>
          </div>
          <div className="flex flex-col gap-5">
            {items.map((r, i) => (
              <IdeaCard
                key={r.ticker}
                r={r}
                rank={i + 1}
                horizon={horizon}
                quote={quotes[r.ticker] ?? null}
                portfolio={portfolio}
                watching={watchlist.has(r.ticker)}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
