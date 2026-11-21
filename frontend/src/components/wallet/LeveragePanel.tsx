"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { formatCurrency, formatPercent } from "@/lib/format";
import type { PositionPreview } from "@/lib/wallet";

// Must match LEVERAGE_OPTIONS in Backend/app/trading.py
const LEVERAGE_OPTIONS = [5, 10, 50, 100];

const money = (v: number, sign = false) =>
  formatCurrency(v, { decimals: 2, sign });
const pct = (v: number) => formatPercent(v, { decimals: 2, sign: true });
const SHOWN_MOVES = [-5, -1, 1, 5];

function tone(v: number) {
  return v > 0
    ? "text-provenance-input-text"
    : v < 0
      ? "text-error"
      : "text-on-surface-variant";
}

type Result =
  | { key: string; data: PositionPreview }
  | { key: string; error: string };

/**
 * x5 / x10 / x50 / x100 picker. Once ticker + margin are filled in it asks the
 * backend how the SAME margin behaves at every leverage (position size,
 * liquidation price, P/L for a few price moves) so the maths lives in one place.
 */
export function LeveragePanel({
  ticker,
  side,
  amount,
  leverage,
  onChange,
}: {
  ticker: string;
  side: "long" | "short";
  amount: string;
  leverage: number;
  onChange: (leverage: number) => void;
}) {
  const [result, setResult] = useState<Result | null>(null);

  const amountNumber = Number(amount);
  const valid =
    /^[A-Z0-9.\-^=]{1,12}$/.test(ticker) &&
    Number.isFinite(amountNumber) &&
    amountNumber > 0 &&
    /^\d+(\.\d{1,2})?$/.test(amount.trim());
  const key = valid ? `${ticker}|${side}|${amountNumber}` : "";

  useEffect(() => {
    if (!key) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const qs = new URLSearchParams({
          ticker,
          side,
          amount: String(amountNumber),
        });
        const res = await fetch(`/api/positions/preview?${qs}`, {
          signal: controller.signal,
          cache: "no-store",
        });
        const body = await res.json().catch(() => ({}));
        setResult(
          res.ok
            ? { key, data: body as PositionPreview }
            : { key, error: body?.detail ?? "Could not load preview." },
        );
      } catch {
        if (!controller.signal.aborted)
          setResult({ key, error: "Could not load preview." });
      }
    }, 400);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [key, ticker, side, amountNumber]);

  const current = key && result?.key === key ? result : null;
  const preview = current && "data" in current ? current.data : null;
  const chosen = preview?.options.find((o) => o.leverage === leverage);

  return (
    <div className="flex flex-col gap-3">
      <span className="font-body-sm text-body-sm font-medium text-on-surface-variant">
        Leverage
      </span>
      <div className="grid grid-cols-4 gap-2" role="group" aria-label="Leverage">
        {LEVERAGE_OPTIONS.map((lev) => (
          <button
            key={lev}
            type="button"
            aria-pressed={leverage === lev}
            onClick={() => onChange(lev)}
            className={`flex flex-col items-center rounded-xl border px-2 py-3 transition-colors ${
              leverage === lev
                ? "border-tertiary-accent bg-primary-fixed text-on-primary-fixed"
                : "border-surface-container-high text-on-surface hover:bg-surface-container-low"
            }`}
          >
            <span className="font-title-md text-title-md">x{lev}</span>
            <span className="font-body-sm text-[11px] text-on-surface-variant">
              wiped at {100 / lev}%
            </span>
          </button>
        ))}
      </div>

      {!valid && (
        <p className="font-body-sm text-body-sm text-on-surface-variant">
          Enter a ticker and a margin amount (max 2 decimals) to see how the
          position changes at each leverage.
        </p>
      )}
      {valid && !current && (
        <p className="font-body-sm text-body-sm text-on-surface-variant">
          Loading preview…
        </p>
      )}
      {current && "error" in current && (
        <p role="alert" className="font-body-sm text-body-sm text-error">
          {current.error}
        </p>
      )}

      {preview && chosen && (
        <div className="flex flex-col gap-3 rounded-xl bg-surface-container-low p-4">
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ["Deducted now", money(preview.amount)],
              ["Balance after", money(preview.balance_after_open)],
              [`Position size (x${chosen.leverage})`, money(chosen.notional)],
              ["Liquidation price", money(chosen.liquidation_price)],
            ].map(([label, value]) => (
              <div key={label} className="flex flex-col gap-1">
                <dt className="font-body-sm text-[12px] text-on-surface-variant">
                  {label}
                </dt>
                <dd className="font-title-md text-title-md tabular-nums text-on-surface">
                  {value}
                </dd>
              </div>
            ))}
          </dl>
          <p className="font-body-sm text-body-sm text-on-surface-variant">
            Entry ≈ {money(preview.entry_price)} · {chosen.quantity} shares ·
            a {chosen.liquidation_move_pct}% move against you wipes out the
            margin.
            {preview.price_is_stale && " (Price may be delayed.)"}
          </p>
          {!preview.affordable && (
            <Badge tone="warning" icon="warning">
              Margin is more than your wallet balance
            </Badge>
          )}

          <div className="overflow-x-auto">
            <table className="w-full min-w-[460px] text-left font-body-sm text-body-sm">
              <caption className="pb-2 text-left text-[12px] text-on-surface-variant">
                P/L on {money(preview.amount)} margin if the {preview.ticker}{" "}
                price moves ({preview.side})
              </caption>
              <thead>
                <tr className="text-on-surface-variant">
                  <th className="py-1 pr-3 font-medium">Leverage</th>
                  <th className="py-1 pr-3 font-medium">Size</th>
                  <th className="py-1 pr-3 font-medium">Liquidated at</th>
                  {SHOWN_MOVES.map((m) => (
                    <th key={m} className="py-1 pr-3 font-medium tabular-nums">
                      {m > 0 ? "+" : ""}
                      {m}%
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.options.map((row) => (
                  <tr
                    key={row.leverage}
                    className={
                      row.leverage === leverage
                        ? "bg-primary-fixed font-medium"
                        : ""
                    }
                  >
                    <td className="py-1.5 pr-3">x{row.leverage}</td>
                    <td className="py-1.5 pr-3 tabular-nums">
                      {money(row.notional)}
                    </td>
                    <td className="py-1.5 pr-3 tabular-nums">
                      {money(row.liquidation_price)}
                    </td>
                    {SHOWN_MOVES.map((m) => {
                      const s = row.scenarios.find(
                        (x) => x.price_move_pct === m,
                      );
                      return (
                        <td
                          key={m}
                          className={`py-1.5 pr-3 tabular-nums ${s ? tone(s.pnl) : ""}`}
                        >
                          {s ? (
                            <>
                              {money(s.pnl, true)}
                              <span className="block text-[11px]">
                                {pct(s.pnl_pct)}
                              </span>
                            </>
                          ) : (
                            "—"
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}