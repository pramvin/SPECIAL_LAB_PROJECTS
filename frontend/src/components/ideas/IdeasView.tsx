import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { NoticeBanner } from "@/components/ui/NoticeBanner";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { AiRatingBadge } from "./AiRatingBadge";
import { AgentPanel } from "./AgentPanel";
import { TradeRow, WatchButton } from "./CardActions";
import type { Portfolio } from "@/lib/wallet";
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
  hint,
  note,
}: {
  label: string;
  value: string;
  tone?: string;
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
      <span
        className={`font-metric-md text-metric-md tabular-nums ${tone ?? "text-on-surface"}`}
      >
        {value}
      </span>
      {note && (
        <span className="text-[12px] text-on-surface-variant">{note}</span>
      )}
    </div>
  );
}

/** Top stripe colour: how the AI review sits against the rule-based idea. */
const ACCENT: Record<string, string> = {
  agree: "bg-provenance-input-text",
  caution: "bg-amber-500",
  disagree: "bg-error",
  review: "bg-surface-container-highest",
  none: "bg-surface-container-high",
};

// The model sometimes writes "Headline [1091]" or "Headlines 12 and 15" in a reason; turn those ids into links.
const ID_REF = /(\[\d+\]|\bHeadlines?\s+\d+(?:\s*(?:,|and)\s*\d+)*)/;

function ReasonText({
  text,
  cited,
}: {
  text: string;
  cited: LlmAnalysis["cited"];
}) {
  const byId = new Map(
    cited.map((c, i) => [String(c.id), { cited: c, n: i + 1 }]),
  );
  const chip = (
    c: LlmAnalysis["cited"][number],
    n: number,
    key: string,
    className = "",
  ) =>
    c.url ? (
      <a
        key={key}
        href={c.url}
        target="_blank"
        rel="noopener noreferrer"
        title={c.title}
        className={`text-tertiary-accent hover:underline ${className}`}
      >
        [{n}]
      </a>
    ) : (
      <span key={key} title={c.title} className={`text-on-surface-variant ${className}`}>
        [{n}]
      </span>
    );

  return (
    <>
      {text.split(ID_REF).map((part, i) => {
        if (i % 2 === 0) return part;
        if (part.startsWith("[")) {
          const known = [...new Set(part.match(/\d+/g) ?? [])]
            .map((id) => byId.get(id))
            .filter(
              (x): x is { cited: LlmAnalysis["cited"][number]; n: number } =>
                x !== undefined,
            );
          if (known.length === 0) return null;
          return (
            <span key={i}>
              {known.map(({ cited: c, n }, k) =>
                chip(c, n, c.id.toString(), k > 0 ? "ml-1" : ""),
              )}
            </span>
          );
        }
        return (
          <span key={i}>
            {part.split(/(\d+)/).map((piece, k) => {
              if (k % 2 === 0) return piece;
              const hit = byId.get(piece);
              return hit ? chip(hit.cited, hit.n, `${piece}-${k}`, "") : null;
            })}
          </span>
        );
      })}
    </>
  );
}

function LlmBlock({ llm }: { llm: LlmAnalysis }) {
  const dir = { up: "Up", down: "Down", none: "No clear view" }[llm.direction];
  return (
    <div className="flex flex-col gap-3 rounded-[20px] bg-surface-container-low p-4 md:p-5">
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
  portfolio,
  watching,
}: {
  r: Recommendation;
  rank: number;
  horizon: Horizon;
  news?: TickerNewsSentiment | null;
  quote?: Quote | null;
  portfolio: Portfolio | null;
  watching: boolean;
}) {
  const trade = portfolio !== null && !r.is_example;
  const chartInterval = CHART_INTERVAL[horizon];

  return (
    <Card as="article" className="relative flex flex-col gap-6 overflow-hidden">
      <span
        aria-hidden
        className={`absolute inset-x-0 top-0 h-1.5 ${ACCENT[r.ai?.agrees ?? "none"]}`}
      />
      <div className="flex flex-col gap-4 pt-1 md:flex-row md:items-start md:justify-between">
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
          <div className="flex flex-wrap items-center gap-2 md:justify-end">
          {trade && <WatchButton ticker={r.ticker} watching={watching} />}
          {r.is_example ? (
            <ProvenanceBadge provenance="example" />
          ) : r.ai ? (
            <AiRatingBadge
              rating={r.ai.rating}
              label={
                r.ai.mode === "quick" ? `AI quick · ${r.ai.rating}` : undefined
              }
            />
          ) : (
            <span
              title="No AI review yet. This card shows the rule-based idea."
              className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-surface-container-highest px-3 py-1 font-body-sm text-body-sm text-on-surface-variant"
            >
              <Icon name="hourglass_top" className="text-[16px]" />
              Rule-based · AI pending
            </span>
          )}
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-2">
          <Level
            label="Current price"
            value={quote ? usd(quote.price) : "—"}
            hint="Nearly real-time: Yahoo Finance quote, can be a few minutes behind"
            note={quote ? quoteTime(quote.quote_time) : "Unavailable"}
          />
          <Level label="Entry" value={usd(r.entry)} />
        </div>
      </div>

      <div className="flex flex-col gap-2 font-body-sm text-body-sm text-on-surface-variant">
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
            a live price.
          </p>
        )}
      </div>

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

      <details className="group border-t border-surface-container-high pt-5">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-title-md text-title-md text-on-surface">
          <span>Why this stock and the news</span>
          <Icon
            name="expand_more"
            className="text-[22px] text-on-surface-variant transition-transform group-open:rotate-180"
          />
        </summary>
        <div className="mt-6 flex flex-col gap-5">
          <AgentPanel
            ticker={r.ticker}
            horizon={horizon}
            ai={r.ai}
            reasons={r.reasons}
            matchReasons={r.match_reasons}
            news={r.news}
          />
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
  portfolio,
  watchlist,
}: {
  horizon: Horizon;
  items: Recommendation[] | null;
  topNews: TopNewsItem[];
  newsSentiment: Record<string, TickerNewsSentiment>;
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
          live data pipeline is connected. Headlines are real (Yahoo Finance), and
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
                news={newsSentiment[r.ticker] ?? null}
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
