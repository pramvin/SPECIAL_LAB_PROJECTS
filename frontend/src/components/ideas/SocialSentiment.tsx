"use client";

import { useState } from "react";
import { SectionLabel } from "@/components/ui/Card";

/**
 * EXAMPLE DATA ONLY. No social-media source is connected yet: every account,
 * post and percentage below is synthetic and does not change the real score.
 */
type Tag = "pos" | "neu" | "neg";

interface Scenario {
  id: string;
  label: string;
  split: [number, number, number]; // positive, neutral, negative (%)
  accounts: number;
  hype: number;
  adjust: number; // capped at +/-10
  tone: "ok" | "warn";
  note: string;
  posts: { handle: string; role: string; weight: number; ago: string; text: string; tag: Tag }[];
}

const SCENARIOS: Scenario[] = [
  {
    id: "agree",
    label: "Positive consensus",
    split: [72, 18, 10],
    accounts: 12,
    hype: 1.2,
    adjust: 6,
    tone: "ok",
    note: "Most credible voices agree and chatter is at a normal level, so the system adds a small bonus.",
    posts: [
      { handle: "@semis_desk_example", role: "Analyst", weight: 0.8, ago: "3h ago", text: "Commercial customer orders keep growing", tag: "pos" },
      { handle: "@macro_notes_example", role: "Economist", weight: 0.7, ago: "6h ago", text: "Earnings trend is in line with market expectations", tag: "pos" },
      { handle: "@value_lens_example", role: "Value investor", weight: 0.6, ago: "9h ago", text: "Getting pricey, but not yet worrying", tag: "neu" },
    ],
  },
  {
    id: "hype",
    label: "Overhyped",
    split: [81, 11, 8],
    accounts: 12,
    hype: 4.5,
    adjust: -7,
    tone: "warn",
    note: "Sentiment is positive but post volume is far above normal, which risks chasing the crowd, so the system deducts points.",
    posts: [
      { handle: "@momo_trader_example", role: "Trader", weight: 0.3, ago: "1h ago", text: "Not in yet? Hurry!", tag: "pos" },
      { handle: "@semis_desk_example", role: "Analyst", weight: 0.8, ago: "4h ago", text: "Good news, but the price already reflects much of it", tag: "neu" },
      { handle: "@meme_hub_example", role: "Online community", weight: 0.2, ago: "5h ago", text: "Send it all the way!", tag: "pos" },
    ],
  },
  {
    id: "split",
    label: "Split opinion",
    split: [45, 20, 35],
    accounts: 12,
    hype: 1.8,
    adjust: -3,
    tone: "warn",
    note: "Credible voices are clearly split into two camps. The system deducts a few points and shows both views on the card.",
    posts: [
      { handle: "@semis_desk_example", role: "Analyst", weight: 0.8, ago: "4h ago", text: "Commercial customer growth is becoming clear", tag: "pos" },
      { handle: "@value_lens_example", role: "Value investor", weight: 0.7, ago: "7h ago", text: "P/E is far above peers, with almost no margin of safety", tag: "neg" },
      { handle: "@market_wrap_example", role: "Financial media", weight: 0.5, ago: "10h ago", text: "Institutional investors still disagree on valuation", tag: "neu" },
    ],
  },
];

const TAG_LABEL: Record<Tag, string> = { pos: "Positive", neu: "Neutral", neg: "Negative" };
const TAG_STYLE: Record<Tag, string> = {
  pos: "border-primary-fixed-dim text-primary",
  neu: "border-outline-variant text-on-surface-variant",
  neg: "border-error text-error",
};

