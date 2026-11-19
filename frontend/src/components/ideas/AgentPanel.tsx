"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { SectionLabel } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { AiRatingBadge, ratingTone } from "./AiRatingBadge";
import { SentimentBadge } from "./SentimentBadge";
import type {
  AgentReview,
  AiSummary,
  AnalystReview,
  Evidence,
  Horizon,
  Point,
  Rating,
  Recommendation,
  Signal,
} from "@/lib/recommendations";



const TABS = [
  "Summary",
  "Analysts",
  "Bull vs Bear",
  "Trade plan & risk",
  "News & social",
  "Track record",
] as const;

const ANALYST_LABEL: Record<keyof AgentReview["review"]["analysts"], string> = {
  market: "Market",
  news: "News",
  fundamentals: "Fundamentals",
  social: "Social",
};

const SOURCE_LABEL: Record<keyof AgentReview["sources"], string> = {
  prices: "Prices",
  news: "News",
  fmp: "Fundamentals data",
  sec: "SEC filings",
  social: "Social",
  macro: "Macro",
};

const SIGNAL: Record<
  Signal,
  { label: string; tone: "success" | "warning" | "danger" | "neutral" }
> = {
  bullish: { label: "Bullish", tone: "success" },
  neutral: { label: "Neutral", tone: "neutral" },
  bearish: { label: "Bearish", tone: "danger" },
  no_data: { label: "No data", tone: "neutral" },
};

const AGREE: Record<
  AgentReview["review"]["agrees"],
  { label: string; tone: "success" | "warning" | "danger" | "neutral"; icon: string }
> = {
  agree: {
    label: "Agrees with the rules",
    tone: "success",
    icon: "check_circle",
  },
  caution: {
    label: "Caution — the AI is less positive than the rules",
    tone: "warning",
    icon: "error",
  },
  disagree: {
    label: "Disagrees with the rules — the idea is still shown",
    tone: "danger",
    icon: "cancel",
  },
  review: {
    label: "Needs review",
    tone: "neutral",
    icon: "help",
  },
};

const STANCE: Record<
  "enter" | "wait" | "avoid",
  { label: string; tone: "success" | "warning" | "danger" }
> = {
  enter: { label: "Enter", tone: "success" },
  wait: { label: "Wait", tone: "warning" },
  avoid: { label: "Avoid", tone: "danger" },
};

type PanelState = "idle" | "loading" | "ok" | "missing" | "error";

const usd = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });
const money = (n: number | null | undefined) =>
  n === null || n === undefined ? "—" : usd(n);
const signedPct = (n: number | null | undefined) =>
  n === null || n === undefined ? "—" : `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`;

function chipOrder(...groups: string[][]): Map<string, number> {
  const order = new Map<string, number>();
  for (const group of groups) {
    for (const id of group) {
      if (!order.has(id)) order.set(id, order.size + 1);
    }
  }
  return order;
}

// The model sometimes writes raw evidence ids ("metric:rsi14", "agent:bear") inside a
// sentence; the [n] chips already cite them, so show plain words instead.
const RAW_ID = /\b(?:metric|news|fund|sec|social|macro|rule|agent|memory):([\w.-]+)/g;

function prose(text: string): string {
  return text
    .replace(RAW_ID, (_m, name: string) => name.replace(/[_-]+/g, " "))
    .replace(/\s{2,}/g, " ");
}

function evidenceTooltip(e: Evidence): string {
  return [e.label, e.value ? `· ${e.value}` : "", e.published_at ? `· ${e.published_at}` : ""]
    .filter(Boolean)
    .join(" ");
}

function Chips({
  ids,
  order,
  byId,
}: {
  ids: string[];
  order: Map<string, number>;
  byId: Map<string, Evidence>;
}) {
  const seen = new Set<string>();
  const chips = ids.filter((id) => {
    if (seen.has(id)) return false;
    seen.add(id);
    return order.has(id) && byId.has(id);
  });
  if (chips.length === 0) return null;
  return (
    <span className="ml-1 inline-flex flex-wrap items-center gap-1 align-middle">
      {chips.map((id) => {
        const n = order.get(id);
        const evidence = byId.get(id);
        if (!n || !evidence) return null;
        const className =
          "rounded bg-surface-container-high px-1 font-body-sm text-[11px] font-medium tabular-nums text-on-surface-variant hover:bg-surface-container-highest";
        return evidence.url ? (
          <a
            key={id}
            href={evidence.url}
            target="_blank"
            rel="noopener noreferrer"
            title={evidenceTooltip(evidence)}
            className={className}
          >
            [{n}]
          </a>
        ) : (
          <span key={id} title={evidenceTooltip(evidence)} className={className}>
            [{n}]
          </span>
        );
      })}
    </span>
  );
}

