"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { TextInput } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { NoticeBanner } from "@/components/ui/NoticeBanner";
import type { Instrument, SearchGroup, WatchlistItem } from "@/lib/watchlist";

const SEARCH_GROUPS: { value: SearchGroup; label: string }[] = [
  { value: "all", label: "All" },
  { value: "sp500", label: "S&P 500" },
  { value: "etf", label: "SCHD & QQQ" },
];

const usd = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });

function Quote({ i }: { i: Instrument }) {
  if (i.price === null) {
    return (
      <span className="font-label-code text-label-code text-on-surface-variant">
        No price data
      </span>
    );
  }
  const up = (i.change ?? 0) >= 0;
  const sign = up ? "+" : "−";
  return (
    <span
      title={`Last close${i.price_date ? ` on ${i.price_date}` : ""}`}
      className="flex flex-col items-end font-label-code text-label-code tabular-nums"
    >
      <span className="text-on-surface">{usd(i.price)}</span>
      {i.change !== null && i.change_pct !== null && (
        <span className={up ? "text-primary" : "text-error"}>
          {sign}${Math.abs(i.change).toFixed(2)} ({sign}
          {Math.abs(i.change_pct).toFixed(2)}%)
        </span>
      )}
    </span>
  );
}

function Row({
  i,
  saved,
  busy,
  onToggle,
  inList = false,
}: {
  i: Instrument;
  saved: boolean;
  busy: boolean;
  onToggle: () => void;
  inList?: boolean;
}) {
  return (
    <li className="flex items-center gap-space-md py-space-sm first:pt-0 last:pb-0">
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-space-xs">
          <span className="font-title-md text-title-md text-on-surface">
            {i.ticker}
          </span>
          <Badge tone={i.kind === "etf" ? "info" : "neutral"}>
            {i.kind === "etf" ? "ETF" : "S&P 500"}
          </Badge>
        </div>
        <span className="truncate font-body-sm text-body-sm text-on-surface-variant">
          {i.name}
          {i.gics_sector ? ` · ${i.gics_sector}` : ""}
        </span>
      </div>
      <Quote i={i} />
      <Button
        variant={saved ? "subtle" : "secondary"}
        size="sm"
        icon={saved ? (inList ? "close" : "star") : "star_outline"}
        disabled={busy}
        onClick={onToggle}
        aria-pressed={saved}
        aria-label={`${saved ? "Remove" : "Add"} ${i.ticker} ${saved ? "from" : "to"} watchlist`}
      >
        {saved ? (inList ? "Remove" : "Saved") : "Add"}
      </Button>
    </li>
  );
}