export function SocialSentiment({ ticker, priceScore }: { ticker: string; priceScore: number }) {
  const [active, setActive] = useState(SCENARIOS[2].id);
  const s = SCENARIOS.find((x) => x.id === active) ?? SCENARIOS[2];
  const total = priceScore + s.adjust;
  const sign = s.adjust > 0 ? "+" : s.adjust < 0 ? "−" : "";

  return (
    <section className="relative flex flex-col gap-space-md overflow-hidden rounded-md border border-outline-variant bg-surface-container-lowest p-space-md">
      {/* Mock panel: no real social data feed exists (X was dropped). Watermark keeps it from reading as real. */}
      <div aria-hidden className="pointer-events-none absolute inset-0 z-10 flex select-none items-center justify-center">
        <span className="-rotate-12 font-headline-md text-[clamp(3rem,14vw,7rem)] font-bold tracking-widest text-on-surface/10">
          SAMPLE
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-space-sm">
        <h3 className="font-title-md text-title-md text-on-surface">
          Social sentiment · {ticker}
        </h3>
        <span className="rounded-full border border-outline-variant px-2.5 py-0.5 font-label-code text-label-code text-on-surface-variant">
          Example
        </span>
      </div>

      <div role="tablist" aria-label="Example scenarios" className="flex flex-wrap gap-space-xs">
        {SCENARIOS.map((x) => (
          <button
            key={x.id}
            type="button"
            role="tab"
            aria-selected={x.id === s.id}
            onClick={() => setActive(x.id)}
            className={`rounded-md border px-space-md py-1.5 font-body-sm text-body-sm transition-colors ${
              x.id === s.id
                ? "border-primary-fixed-dim bg-primary-fixed text-on-primary-fixed"
                : "border-outline-variant bg-surface-container-lowest text-on-surface hover:bg-surface-container-low"
            }`}
          >
            {x.label}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-space-xs">
        <SectionLabel>Sentiment direction (24h)</SectionLabel>
        <div className="flex h-3 overflow-hidden rounded-full" role="img"
          aria-label={`Positive ${s.split[0]}%, neutral ${s.split[1]}%, negative ${s.split[2]}%`}>
          <div className="bg-primary-fixed-dim" style={{ width: `${s.split[0]}%` }} />
          <div className="bg-outline-variant" style={{ width: `${s.split[1]}%` }} />
          <div className="bg-error/70" style={{ width: `${s.split[2]}%` }} />
        </div>
        <div className="flex gap-space-md font-label-code text-label-code text-on-surface-variant">
          <span>Positive {s.split[0]}%</span>
          <span>Neutral {s.split[1]}%</span>
          <span>Negative {s.split[2]}%</span>
        </div>
        <p className="font-body-sm text-body-sm text-on-surface-variant">
          Weighted from {s.accounts} accounts · buzz {s.hype}x normal
        </p>
      </div>

      <div className="flex flex-col gap-space-xs">
        <SectionLabel>Adjusted score</SectionLabel>
        <dl className="grid grid-cols-[1fr_auto] gap-x-space-lg gap-y-1 font-body-md text-body-md">
          <dt className="text-on-surface">Price score</dt>
          <dd className="text-right text-on-surface">{priceScore}</dd>
          <dt className="text-on-surface">Social adjustment (cap ±10)</dt>
          <dd className={`text-right ${s.adjust < 0 ? "text-error" : "text-primary"}`}>
            {sign}{Math.abs(s.adjust)}
          </dd>
          <dt className="border-t border-outline-variant pt-1 font-semibold text-on-surface">Total score</dt>
          <dd className="border-t border-outline-variant pt-1 text-right font-headline-sm text-headline-sm text-on-surface">
            {total}
          </dd>
        </dl>
      </div>

      <p
        className={`rounded-md p-space-md font-body-sm text-body-sm ${
          s.tone === "warn"
            ? "bg-provenance-warning-bg text-provenance-warning-text"
            : "bg-provenance-input-bg text-provenance-input-text"
        }`}
      >
        {s.note}
      </p>

      <div className="flex flex-col gap-space-xs">
        <SectionLabel>Posts picked by the system</SectionLabel>
        <ul className="flex flex-col divide-y divide-surface-container-high">
          {s.posts.map((p) => (
            <li key={p.handle + p.text} className="flex items-start justify-between gap-space-md py-space-sm">
              <div className="flex min-w-0 flex-col gap-1">
                <span className="font-label-code text-label-code text-on-surface-variant">
                  {p.handle} · {p.role} · weight {p.weight} · {p.ago}
                </span>
                <span className="font-body-md text-body-md text-on-surface">{p.text}</span>
              </div>
              <span className={`shrink-0 rounded-full border px-2.5 py-0.5 font-label-code text-label-code ${TAG_STYLE[p.tag]}`}>
                {TAG_LABEL[p.tag]}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <p className="font-body-sm text-body-sm text-on-surface-variant">
        Everything in this section is example data. No social source is connected yet, and it does not change the real score of this stock.
      </p>
    </section>
  );
}
