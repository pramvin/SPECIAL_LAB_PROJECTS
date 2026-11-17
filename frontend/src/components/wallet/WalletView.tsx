"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, SectionLabel } from "@/components/ui/Card";
import { Field, TextInput } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { LineChart } from "@/components/ui/LineChart";
import { NoticeBanner } from "@/components/ui/NoticeBanner";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { formatCurrency, formatPercent } from "@/lib/format";
import type {
  Position,
  Trade,
  WalletData,
  WalletTransaction,
} from "@/lib/wallet";

function money(value: number, sign = false): string {
  return formatCurrency(value, { decimals: 2, sign });
}

function percent(value: number): string {
  return formatPercent(value, { decimals: 2, sign: true });
}

function formatTime(epoch: number): string {
  return `${new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(new Date(epoch * 1000))} UTC`;
}

function toneFor(value: number): string {
  return value > 0
    ? "text-provenance-input-text"
    : value < 0
      ? "text-error"
      : "text-on-surface-variant";
}

function SideBadge({ side }: { side: Position["side"] }) {
  return (
    <Badge
      tone={side === "long" ? "success" : "info"}
      icon={side === "long" ? "trending_up" : "trending_down"}
    >
      {side === "long" ? "Long" : "Short"}
    </Badge>
  );
}

function EmptyState({ icon, text }: { icon: string; text: string }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl bg-surface-container-low px-4 py-8 text-center">
      <Icon name={icon} className="text-[26px] text-on-surface-variant" />
      <p className="font-body-sm text-body-sm text-on-surface-variant">{text}</p>
    </div>
  );
}

