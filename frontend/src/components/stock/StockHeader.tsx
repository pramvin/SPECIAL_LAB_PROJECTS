import Link from "next/link";
import { Icon } from "@/components/ui/Icon";
import type { Horizon } from "@/lib/recommendations";

const usd = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });

const TABS: { value: Horizon; label: string }[] = [
  { value: "1w", label: "1 week" },
  { value: "1m", label: "1 month" },
  { value: "3m", label: "3 months" },
];

export function StockHeader({
  ticker,
  name,
  price,
  change,
  changePct,
  asOf,
  horizon,
}: {
  ticker: string;
  name: string;
  price: number;
  change: number;
  changePct: number;
  asOf: string | null;
  horizon: Horizon;
}) {
  const up = changePct >= 0;
  return (
    <header className="flex flex-col gap-5">
      <Link
        href="/"
        className="inline-flex w-fit items-center gap-1 font-body-sm text-body-sm font-medium text-on-surface-variant hover:text-on-surface"
      >
        <Icon name="arrow_back" className="text-[16px]" />
        All ideas
      </Link>

      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="font-headline-lg text-headline-lg-mobile tracking-tight text-on-surface sm:text-headline-lg">
            {ticker}
          </h1>
          <p className="font-body-lg text-body-lg text-on-surface-variant">
            {name}
          </p>
        </div>
        <div className="flex flex-col md:items-end">
          <span className="font-metric-xl text-metric-xl tabular-nums text-on-surface">
            {usd(price)}
          </span>
          <span
            className={`font-body-md text-body-md font-semibold tabular-nums ${
              up ? "text-green-700" : "text-error"
            }`}
          >
            {up ? "+" : "−"}
            {usd(Math.abs(change))} ({up ? "+" : "−"}
            {Math.abs(changePct).toFixed(2)}%)
          </span>
          {asOf && (
            <span className="text-[12.5px] text-on-surface-variant">
              Last close {asOf} · not a live price
            </span>
          )}
        </div>
      </div>

      <nav aria-label="Analysis horizon" className="flex flex-wrap items-center gap-2">
        {TABS.map((tab) =>
          tab.value === "1w" ? (
            <Link
              key={tab.value}
              href={`/stock/${encodeURIComponent(ticker)}?h=1w`}
              aria-current={horizon === "1w" ? "page" : undefined}
              className={`rounded-full px-5 py-2.5 font-body-sm text-body-sm font-medium transition-colors ${
                horizon === "1w"
                  ? "bg-on-surface text-white"
                  : "bg-surface-container-low text-on-surface hover:bg-surface-container-high"
              }`}
            >
              {tab.label}
            </Link>
          ) : (
            <span
              key={tab.value}
              aria-disabled="true"
              title={`${tab.label} is coming soon`}
              className="inline-flex cursor-not-allowed items-center gap-2 rounded-full bg-surface-container-low px-5 py-2.5 font-body-sm text-body-sm font-medium text-on-surface-variant opacity-60"
            >
              {tab.label}
              <span className="rounded-full border border-surface-container-high bg-white px-2 py-0.5 text-[11px] font-semibold">
                Coming soon
              </span>
            </span>
          ),
        )}
      </nav>
    </header>
  );
}