export function WatchlistView({ initial }: { initial: WatchlistItem[] | null }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState<SearchGroup>("all");
  const [results, setResults] = useState<Instrument[]>([]);
  const [searching, setSearching] = useState(true);
  const [searchError, setSearchError] = useState("");
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>(initial ?? []);
  const [pending, setPending] = useState<Set<string>>(new Set());
  const [actionError, setActionError] = useState("");

  const saved = new Set(watchlist.map((w) => w.ticker));

  // Debounced search; a newer keystroke cancels the older request.
  useEffect(() => {
    const ctrl = new AbortController();
    const timer = setTimeout(
      async () => {
        setSearching(true);
        try {
          const params = new URLSearchParams({ q: query.trim(), group });
          const res = await fetch(`/api/search?${params}`, {
            signal: ctrl.signal,
          });
          if (res.status === 401) {
            router.replace("/login");
            return;
          }
          if (!res.ok) throw new Error(String(res.status));
          const data = (await res.json()) as { items: Instrument[] };
          setResults(data.items);
          setSearchError("");
        } catch {
          if (!ctrl.signal.aborted) {
            setSearchError("Search failed. Is the backend running?");
          }
        } finally {
          if (!ctrl.signal.aborted) setSearching(false);
        }
      },
      query ? 250 : 0,
    );
    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [query, group, router]);

  function setBusy(ticker: string, on: boolean) {
    setPending((p) => {
      const next = new Set(p);
      if (on) next.add(ticker);
      else next.delete(ticker);
      return next;
    });
  }

  async function toggle(i: Instrument) {
    const removing = saved.has(i.ticker);
    setBusy(i.ticker, true);
    setActionError("");
    try {
      const res = await fetch(
        removing
          ? `/api/watchlist/${encodeURIComponent(i.ticker)}`
          : "/api/watchlist",
        removing
          ? { method: "DELETE" }
          : {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ ticker: i.ticker }),
            },
      );
      if (res.status === 401) {
        router.replace("/login");
        return;
      }
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setActionError(
          typeof body?.detail === "string"
            ? body.detail
            : "Could not update the watchlist.",
        );
        return;
      }
      if (removing) {
        setWatchlist((w) => w.filter((x) => x.ticker !== i.ticker));
      } else {
        const item = (await res.json()) as WatchlistItem;
        setWatchlist((w) =>
          w.some((x) => x.ticker === item.ticker) ? w : [item, ...w],
        );
      }
    } catch {
      setActionError("Cannot reach the server. Is the backend running?");
    } finally {
      setBusy(i.ticker, false);
    }
  }

  return (
    <div className="flex flex-col gap-space-lg">
      <div className="flex flex-col gap-1">
        <h1 className="font-headline-md text-headline-md text-on-surface">
          Search &amp; watchlist
        </h1>
        <p className="font-body-md text-body-md text-on-surface-variant">
          Find S&amp;P 500 stocks and the SCHD and QQQ ETFs, and keep the ones
          you want to follow. Your list is saved to your account.
        </p>
      </div>

      <NoticeBanner icon="info" tone="neutral" title="A reading list, not advice">
        Prices are the last daily close in our database, not live quotes. An ETF
        shows no price until its price history is loaded. Saving a ticker is not
        a recommendation.
      </NoticeBanner>

      {actionError && (
        <p role="alert" className="font-body-md text-body-md text-error">
          {actionError}
        </p>
      )}

      <div className="grid gap-space-lg lg:grid-cols-2">
        <Card className="flex flex-col gap-space-md">
          <CardHeader title="Search" icon="search" />
          <div className="flex flex-col gap-space-sm">
            <TextInput
              type="search"
              aria-label="Search by ticker or company name"
              placeholder="Ticker or company, e.g. AAPL or Microsoft"
              autoComplete="off"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div
              role="group"
              aria-label="Search in"
              className="flex flex-wrap gap-space-xs"
            >
              {SEARCH_GROUPS.map((g) => (
                <button
                  key={g.value}
                  type="button"
                  aria-pressed={group === g.value}
                  onClick={() => setGroup(g.value)}
                  className={`rounded-md px-space-md py-1.5 font-body-sm text-body-sm font-medium transition-colors ${
                    group === g.value
                      ? "bg-primary-container text-on-primary"
                      : "bg-surface-container-low text-on-surface hover:bg-surface-container-high"
                  }`}
                >
                  {g.label}
                </button>
              ))}
            </div>
          </div>

          {searchError && (
            <p role="alert" className="font-body-md text-body-md text-error">
              {searchError}
            </p>
          )}
          {!searchError && (
            <p
              aria-live="polite"
              className="font-body-sm text-body-sm text-on-surface-variant"
            >
              {searching
                ? "Searching…"
                : results.length === 0
                  ? "No matches."
                  : query
                    ? `${results.length} result${results.length === 1 ? "" : "s"}`
                    : "Showing the first matches. Type to narrow down."}
            </p>
          )}
          <ul className="flex flex-col divide-y divide-surface-container-high">
            {results.map((i) => (
              <Row
                key={i.ticker}
                i={i}
                saved={saved.has(i.ticker)}
                busy={pending.has(i.ticker)}
                onToggle={() => toggle(i)}
              />
            ))}
          </ul>
        </Card>

        <Card className="flex flex-col gap-space-md">
          <CardHeader
            title="Your watchlist"
            icon="star"
            subtitle={`${watchlist.length} saved`}
          />
          {initial === null && (
            <p role="alert" className="font-body-md text-body-md text-error">
              Could not load your saved list. Is the backend running?
            </p>
          )}
          {initial !== null && watchlist.length === 0 && (
            <p className="flex items-center gap-space-xs font-body-md text-body-md text-on-surface-variant">
              <Icon name="star_outline" className="text-[20px]" />
              Nothing saved yet. Use Add on a search result.
            </p>
          )}
          <ul className="flex flex-col divide-y divide-surface-container-high">
            {watchlist.map((w) => (
              <Row
                key={w.ticker}
                i={w}
                saved
                inList
                busy={pending.has(w.ticker)}
                onToggle={() => toggle(w)}
              />
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}