function TransactionRow({ tx }: { tx: WalletTransaction }) {
  const deposit = tx.kind === "deposit";
  return (
    <li className="flex flex-wrap items-start justify-between gap-3 py-4 first:pt-0 last:pb-0">
      <div className="flex items-start gap-3">
        <span
          className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
            deposit
              ? "bg-provenance-input-bg text-provenance-input-text"
              : "bg-surface-container-low text-on-surface-variant"
          }`}
        >
          <Icon name={deposit ? "add" : "remove"} className="text-[18px]" />
        </span>
        <div className="flex flex-col gap-1">
          <span className="font-title-md text-title-md text-on-surface">
            {deposit ? "Deposit" : "Withdrawal"}
          </span>
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            {formatTime(tx.created_at)}
            {tx.note ? ` · ${tx.note}` : ""}
          </span>
        </div>
      </div>
      <div className="text-right">
        <div
          className={`font-title-md text-title-md tabular-nums ${
            deposit ? "text-provenance-input-text" : "text-on-surface"
          }`}
        >
          {deposit ? "+" : "−"}
          {money(tx.amount)}
        </div>
        <div className="font-body-sm text-body-sm text-on-surface-variant">
          Balance {money(tx.balance_after)}
        </div>
      </div>
    </li>
  );
}

function PositionRow({
  position,
  closing,
  onClose,
}: {
  position: Position;
  closing: boolean;
  onClose: () => void;
}) {
  const pnl = position.unrealized_pnl;
  return (
    <li className="flex flex-col gap-4 rounded-xl bg-surface-container-low p-4 first:mt-0 last:mb-0">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-title-md text-title-md text-on-surface">
              {position.ticker}
            </span>
            <SideBadge side={position.side} />
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              {position.leverage.toFixed(2)}x
            </span>
          </div>
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            Entry {money(position.entry_price)} · Current{" "}
            {position.current_price === null
              ? "—"
              : money(position.current_price)}
          </span>
        </div>
        <Button
          variant="secondary"
          size="sm"
          icon="close"
          disabled={closing}
          onClick={onClose}
        >
          {closing ? "Closing…" : "Close"}
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="flex flex-col gap-1">
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            Quantity
          </span>
          <span className="font-title-md text-title-md tabular-nums text-on-surface">
            {position.quantity.toFixed(4)}
          </span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            Margin
          </span>
          <span className="font-title-md text-title-md tabular-nums text-on-surface">
            {money(position.amount_deducted)}
          </span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            Notional
          </span>
          <span className="font-title-md text-title-md tabular-nums text-on-surface">
            {money(position.notional)}
          </span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            Unrealized P/L
          </span>
          <span
            className={`font-title-md text-title-md tabular-nums ${
              pnl === null ? "text-on-surface-variant" : toneFor(pnl)
            }`}
          >
            {pnl === null ? "No price" : money(pnl, true)}
          </span>
          {position.unrealized_pnl_pct !== null && (
            <span className={`font-body-sm text-body-sm ${toneFor(pnl ?? 0)}`}>
              {percent(position.unrealized_pnl_pct)}
            </span>
          )}
        </div>
      </div>
    </li>
  );
}

function TradeRow({ trade }: { trade: Trade }) {
  return (
    <li className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-start sm:justify-between">
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-title-md text-title-md text-on-surface">
            {trade.ticker}
          </span>
          <SideBadge side={trade.side} />
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            {trade.leverage.toFixed(2)}x
          </span>
        </div>
        <span className="font-body-sm text-body-sm text-on-surface-variant">
          {money(trade.entry_price)} → {money(trade.exit_price)} ·{" "}
          {formatTime(trade.closed_at)}
        </span>
      </div>
      <div className="text-right">
        <div
          className={`font-title-md text-title-md tabular-nums ${toneFor(trade.pnl)}`}
        >
          {money(trade.pnl, true)}
        </div>
        <div className={`font-body-sm text-body-sm ${toneFor(trade.pnl)}`}>
          {percent(trade.pnl_pct)}
        </div>
      </div>
    </li>
  );
}

export function WalletView({ initial }: { initial: WalletData }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [mode, setMode] = useState<"deposit" | "withdraw">("deposit");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [ticker, setTicker] = useState("");
  const [side, setSide] = useState<"long" | "short">("long");
  const [tradeAmount, setTradeAmount] = useState("");
  const [leverage, setLeverage] = useState("1");
  const [closingId, setClosingId] = useState<number | null>(null);

  const wallet = initial.wallet;
  const positions = initial.positions;
  const trades = initial.trades;
  const history = initial.history;
  const startingBalance = initial.startingBalance;
  const disabled = busy || pending;

  const realizedPnl = trades.reduce((sum, trade) => sum + trade.pnl, 0);
  const unrealizedPnl = positions.reduce(
    (sum, position) => sum + (position.unrealized_pnl ?? 0),
    0,
  );
  const openMargin = positions.reduce(
    (sum, position) => sum + position.amount_deducted,
    0,
  );
  const balances = history.map((point) => point.balance);

  function refresh() {
    startTransition(() => router.refresh());
  }

  async function postJson(path: string, body: unknown) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (res.status === 401) {
      router.replace("/login");
      throw new Error("Session expired. Sign in again.");
    }
    const data = (await res.json().catch(() => null)) as
      | { detail?: unknown }
      | null;
    if (!res.ok) {
      throw new Error(
        typeof data?.detail === "string"
          ? data.detail
          : `Request failed (${res.status})`,
      );
    }
    return data;
  }

  async function submitFunds(event: React.FormEvent) {
    event.preventDefault();
    const value = Number(amount);
    if (!Number.isFinite(value) || value <= 0) {
      setError("Enter an amount greater than 0.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await postJson(`/api/wallet/${mode}`, {
        amount: value,
        note: note.trim(),
      });
      setAmount("");
      setNote("");
      setNotice(
        mode === "deposit"
          ? "Funds added to your simulated wallet."
          : "Funds withdrawn from your simulated wallet.",
      );
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update wallet.");
    } finally {
      setBusy(false);
    }
  }

  async function openPosition(event: React.FormEvent) {
    event.preventDefault();
    const cleanTicker = ticker.trim().toUpperCase();
    const value = Number(tradeAmount);
    const lev = Number(leverage);
    if (!cleanTicker) {
      setError("Enter a ticker.");
      return;
    }
    if (!Number.isFinite(value) || value <= 0) {
      setError("Enter a margin amount greater than 0.");
      return;
    }
    if (!Number.isFinite(lev) || lev < 1 || lev > 10) {
      setError("Leverage must be between 1 and 10.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await postJson("/api/positions", {
        ticker: cleanTicker,
        side,
        amount: value,
        leverage: lev,
      });
      setTicker("");
      setTradeAmount("");
      setLeverage("1");
      setNotice(`Opened a ${side} position in ${cleanTicker}.`);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open position.");
    } finally {
      setBusy(false);
    }
  }

  async function closePosition(position: Position) {
    setClosingId(position.id);
    setError("");
    setNotice("");
    try {
      await postJson(`/api/positions/${position.id}/close`, {});
      setNotice(`Closed ${position.ticker}.`);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not close position.");
    } finally {
      setClosingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-12 lg:gap-16">
      <header className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <SectionLabel>Simulated portfolio</SectionLabel>
          <ProvenanceBadge provenance="example" label="Simulated" />
        </div>
        <h1 className="max-w-3xl font-headline-lg text-headline-lg-mobile tracking-tight text-on-surface sm:text-headline-lg">
          Wallet
        </h1>
        <p className="max-w-2xl font-body-lg text-body-lg text-on-surface-variant">
          Track your simulated cash, add or withdraw funds, and manage paper
          trades. No real money or orders are involved.
        </p>
      </header>

      {initial.error && (
        <NoticeBanner icon="warning" tone="warning" title="Wallet unavailable">
          {initial.error}
        </NoticeBanner>
      )}

      {wallet && wallet.balance < 0 && (
        <NoticeBanner icon="warning" tone="warning" title="Negative balance">
          Leveraged losses have pushed your simulated cash below zero.
        </NoticeBanner>
      )}

      {notice && (
        <NoticeBanner icon="check_circle" tone="neutral" title="Updated">
          {notice}
        </NoticeBanner>
      )}

      {error && (
        <p role="alert" className="font-body-md text-body-md text-error">
          {error}
        </p>
      )}

      <div className="grid items-start gap-6 lg:grid-cols-[1.35fr_0.65fr]">
        <Card className="flex flex-col gap-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex flex-col gap-2">
              <SectionLabel>Cash balance</SectionLabel>
              <span className="font-metric-xl text-metric-xl tabular-nums text-on-surface">
                {wallet ? money(wallet.balance) : "—"}
              </span>
              <span
                className={`font-body-md text-body-md tabular-nums ${toneFor(wallet?.change ?? 0)}`}
              >
                {wallet ? money(wallet.change, true) : "—"}{" "}
                {wallet ? `(${percent(wallet.change_pct)})` : ""} from{" "}
                {money(startingBalance)}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-right sm:grid-cols-3">
              <div className="flex flex-col gap-1">
                <span className="font-body-sm text-body-sm text-on-surface-variant">
                  Open
                </span>
                <span className="font-title-md text-title-md tabular-nums text-on-surface">
                  {positions.length}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="font-body-sm text-body-sm text-on-surface-variant">
                  Invested margin
                </span>
                <span className="font-title-md text-title-md tabular-nums text-on-surface">
                  {money(openMargin)}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="font-body-sm text-body-sm text-on-surface-variant">
                  Realized P/L
                </span>
                <span
                  className={`font-title-md text-title-md tabular-nums ${toneFor(realizedPnl)}`}
                >
                  {money(realizedPnl, true)}
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-3 border-t border-surface-container-high pt-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <SectionLabel>Balance history</SectionLabel>
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                Unrealized {money(unrealizedPnl, true)}
              </span>
            </div>
            {balances.length >= 2 ? (
              <>
                <LineChart
                  series={[{ points: balances, color: "#0071e3", area: true }]}
                  target={startingBalance}
                  height={180}
                  ariaLabel="Simulated wallet balance history"
                />
                <div className="flex flex-wrap items-center justify-between gap-2 font-body-sm text-body-sm text-on-surface-variant">
                  <span>Start {money(balances[0])}</span>
                  <span className="text-on-surface">
                    Now {money(balances[balances.length - 1])}
                  </span>
                </div>
              </>
            ) : (
              <EmptyState
                icon="show_chart"
                text="Not enough history yet. Deposit, withdraw, or open a trade to add a snapshot."
              />
            )}
          </div>
        </Card>

        <Card className="flex flex-col gap-5">
          <CardHeader
            icon="account_balance_wallet"
            title="Add or withdraw"
            subtitle="Simulated USD only. No bank connection."
            badge={<ProvenanceBadge provenance="input" label="User Input" />}
          />
          <div
            role="tablist"
            aria-label="Wallet action"
            className="inline-flex rounded-full bg-surface-container-low p-1"
          >
            {(["deposit", "withdraw"] as const).map((option) => (
              <button
                key={option}
                type="button"
                role="tab"
                aria-selected={mode === option}
                onClick={() => {
                  setMode(option);
                  setError("");
                }}
                className={`flex-1 rounded-full px-4 py-2 font-body-sm text-body-sm font-medium capitalize transition-colors ${
                  mode === option
                    ? "bg-white text-on-surface shadow-sm"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
              >
                {option}
              </button>
            ))}
          </div>
          <form onSubmit={submitFunds} className="flex flex-col gap-4">
            <Field label="Amount (USD)" htmlFor="wallet-amount" required>
              <TextInput
                id="wallet-amount"
                type="number"
                inputMode="decimal"
                min="0.01"
                step="0.01"
                placeholder="100.00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
            </Field>
            <Field label="Note (optional)" htmlFor="wallet-note">
              <TextInput
                id="wallet-note"
                maxLength={200}
                placeholder="Example: monthly savings"
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </Field>
            <Button type="submit" disabled={disabled} className="w-full">
              {busy ? "Updating…" : mode === "deposit" ? "Deposit" : "Withdraw"}
            </Button>
          </form>
          <p className="font-body-sm text-body-sm text-on-surface-variant">
            Available cash:{" "}
            <span className="tabular-nums text-on-surface">
              {wallet ? money(wallet.balance) : "—"}
            </span>
          </p>
        </Card>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[0.8fr_1.2fr]">
        <Card className="flex flex-col gap-5">
          <CardHeader
            icon="add_chart"
            title="Open a position"
            subtitle="Uses the latest daily close in the database."
            badge={<ProvenanceBadge provenance="input" label="User Input" />}
          />
          <form onSubmit={openPosition} className="flex flex-col gap-4">
            <Field label="Ticker" htmlFor="position-ticker" required>
              <TextInput
                id="position-ticker"
                placeholder="AAPL"
                autoComplete="off"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
              />
            </Field>
            <div className="flex flex-col gap-2">
              <span className="font-body-sm text-body-sm font-medium text-on-surface-variant">
                Side
              </span>
              <div className="flex gap-2">
                {(["long", "short"] as const).map((option) => (
                  <button
                    key={option}
                    type="button"
                    aria-pressed={side === option}
                    onClick={() => setSide(option)}
                    className={`flex-1 rounded-xl border px-4 py-3 font-body-sm text-body-sm font-medium capitalize transition-colors ${
                      side === option
                        ? "border-tertiary-accent bg-primary-fixed text-on-primary-fixed"
                        : "border-surface-container-high text-on-surface hover:bg-surface-container-low"
                    }`}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Margin (USD)" htmlFor="position-amount" required>
                <TextInput
                  id="position-amount"
                  type="number"
                  inputMode="decimal"
                  min="0.01"
                  step="0.01"
                  placeholder="100.00"
                  value={tradeAmount}
                  onChange={(e) => setTradeAmount(e.target.value)}
                />
              </Field>
              <Field label="Leverage" htmlFor="position-leverage" required>
                <TextInput
                  id="position-leverage"
                  type="number"
                  inputMode="decimal"
                  min="1"
                  max="10"
                  step="0.5"
                  value={leverage}
                  onChange={(e) => setLeverage(e.target.value)}
                />
              </Field>
            </div>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Notional = margin × leverage. A large leveraged loss can make the
              balance negative.
            </p>
            <Button type="submit" disabled={disabled} className="w-full">
              {busy ? "Opening…" : "Open position"}
            </Button>
          </form>
        </Card>

        <Card className="flex flex-col gap-5">
          <CardHeader
            icon="swap_vert"
            title="Open positions"
            subtitle={`${positions.length} ${positions.length === 1 ? "position" : "positions"}`}
            badge={<ProvenanceBadge provenance="example" label="Simulated" />}
          />
          {positions.length === 0 ? (
            <EmptyState
              icon="inbox"
              text="No open positions. Open a simulated trade to see it here."
            />
          ) : (
            <ul className="flex flex-col gap-3">
              {positions.map((position) => (
                <PositionRow
                  key={position.id}
                  position={position}
                  closing={closingId === position.id}
                  onClose={() => closePosition(position)}
                />
              ))}
            </ul>
          )}
        </Card>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-2">
        <Card className="flex flex-col gap-5">
          <CardHeader
            icon="receipt_long"
            title="Closed trades"
            subtitle={`${trades.length} ${trades.length === 1 ? "trade" : "trades"}`}
            badge={<ProvenanceBadge provenance="example" label="Simulated" />}
          />
          {trades.length === 0 ? (
            <EmptyState
              icon="history"
              text="No closed trades yet. Close an open position to record P/L."
            />
          ) : (
            <ul className="flex flex-col divide-y divide-surface-container-high">
              {trades.map((trade) => (
                <TradeRow key={trade.id} trade={trade} />
              ))}
            </ul>
          )}
        </Card>

        <Card className="flex flex-col gap-5">
          <CardHeader
            icon="list_alt"
            title="Transaction log"
            subtitle={`${initial.transactions.length} ${initial.transactions.length === 1 ? "entry" : "entries"}`}
            badge={<ProvenanceBadge provenance="input" label="User Input" />}
          />
          {initial.transactions.length === 0 ? (
            <EmptyState
              icon="receipt"
              text="No deposits or withdrawals yet."
            />
          ) : (
            <ul className="flex flex-col divide-y divide-surface-container-high">
              {initial.transactions.map((tx) => (
                <TransactionRow key={tx.id} tx={tx} />
              ))}
            </ul>
          )}
        </Card>
      </div>

      <p className="max-w-3xl font-body-sm text-body-sm text-on-surface-variant">
        Simulated trading only. This is not investment advice, not a real
        brokerage account, and no orders or money are moved.
      </p>
    </div>
  );
}