function Points({
  points,
  order,
  byId,
  empty = "No points.",
}: {
  points: Point[];
  order: Map<string, number>;
  byId: Map<string, Evidence>;
  empty?: string;
}) {
  if (points.length === 0) {
    return (
      <p className="font-body-sm text-body-sm text-on-surface-variant">{empty}</p>
    );
  }
  return (
    <ul className="flex list-disc flex-col gap-2 pl-5 font-body-sm text-body-sm text-on-surface">
      {points.map((p, i) => (
        <li key={i}>
          {prose(p.text)}
          <Chips ids={p.evidence} order={order} byId={byId} />
        </li>
      ))}
    </ul>
  );
}

function sentimentFor(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const s = raw.toLowerCase();
  if (s === "positive" || s === "bullish") return "bullish";
  if (s === "negative" || s === "bearish") return "bearish";
  if (s === "neutral") return "neutral";
  return null;
}

function RatingPill({ rating }: { rating: Rating }) {
  return (
    <Badge tone={ratingTone(rating)} className="tabular-nums">
      {rating}
    </Badge>
  );
}

function AnalystCard({
  title,
  analyst,
  order,
  byId,
}: {
  title: string;
  analyst: AnalystReview | null;
  order: Map<string, number>;
  byId: Map<string, Evidence>;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-[20px] bg-surface-container-low p-4">
      <div className="flex flex-wrap items-center gap-2">
        <h4 className="font-title-md text-title-md text-on-surface">{title}</h4>
        {analyst && (
          <Badge tone={SIGNAL[analyst.signal].tone}>
            {SIGNAL[analyst.signal].label}
          </Badge>
        )}
        <ProvenanceBadge provenance="ai" label="AI" />
      </div>
      {analyst ? (
        <>
          <p className="font-body-sm text-body-sm text-on-surface">
            {prose(analyst.summary)}
          </p>
          <Points points={analyst.points} order={order} byId={byId} />
          {analyst.data_gaps.length > 0 && (
            <div className="flex flex-col gap-1">
              <SectionLabel>Data gaps</SectionLabel>
              <ul className="flex list-disc flex-col gap-1 pl-5 font-body-sm text-body-sm text-on-surface-variant">
                {analyst.data_gaps.map((gap) => (
                  <li key={gap}>{gap}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      ) : (
        <p className="font-body-sm text-body-sm text-on-surface-variant">
          Not available for this review.
        </p>
      )}
    </div>
  );
}

export function AgentPanel({
  ticker,
  horizon,
  ai,
  reasons,
  matchReasons,
  news,
}: {
  ticker: string;
  horizon: Horizon;
  ai: AiSummary | null;
  reasons: string[];
  matchReasons: string[];
  news: Recommendation["news"];
}) {
  const [state, setState] = useState<PanelState>(ai ? "idle" : "missing");
  const [review, setReview] = useState<AgentReview | null>(null);
  const [isDemo, setIsDemo] = useState(false);
  const [tab, setTab] = useState(0);
  const requested = useRef(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const load = useCallback(async () => {
    if (requested.current) return;
    const demo =
      process.env.NODE_ENV === "development" &&
      typeof window !== "undefined" &&
      new URLSearchParams(window.location.search).get("demoAgents") === "1";
    if (demo) {
      requested.current = true;
      try {
        const exampleJson = await import("@/lib/agent-example.json");
        setReview(exampleJson.default as unknown as AgentReview);
        setIsDemo(true);
        setState("ok");
      } catch {
        setState("error");
      }
      return;
    }
    if (!ai) return;
    requested.current = true;
    if (ai.mode === "quick") {
      // A quick review has no detail endpoint; the panel shows it from the list data.
      setState("missing");
      return;
    }
    setState("loading");
    try {
      const res = await fetch(
        `/api/agents/${encodeURIComponent(ticker)}?horizon=${horizon}`,
        { cache: "no-store" },
      );
      if (res.status === 404) {
        setState("missing");
        return;
      }
      if (!res.ok) {
        setState("error");
        return;
      }
      setReview((await res.json()) as AgentReview);
      setState("ok");
    } catch {
      setState("error");
    }
  }, [ai, horizon, ticker]);

  useEffect(() => {
    const details = rootRef.current?.closest("details");
    if (!details) return;
    const maybeLoad = () => {
      if (details.open) void load();
    };
    maybeLoad();
    details.addEventListener("toggle", maybeLoad);
    return () => details.removeEventListener("toggle", maybeLoad);
  }, [load]);

  const retry = () => {
    requested.current = false;
    void load();
  };

  const evidence = useMemo(
    () => new Map((review?.evidence ?? []).map((e) => [e.id, e] as const)),
    [review],
  );

  if (state === "ok" && review) {
    const r = review.review;
    const manager = r.debate.manager;
    const summaryOrder = chipOrder(
      ...r.key_risks.map((p) => p.evidence),
      manager?.evidence ?? [],
    );
    const analystOrder = chipOrder(
      ...(Object.keys(ANALYST_LABEL) as (keyof typeof ANALYST_LABEL)[]).flatMap(
        (key) => (r.analysts[key]?.points ?? []).map((p) => p.evidence),
      ),
    );
    const debateOrder = chipOrder(
      ...r.debate.bull.map((p) => p.evidence),
      ...r.debate.bear.map((p) => p.evidence),
      manager?.evidence ?? [],
    );
    const planOrder = chipOrder(
      r.trader?.evidence ?? [],
      ...(Object.keys(r.risk) as (keyof typeof r.risk)[]).map(
        (key) => r.risk[key]?.evidence ?? [],
      ),
    );
    const agree = AGREE[r.agrees];
    const newsEvidence = review.evidence.filter(
      (e) => e.kind === "news" || e.kind === "social",
    );

    const summaryTab = (
      <div className="grid gap-6 md:grid-cols-2">
        <div className="flex flex-col gap-3">
          <SectionLabel>From the rules</SectionLabel>
          <ul className="flex list-disc flex-col gap-2 pl-5 font-body-md text-body-md text-on-surface">
            {[...matchReasons, ...reasons].map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </div>
        <div className="flex flex-col gap-3">
          <SectionLabel>AI key points</SectionLabel>
          <Points
            points={r.key_risks}
            order={summaryOrder}
            byId={evidence}
            empty="The AI did not add key points."
          />
          {manager && (
            <div className="flex flex-col gap-2 rounded-[20px] bg-surface-container-low p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-title-md text-title-md text-on-surface">
                  Research manager
                </span>
                <RatingPill rating={manager.lean} />
                <ProvenanceBadge provenance="ai" label="AI" />
              </div>
              <p className="font-body-sm text-body-sm text-on-surface">
                {prose(manager.rationale)}
                <Chips ids={manager.evidence} order={summaryOrder} byId={evidence} />
              </p>
            </div>
          )}
        </div>
      </div>
    );

    const analystsTab = (
      <div className="flex flex-col gap-4">
        <div className="grid gap-4 md:grid-cols-2">
          {(Object.keys(ANALYST_LABEL) as (keyof typeof ANALYST_LABEL)[]).map(
            (key) => (
              <AnalystCard
                key={key}
                title={ANALYST_LABEL[key]}
                analyst={r.analysts[key]}
                order={analystOrder}
                byId={evidence}
              />
            ),
          )}
        </div>
        <div className="flex flex-col gap-1 rounded-[20px] bg-surface-container-low p-4 font-body-sm text-body-sm text-on-surface-variant">
          <SectionLabel>Data sources</SectionLabel>
          <ul className="flex flex-col gap-1">
            {(Object.keys(SOURCE_LABEL) as (keyof typeof SOURCE_LABEL)[]).map(
              (key) => {
                const source = review.sources[key];
                return (
                  <li key={key} className="tabular-nums">
                    {SOURCE_LABEL[key]}: {source.status}
                    {source.reason ? ` — ${source.reason}` : ""}
                  </li>
                );
              },
            )}
          </ul>
        </div>
      </div>
    );

    const debateTab = (
      <div className="flex flex-col gap-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="flex flex-col gap-2 rounded-[20px] bg-surface-container-low p-4">
            <h4 className="font-title-md text-title-md text-on-surface">Bull case</h4>
            <Points
              points={r.debate.bull}
              order={debateOrder}
              byId={evidence}
              empty="No bull points."
            />
          </div>
          <div className="flex flex-col gap-2 rounded-[20px] bg-surface-container-low p-4">
            <h4 className="font-title-md text-title-md text-on-surface">Bear case</h4>
            <Points
              points={r.debate.bear}
              order={debateOrder}
              byId={evidence}
              empty="No bear points."
            />
          </div>
        </div>
        <div className="flex flex-col gap-2 rounded-[20px] bg-surface-container-low p-4">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="font-title-md text-title-md text-on-surface">
              Research manager
            </h4>
            {manager ? <RatingPill rating={manager.lean} /> : null}
            <ProvenanceBadge provenance="ai" label="AI" />
          </div>
          {manager ? (
            <p className="font-body-sm text-body-sm text-on-surface">
              {prose(manager.rationale)}
              <Chips ids={manager.evidence} order={debateOrder} byId={evidence} />
            </p>
          ) : (
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Not available for this review.
            </p>
          )}
        </div>
      </div>
    );

    const planTab = (
      <div className="flex flex-col gap-4">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[320px] border-collapse text-left font-body-sm text-body-sm">
            <caption className="sr-only">
              The card&apos;s rule levels compared with the AI suggestion
            </caption>
            <thead>
              <tr className="text-on-surface-variant">
                <th scope="col" className="py-2 pr-4 font-medium">
                  Level
                </th>
                <th scope="col" className="py-2 pr-4 font-medium">
                  Rules (used)
                </th>
                <th scope="col" className="py-2 font-medium">
                  AI suggestion
                </th>
              </tr>
            </thead>
            <tbody className="tabular-nums text-on-surface">
              <tr className="border-t border-surface-container-high">
                <th scope="row" className="py-2 pr-4 font-normal">
                  Entry
                </th>
                <td className="py-2 pr-4">{money(r.rules.entry)}</td>
                <td className="py-2">—</td>
              </tr>
              <tr className="border-t border-surface-container-high">
                <th scope="row" className="py-2 pr-4 font-normal">
                  Stop
                </th>
                <td className="py-2 pr-4">{money(r.rules.stop)}</td>
                <td className="py-2">{money(r.trader?.suggested_stop)}</td>
              </tr>
              <tr className="border-t border-surface-container-high">
                <th scope="row" className="py-2 pr-4 font-normal">
                  Target
                </th>
                <td className="py-2 pr-4">{money(r.rules.target)}</td>
                <td className="py-2">{money(r.trader?.suggested_target)}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="font-body-sm text-body-sm text-on-surface-variant">
          The card&apos;s entry, stop and target always come from the rules. The
          AI suggestion is stored and shown separately and never changes them.
        </p>

        <div className="flex flex-col gap-2 rounded-[20px] bg-surface-container-low p-4">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="font-title-md text-title-md text-on-surface">Trader plan</h4>
            {r.trader && (
              <Badge tone={STANCE[r.trader.stance].tone}>
                {STANCE[r.trader.stance].label}
              </Badge>
            )}
            <ProvenanceBadge provenance="ai" label="AI" />
          </div>
          {r.trader ? (
            <p className="font-body-sm text-body-sm text-on-surface">
              {prose(r.trader.rationale)}
              <Chips ids={r.trader.evidence} order={planOrder} byId={evidence} />
            </p>
          ) : (
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              No trade plan from the AI for this idea.
            </p>
          )}
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {(Object.keys(r.risk) as (keyof typeof r.risk)[]).map((key) => {
            const view = r.risk[key];
            return (
              <div
                key={key}
                className="flex flex-col gap-2 rounded-[20px] bg-surface-container-low p-4"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="font-title-md text-title-md capitalize text-on-surface">
                    {key}
                  </h4>
                  <ProvenanceBadge provenance="ai" label="AI" />
                </div>
                {view ? (
                  <>
                    <p className="font-body-sm text-body-sm text-on-surface">
                      {view.view}
                      <Chips ids={view.evidence} order={planOrder} byId={evidence} />
                    </p>
                    <p className="font-body-sm text-body-sm text-on-surface-variant">
                      Suggested position{" "}
                      <span className="tabular-nums text-on-surface">
                        {view.suggested_position_pct === null
                          ? "—"
                          : `${view.suggested_position_pct}%`}
                      </span>
                    </p>
                  </>
                ) : (
                  <p className="font-body-sm text-body-sm text-on-surface-variant">
                    Not available for this review.
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );

    const newsTab =
      newsEvidence.length === 0 ? (
        <p className="font-body-sm text-body-sm text-on-surface-variant">
          No news or social evidence in this review.
        </p>
      ) : (
        <ul className="flex flex-col gap-3 font-body-sm text-body-sm text-on-surface">
          {newsEvidence.map((e) => (
            <li key={e.id} className="flex flex-col gap-1">
              {e.url ? (
                <a
                  href={e.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-body-md text-body-md leading-snug text-on-surface hover:text-tertiary-accent"
                >
                  {e.label}
                </a>
              ) : (
                e.label
              )}
              <span className="flex flex-wrap items-center gap-2 text-on-surface-variant">
                <SentimentBadge sentiment={sentimentFor(e.sentiment)} />
                <Badge tone="neutral">{e.kind}</Badge>
                {e.published_at ? (
                  <span className="tabular-nums">
                    {new Date(e.published_at).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </span>
                ) : null}
              </span>
            </li>
          ))}
        </ul>
      );

    const trackTab =
      review.track_record.length === 0 ? (
        <p className="font-body-sm text-body-sm text-on-surface-variant">
          No settled reviews yet (settles after 5 trading days)
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[420px] border-collapse text-left font-body-sm text-body-sm">
            <caption className="sr-only">Past reviews and how they did vs SPY</caption>
            <thead>
              <tr className="text-on-surface-variant">
                <th scope="col" className="py-2 pr-4 font-medium">
                  Date
                </th>
                <th scope="col" className="py-2 pr-4 font-medium">
                  Rating
                </th>
                <th scope="col" className="py-2 pr-4 font-medium">
                  Return
                </th>
                <th scope="col" className="py-2 pr-4 font-medium">
                  SPY
                </th>
                <th scope="col" className="py-2 pr-4 font-medium">
                  Alpha
                </th>
                <th scope="col" className="py-2 font-medium">
                  Reflection
                </th>
              </tr>
            </thead>
            <tbody className="text-on-surface">
              {review.track_record.map((entry) => (
                <tr
                  key={`${entry.as_of}-${entry.rating}`}
                  className="border-t border-surface-container-high align-top"
                >
                  <td className="py-2 pr-4 tabular-nums">{entry.as_of}</td>
                  <td className="py-2 pr-4">
                    <RatingPill rating={entry.rating} />
                  </td>
                  <td className="py-2 pr-4 tabular-nums">
                    {signedPct(entry.return_pct)}
                  </td>
                  <td className="py-2 pr-4 tabular-nums">
                    {signedPct(entry.benchmark_return_pct)}
                  </td>
                  <td className="py-2 pr-4 tabular-nums">
                    {signedPct(entry.alpha_pct)}
                  </td>
                  <td className="max-w-[320px] py-2">{entry.reflection ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );

    const tabContent = [summaryTab, analystsTab, debateTab, planTab, newsTab, trackTab][tab];

    return (
      <div ref={rootRef} className="flex flex-col gap-4">
        <div className="flex flex-col gap-3 rounded-[20px] bg-surface-container-low p-4 md:p-5">
          <div className="flex flex-wrap items-center gap-2">
            <AiRatingBadge rating={r.rating} label={`AI · ${r.rating}`} />
            <ProvenanceBadge provenance="ai" label="AI opinion · not backtested" />
            {isDemo && <ProvenanceBadge provenance="example" label="Example data" />}
          </div>
          <p className="font-body-md text-body-md text-on-surface">
            {prose(r.summary)}
            <Chips
              ids={Array.from(summaryOrder.keys())}
              order={summaryOrder}
              byId={evidence}
            />
          </p>
          <span title={agree.label}>
            <Badge tone={agree.tone} icon={agree.icon}>
              {agree.label}
            </Badge>
          </span>
          <p className="font-body-sm text-body-sm text-on-surface-variant">
            AI opinion · not backtested · not investment advice
          </p>
        </div>

        <div
          role="tablist"
          aria-label="AI review sections"
          className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1"
        >
          {TABS.map((label, i) => (
            <button
              key={label}
              ref={(el) => {
                tabRefs.current[i] = el;
              }}
              type="button"
              role="tab"
              id={`agent-tab-${i}`}
              aria-selected={tab === i}
              aria-controls="agent-tabpanel"
              tabIndex={tab === i ? 0 : -1}
              onClick={() => setTab(i)}
              onKeyDown={(event) => {
                let next: number | null = null;
                if (event.key === "ArrowRight") next = (i + 1) % TABS.length;
                if (event.key === "ArrowLeft") next = (i - 1 + TABS.length) % TABS.length;
                if (event.key === "Home") next = 0;
                if (event.key === "End") next = TABS.length - 1;
                if (next !== null) {
                  event.preventDefault();
                  setTab(next);
                  tabRefs.current[next]?.focus();
                }
              }}
              className={`whitespace-nowrap rounded-full px-4 py-2 font-body-sm text-body-sm font-medium transition-colors ${
                tab === i
                  ? "bg-on-surface text-white"
                  : "bg-surface-container-low text-on-surface hover:bg-surface-container-high"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div
          role="tabpanel"
          id="agent-tabpanel"
          aria-labelledby={`agent-tab-${tab}`}
          tabIndex={0}
          className="flex flex-col gap-4 rounded-[20px] border border-surface-container-high p-4 md:p-5"
        >
          {tabContent}
        </div>

        <footer className="flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-surface-container-high pt-3 font-body-sm text-body-sm text-on-surface-variant">
          <span>{review.model}</span>
          <span aria-hidden>·</span>
          <span>{review.prompt_version}</span>
          <span aria-hidden>·</span>
          <span className="tabular-nums">
            reviewed{" "}
            {new Date(review.created_at).toLocaleString("en-US", {
              dateStyle: "medium",
              timeStyle: "short",
            })}
          </span>
          <span aria-hidden>·</span>
          <span>Not investment advice.</span>
        </footer>
      </div>
    );
  }

  if (state === "loading") {
    return (
      <div ref={rootRef} className="flex flex-col gap-3" aria-busy="true">
        <span className="sr-only">Loading the AI review…</span>
        <div className="h-28 animate-pulse rounded-[20px] bg-surface-container-low" />
        <div className="h-9 w-2/3 animate-pulse rounded-full bg-surface-container-low" />
        <div className="h-32 animate-pulse rounded-[20px] bg-surface-container-low" />
      </div>
    );
  }

  if (state === "error") {
    return (
      <div ref={rootRef} className="flex flex-col gap-3">
        <p className="font-body-md text-body-md text-error">
          Could not load the AI review for {ticker}.
        </p>
        <button
          type="button"
          onClick={retry}
          className="inline-flex h-9 w-fit items-center justify-center gap-2 rounded-full bg-surface-container-low px-4 font-body-sm text-body-sm font-medium text-on-surface transition-colors hover:bg-surface-container-high"
        >
          <Icon name="refresh" className="text-[18px]" />
          Try again
        </button>
      </div>
    );
  }

  return (
    <div ref={rootRef} className="flex flex-col gap-4">
      {ai?.mode === "quick" && (
        <div className="flex flex-col gap-3 rounded-[20px] border border-surface-container-high p-4 md:p-5">
          <div className="flex flex-wrap items-center gap-2">
            <AiRatingBadge
              rating={ai.rating}
              label={`AI quick · ${ai.rating}`}
            />
            <Badge tone="neutral">Confidence: {ai.confidence ?? "low"}</Badge>
            <Badge
              tone={AGREE[ai.agrees].tone}
              icon={AGREE[ai.agrees].icon}
            >
              {AGREE[ai.agrees].label}
            </Badge>
          </div>
          <p className="font-body-md text-body-md text-on-surface">
            {prose(ai.summary)}
          </p>
          {(ai.points ?? []).length > 0 && (
            <ul className="flex list-disc flex-col gap-2 pl-5 font-body-md text-body-md text-on-surface">
              {(ai.points ?? []).map((p) => (
                <li key={p.text}>{prose(p.text)}</li>
              ))}
            </ul>
          )}
          <p className="font-body-sm text-body-sm text-on-surface-variant">
            Quick AI check from a one-page brief (the rule idea, price metrics
            and a few headlines). The full 12-agent review has not run for this
            idea. AI opinion · not backtested · not investment advice.
          </p>
        </div>
      )}
      <div className="grid gap-6 md:grid-cols-2">
        <div className="flex flex-col gap-3">
          <SectionLabel>Reasons</SectionLabel>
          <ul className="flex list-disc flex-col gap-2 pl-5 font-body-md text-body-md text-on-surface">
            {[...matchReasons, ...reasons].map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </div>
        <div className="flex flex-col gap-3">
          <SectionLabel>News</SectionLabel>
          <ul className="flex flex-col gap-3 font-body-sm text-body-sm text-on-surface">
            {news.length === 0 && (
              <li className="text-on-surface-variant">No recent headlines found.</li>
            )}
            {news.map((n) => (
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
      {ai?.mode !== "quick" && (
        <p className="font-body-sm text-body-sm text-on-surface-variant">
          AI review pending — this card shows the rule-based idea until the
          agent team has reviewed it.
        </p>
      )}
    </div>
  );
}
