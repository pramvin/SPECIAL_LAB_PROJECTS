"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Icon } from "@/components/ui/Icon";
import type { Position } from "@/lib/wallet";

const usd = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });
const signed = (n: number) => `${n < 0 ? "−" : "+"}${usd(Math.abs(n))}`;

async function call(path: string, method: string, body?: unknown) {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = (await res.json().catch(() => null)) as { detail?: unknown } | null;
  if (!res.ok) {
    throw new Error(
      typeof data?.detail === "string" ? data.detail : `Request failed (${res.status})`,
    );
  }
}

function useRefresh() {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  return { pending, refresh: () => startTransition(() => router.refresh()) };
}

export function WatchButton({
  ticker,
  watching,
}: {
  ticker: string;
  watching: boolean;
}) {
  const { pending, refresh } = useRefresh();
  const [on, setOn] = useState(watching);
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    const next = !on;
    setOn(next);
    setError(null);
    try {
      if (next) await call("/api/watchlist", "POST", { ticker });
      else await call(`/api/watchlist/${ticker}`, "DELETE");
      refresh();
    } catch (e) {
      setOn(!next);
      setError(e instanceof Error ? e.message : "Could not update the watchlist.");
    }
  }

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={pending}
      aria-pressed={on}
      title={error ?? undefined}
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 font-body-sm text-body-sm font-semibold ${
        on
          ? "border-amber-200 bg-amber-50 text-amber-800"
          : "border-surface-container-high bg-white text-on-surface"
      } ${error ? "ring-1 ring-error" : ""}`}
    >
      <Icon name="star" className={`text-[16px] ${on ? "text-amber-500" : ""}`} />
      {on ? "Watching" : "Watch"}
    </button>
  );
}

const QUICK = [10, 20, 50];

export function TradeRow({
  ticker,
  entry,
  stop,
  target,
  positionPct,
  balance,
  position,
  livePrice,
}: {
  ticker: string;
  entry: number;
  stop: number;
  target: number;
  positionPct: number;
  balance: number;
  position: Position | null;
  livePrice: number | null;
}) {
  const { pending, refresh } = useRefresh();
  const suggested = Math.max(1, Math.floor((balance * positionPct) / 100));
  const [open, setOpen] = useState(false);
  const [amount, setAmount] = useState(String(suggested));
  const [leverage, setLeverage] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      setOpen(false);
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed.");
    } finally {
      setBusy(false);
    }
  }

  if (position) {
    const now = position.current_price ?? livePrice;
    const pnl = position.unrealized_pnl;
    return (
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3 border-t border-surface-container-high pt-5">
        <span className="rounded-lg bg-green-50 px-2.5 py-1 text-[12px] font-bold uppercase text-green-700">
          You hold · {position.side} {position.leverage}x
        </span>
        <Metric label="Invested" value={usd(position.amount_deducted)} />
        <Metric label="Entry" value={usd(position.entry_price)} />
        <Metric label="Now" value={now === null ? "—" : usd(now)} />
        <Metric
          label="Unrealized P/L"
          value={
            pnl === null
              ? "—"
              : `${signed(pnl)} (${position.unrealized_pnl_pct?.toFixed(2)}%)`
          }
          tone={pnl !== null && pnl < 0 ? "text-error" : "text-green-700"}
        />
        <span className="flex-1" />
        <button
          type="button"
          disabled={busy || pending}
          onClick={() =>
            run(() => call(`/api/positions/${position.id}/close`, "POST"))
          }
          className="rounded-xl bg-red-50 px-4 py-2.5 font-body-sm text-body-sm font-semibold text-error disabled:opacity-60"
        >
          Close position
        </button>
        {error && <p className="w-full text-body-sm text-error">{error}</p>}
      </div>
    );
  }

  const value = Number(amount);
  const valid = Number.isFinite(value) && value > 0 && value <= balance;
  const notional = valid ? value * leverage : 0;
  const lossAtStop = (notional * (stop - entry)) / entry;
  const gainAtTarget = (notional * (target - entry)) / entry;

  if (!open) {
    return (
      <div className="flex flex-wrap items-center gap-3 border-t border-surface-container-high pt-5">
        <button
          type="button"
          onClick={() => setOpen(true)}
          disabled={balance < 1}
          className="rounded-xl bg-on-surface px-5 py-2.5 font-body-sm text-body-sm font-semibold text-white disabled:opacity-50"
        >
          Open position
        </button>
        <span className="font-body-sm text-body-sm text-on-surface-variant">
          Suggested: <b className="text-on-surface">{usd(suggested)}</b> ({positionPct}%
          of balance)
        </span>
        <span className="flex-1" />
        <span className="font-body-sm text-body-sm text-on-surface-variant">
          Available <b className="text-on-surface">{usd(balance)}</b>
        </span>
      </div>
    );
  }

  return (
    <div className="grid gap-5 rounded-2xl bg-surface-container-low p-5 md:grid-cols-[1.2fr_1fr]">
      <div className="flex flex-col gap-4">
        <h3 className="font-title-md text-title-md text-on-surface">
          Open a paper position in {ticker}
        </h3>
        <label className="flex flex-col gap-1.5 font-body-sm text-body-sm text-on-surface-variant">
          Amount (cash margin) · Long only
          <input
            type="number"
            min={1}
            max={balance}
            step="1"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="rounded-xl border border-surface-container-high bg-white px-3 py-2 text-[16px] font-semibold tabular-nums text-on-surface"
          />
        </label>
        <div className="flex flex-wrap gap-2">
          {QUICK.map((pct) => (
            <button
              key={pct}
              type="button"
              onClick={() => setAmount(String(Math.max(1, Math.floor((balance * pct) / 100))))}
              className="rounded-full border border-surface-container-high bg-white px-3 py-1 text-[12.5px] font-semibold"
            >
              {pct}%
            </button>
          ))}
          <button
            type="button"
            onClick={() => setAmount(String(Math.floor(balance * 100) / 100))}
            className="rounded-full border border-surface-container-high bg-white px-3 py-1 text-[12.5px] font-semibold"
          >
            Max
          </button>
        </div>
        <label className="flex flex-col gap-1.5 font-body-sm text-body-sm text-on-surface-variant">
          <span>
            Leverage: <b className="text-on-surface">{leverage}x</b>
            {leverage === 1 ? " · no leverage" : " · losses grow with leverage"}
          </span>
          <input
            type="range"
            min={1}
            max={10}
            step={1}
            value={leverage}
            onChange={(e) => setLeverage(Number(e.target.value))}
          />
        </label>
      </div>
      <div className="flex flex-col gap-3">
        <dl className="flex flex-col gap-1.5 rounded-2xl bg-white p-4 font-body-sm text-body-sm">
          <Row label="Entry price (card)" value={usd(entry)} />
          <Row label="Notional" value={usd(notional)} />
          <Row label="Quantity" value={`${(notional / entry).toFixed(3)} shares`} />
          <Row label="Balance after" value={usd(balance - (valid ? value : 0))} />
          <Row
            label={`If stop hit (${usd(stop)})`}
            value={signed(lossAtStop)}
            tone="text-error"
            strong
          />
          <Row
            label={`If target hit (${usd(target)})`}
            value={signed(gainAtTarget)}
            tone="text-green-700"
            strong
          />
        </dl>
        <p className="rounded-xl bg-amber-50 px-3 py-2 text-[12.5px] text-amber-800">
          Paper money. The fill uses the latest daily close in our data, so it can
          differ from the card price. Stop and target are guides only: positions do
          not close by themselves.
          {leverage > 1 && " With leverage you can lose more than the margin."}
        </p>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="flex-1 rounded-xl bg-white px-4 py-2.5 font-body-sm text-body-sm font-semibold"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!valid || busy || pending}
            onClick={() =>
              run(() =>
                call("/api/positions", "POST", {
                  ticker,
                  side: "long",
                  amount: value,
                  leverage,
                }),
              )
            }
            className="flex-1 rounded-xl bg-green-700 px-4 py-2.5 font-body-sm text-body-sm font-semibold text-white disabled:opacity-50"
          >
            Confirm Long {valid ? usd(value) : ""}
          </button>
        </div>
        {!valid && amount !== "" && (
          <p className="text-body-sm text-error">
            Amount must be more than $0 and at most your balance.
          </p>
        )}
        {error && <p className="text-body-sm text-error">{error}</p>}
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  tone = "text-on-surface",
}: {
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div className="flex flex-col">
      <small className="text-[12px] text-on-surface-variant">{label}</small>
      <b className={`text-[16px] tabular-nums ${tone}`}>{value}</b>
    </div>
  );
}

function Row({
  label,
  value,
  tone = "text-on-surface",
  strong = false,
}: {
  label: string;
  value: string;
  tone?: string;
  strong?: boolean;
}) {
  return (
    <div className={`flex justify-between ${strong ? "font-bold" : ""}`}>
      <dt className="font-normal text-on-surface-variant">{label}</dt>
      <dd className={`tabular-nums ${tone}`}>{value}</dd>
    </div>
  );
}
