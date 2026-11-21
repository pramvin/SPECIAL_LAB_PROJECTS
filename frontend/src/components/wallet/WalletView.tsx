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
  HistoryPage,
  Position,
  Trade,
  TradingSummary,
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
  const [confirming, setConfirming] = useState(false);
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
        {!confirming && (
          <Button
            variant="secondary"
            size="sm"
            icon="close"
            disabled={closing}
            onClick={() => setConfirming(true)}
          >
            Close
          </Button>
        )}
      </div>

      {confirming && (
        <div
          role="group"
          aria-label={`Confirm closing ${position.ticker}`}
          className="flex flex-col gap-3 rounded-xl border border-surface-container-high bg-white p-4"
        >
          <div className="flex flex-col gap-1">
            <span className="font-title-md text-title-md text-on-surface">
              Close {position.ticker} {position.side} position?
            </span>
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              The close uses the latest Yahoo Finance daily bar fetched when
              confirmed; it is not a real-time quote.
            </span>
            {pnl !== null && (
              <span className={`font-body-sm text-body-sm ${toneFor(pnl)}`}>
                Estimated P/L from the currently saved daily close:{" "}
                {money(pnl, true)}
              </span>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={closing}
              onClick={() => setConfirming(false)}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={closing}
              onClick={() => {
                setConfirming(false);
                onClose();
              }}
            >
              {closing ? "Closing…" : "Confirm close"}
            </Button>
          </div>
        </div>
      )}

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
  const [notice, setNotice] = useState<{
    title: string;
    message: string;
  } | null>(null);
  const [mode, setMode] = useState<"deposit" | "withdraw">("deposit");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [ticker, setTicker] = useState("");
  const [side, setSide] = useState<"long" | "short">("long");
  const [tradeAmount, setTradeAmount] = useState("");
  const [leverage, setLeverage] = useState("1");
  const [closingId, setClosingId] = useState<number | null>(null);
  const [positionSort, setPositionSort] = useState<
    "newest" | "ticker" | "profit"
  >("newest");
  const [transactionRows, setTransactionRows] = useState(initial.transactions);
  const [transactionTotal, setTransactionTotal] = useState(
    initial.transactionTotal,
  );
  const [transactionsHaveMore, setTransactionsHaveMore] = useState(
    initial.transactionsHasMore,
  );
  const [tradeRows, setTradeRows] = useState(initial.trades);
  const [tradeTotal, setTradeTotal] = useState(initial.tradeTotal);
  const [tradesHaveMore, setTradesHaveMore] = useState(initial.tradesHasMore);
  const [transactionSearch, setTransactionSearch] = useState("");
  const [transactionKind, setTransactionKind] = useState<
    "all" | "deposit" | "withdraw"
  >("all");
  const [tradeSearch, setTradeSearch] = useState("");
  const [tradeSide, setTradeSide] = useState<"all" | "long" | "short">("all");
  const [tradeOutcome, setTradeOutcome] = useState<
    "all" | "win" | "loss" | "breakeven"
  >("all");
  const [activeTransactionFilters, setActiveTransactionFilters] = useState({
    search: "",
    kind: "all" as "all" | "deposit" | "withdraw",
  });
  const [activeTradeFilters, setActiveTradeFilters] = useState({
    search: "",
    side: "all" as "all" | "long" | "short",
    outcome: "all" as "all" | "win" | "loss" | "breakeven",
  });
  const [transactionsLoading, setTransactionsLoading] = useState(false);
  const [tradesLoading, setTradesLoading] = useState(false);
  const [transactionError, setTransactionError] = useState("");
  const [tradeError, setTradeError] = useState("");

  const wallet = initial.wallet;
  const positions = initial.positions;
  const summary: TradingSummary | null = initial.tradingSummary;
  const history = initial.history;
  const startingBalance = initial.startingBalance;
  const disabled = busy || pending;

  const realizedPnl = summary?.realized_pnl ?? null;
  const unrealizedPnl = summary?.unrealized_pnl ?? null;
  const openMargin = summary?.open_margin ?? 0;
  const percentageChanges = history.map((point) => point.change_pct);
  const currentChangePct =
    wallet?.change_pct ?? percentageChanges[percentageChanges.length - 1] ?? 0;
  const sortedPositions = [...positions].sort((left, right) => {
    if (positionSort === "ticker") {
      return (
        left.ticker.localeCompare(right.ticker) ||
        right.opened_at - left.opened_at
      );
    }
    if (positionSort === "profit") {
      const leftPnl = left.unrealized_pnl ?? Number.NEGATIVE_INFINITY;
      const rightPnl = right.unrealized_pnl ?? Number.NEGATIVE_INFINITY;
      if (leftPnl !== rightPnl) return rightPnl > leftPnl ? 1 : -1;
      return right.opened_at - left.opened_at;
    }
    return right.opened_at - left.opened_at || right.id - left.id;
  });

  function refresh() {
    startTransition(() => router.refresh());
  }

  async function postJson<T = unknown>(path: string, body: unknown): Promise<T> {
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
      | (T & { detail?: unknown })
      | null;
    if (!res.ok) {
      throw new Error(
        typeof data?.detail === "string"
          ? data.detail
          : `Request failed (${res.status})`,
      );
    }
    if (data === null) {
      throw new Error("The server returned an empty response.");
    }
    return data;
  }

  async function getHistoryPage<T>(path: string): Promise<HistoryPage<T>> {
    const res = await fetch(path, { cache: "no-store" });
    if (res.status === 401) {
      router.replace("/login");
      throw new Error("Session expired. Sign in again.");
    }
    const data = (await res.json().catch(() => null)) as
      | (HistoryPage<T> & { detail?: unknown })
      | null;
    if (!res.ok) {
      throw new Error(
        typeof data?.detail === "string"
          ? data.detail
          : `Request failed (${res.status})`,
      );
    }
    if (
      data === null ||
      !Array.isArray(data.items) ||
      typeof data.total !== "number" ||
      typeof data.has_more !== "boolean"
    ) {
      throw new Error("The server returned an invalid history page.");
    }
    return data;
  }

  async function loadTransactions(
    filters: typeof activeTransactionFilters,
    append = false,
  ) {
    setTransactionsLoading(true);
    setTransactionError("");
    const params = new URLSearchParams({
      limit: "50",
      offset: String(append ? transactionRows.length : 0),
    });
    if (filters.search) params.set("search", filters.search);
    if (filters.kind !== "all") params.set("kind", filters.kind);
    try {
      const page = await getHistoryPage<WalletTransaction>(
        `/api/wallet/transactions?${params.toString()}`,
      );
      setTransactionRows((current) =>
        append ? [...current, ...page.items] : page.items,
      );
      setTransactionTotal(page.total);
      setTransactionsHaveMore(page.has_more);
    } catch (err) {
      setTransactionError(
        err instanceof Error
          ? err.message
          : "Could not load transaction history.",
      );
    } finally {
      setTransactionsLoading(false);
    }
  }

  async function loadTrades(
    filters: typeof activeTradeFilters,
    append = false,
  ) {
    setTradesLoading(true);
    setTradeError("");
    const params = new URLSearchParams({
      limit: "50",
      offset: String(append ? tradeRows.length : 0),
    });
    if (filters.search) params.set("search", filters.search);
    if (filters.side !== "all") params.set("side", filters.side);
    if (filters.outcome !== "all") params.set("outcome", filters.outcome);
    try {
      const page = await getHistoryPage<Trade>(
        `/api/trades?${params.toString()}`,
      );
      setTradeRows((current) =>
        append ? [...current, ...page.items] : page.items,
      );
      setTradeTotal(page.total);
      setTradesHaveMore(page.has_more);
    } catch (err) {
      setTradeError(
        err instanceof Error ? err.message : "Could not load trade history.",
      );
    } finally {
      setTradesLoading(false);
    }
  }

  function applyTransactionFilters(event: React.FormEvent) {
    event.preventDefault();
    const filters = {
      search: transactionSearch.trim(),
      kind: transactionKind,
    };
    setActiveTransactionFilters(filters);
    void loadTransactions(filters);
  }

  function applyTradeFilters(event: React.FormEvent) {
    event.preventDefault();
    const filters = {
      search: tradeSearch.trim().toUpperCase(),
      side: tradeSide,
      outcome: tradeOutcome,
    };
    setActiveTradeFilters(filters);
    void loadTrades(filters);
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
    setNotice(null);
    try {
      const result = await postJson<{
        transaction: WalletTransaction;
      }>(`/api/wallet/${mode}`, {
        amount: value,
        note: note.trim(),
      });
      setAmount("");
      setNote("");
      setNotice({
        title: mode === "deposit" ? "Deposit confirmed" : "Withdrawal confirmed",
        message: `${money(result.transaction.amount)} ${
          mode === "deposit" ? "added to" : "withdrawn from"
        } your simulated wallet. New balance: ${money(result.transaction.balance_after)}.`,
      });
      refresh();
      void loadTransactions(activeTransactionFilters);
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
    setNotice(null);
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
      setNotice({
        title: "Position opened",
        message: `Opened a ${side} position in ${cleanTicker}.`,
      });
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
    setNotice(null);
    try {
      await postJson(`/api/positions/${position.id}/close`, {});
      setNotice({
        title: "Position closed",
        message: `Closed ${position.ticker}.`,
      });
      refresh();
      void loadTrades(activeTradeFilters);
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
          Paper Trading
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
        <div role="status" aria-live="polite">
          <NoticeBanner
            icon="check_circle"
            tone="neutral"
            title={notice.title}
          >
            {notice.message}
          </NoticeBanner>
        </div>
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
            <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-right sm:grid-cols-4">
              <div className="flex flex-col gap-1">
                <span className="font-body-sm text-body-sm text-on-surface-variant">
                  Open
                </span>
                <span className="font-title-md text-title-md tabular-nums text-on-surface">
                  {summary?.open_position_count ?? "—"}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="font-body-sm text-body-sm text-on-surface-variant">
                  Invested margin
                </span>
                <span className="font-title-md text-title-md tabular-nums text-on-surface">
                  {summary ? money(openMargin) : "—"}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="font-body-sm text-body-sm text-on-surface-variant">
                  Realized P/L
                </span>
                <span
                  className={`font-title-md text-title-md tabular-nums ${realizedPnl === null ? "text-on-surface-variant" : toneFor(realizedPnl)}`}
                >
                  {realizedPnl === null ? "—" : money(realizedPnl, true)}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="font-body-sm text-body-sm text-on-surface-variant">
                  Unrealized P/L
                </span>
                <span
                  className={`font-title-md text-title-md tabular-nums ${unrealizedPnl === null ? "text-on-surface-variant" : toneFor(unrealizedPnl)}`}
                >
                  {unrealizedPnl === null ? "—" : money(unrealizedPnl, true)}
                </span>
              </div>
            </div>
          </div>

          <div
            role="group"
            aria-label="Closed-trade performance"
            className="grid grid-cols-2 gap-4 border-t border-surface-container-high pt-5 sm:grid-cols-4"
          >
            <div className="flex flex-col gap-1">
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                Closed trades
              </span>
              <span className="font-title-md text-title-md tabular-nums text-on-surface">
                {summary?.closed_trade_count ?? "—"}
              </span>
              {summary && (
                <span className="font-body-sm text-body-sm text-on-surface-variant">
                  {summary.win_count} wins · {summary.loss_count} losses ·{" "}
                  {summary.breakeven_count} even
                </span>
              )}
            </div>
            <div className="flex flex-col gap-1">
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                Win rate
              </span>
              <span className="font-title-md text-title-md tabular-nums text-on-surface">
                {summary?.win_rate_pct === null || !summary
                  ? "—"
                  : `${summary.win_rate_pct.toFixed(2)}%`}
              </span>
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                Wins ÷ all closed trades
              </span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                Average closed P/L
              </span>
              <span
                className={`font-title-md text-title-md tabular-nums ${summary?.average_pnl === null || !summary ? "text-on-surface-variant" : toneFor(summary.average_pnl)}`}
              >
                {summary?.average_pnl === null || !summary
                  ? "—"
                  : money(summary.average_pnl, true)}
              </span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                Best / worst
              </span>
              <span className="font-title-md text-title-md tabular-nums text-on-surface">
                {summary?.best_trade_pnl === null ||
                summary?.worst_trade_pnl === null ||
                !summary
                  ? "—"
                  : `${money(summary.best_trade_pnl, true)} / ${money(summary.worst_trade_pnl, true)}`}
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-3 border-t border-surface-container-high pt-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <SectionLabel>Balance change over time</SectionLabel>
              {summary && summary.unpriced_position_count > 0 ? (
                <span className="font-body-sm text-body-sm text-on-surface-variant">
                  Unrealized P/L unavailable for{" "}
                  {summary.unpriced_position_count} unpriced{" "}
                  {summary.unpriced_position_count === 1 ? "position" : "positions"}
                </span>
              ) : (
                <span className="font-body-sm text-body-sm text-on-surface-variant">
                  Unrealized P/L{" "}
                  {unrealizedPnl === null ? "—" : money(unrealizedPnl, true)}
                </span>
              )}
            </div>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Percentage change from your initial {money(startingBalance)}.
              Open-position P/L uses the latest saved Yahoo Finance daily bar,
              not a live quote.
            </p>
            {percentageChanges.length >= 2 ? (
              <>
                <LineChart
                  series={[
                    {
                      points: percentageChanges,
                      color: "#0071e3",
                      area: true,
                    },
                  ]}
                  target={0}
                  height={180}
                  ariaLabel="Percentage change in simulated wallet balance over time"
                />
                <div className="flex flex-wrap items-center justify-between gap-2 font-body-sm text-body-sm text-on-surface-variant">
                  <span>
                    Earliest {percent(percentageChanges[0])}
                  </span>
                  <span className={toneFor(currentChangePct)}>
                    Now {percent(currentChangePct)}
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
            subtitle="Uses Yahoo Finance's latest daily bar; prices are not real-time."
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
          {positions.length > 1 && (
            <Field label="Sort positions" htmlFor="position-sort">
              <select
                id="position-sort"
                value={positionSort}
                onChange={(event) =>
                  setPositionSort(
                    event.target.value as "newest" | "ticker" | "profit",
                  )
                }
                className="w-full rounded-lg border border-surface-container-high bg-white px-3 py-2 font-body-sm text-body-sm text-on-surface focus-visible:outline-2 focus-visible:outline-primary"
              >
                <option value="newest">Newest first</option>
                <option value="ticker">Ticker A–Z</option>
                <option value="profit">Best unrealized P/L</option>
              </select>
            </Field>
          )}
          {positions.length === 0 ? (
            <EmptyState
              icon="inbox"
              text="No open positions. Open a simulated trade to see it here."
            />
          ) : (
            <ul className="flex flex-col gap-3">
              {sortedPositions.map((position) => (
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
            subtitle={`${tradeTotal} ${tradeTotal === 1 ? "trade" : "trades"}`}
            badge={<ProvenanceBadge provenance="example" label="Simulated" />}
          />
          <form
            onSubmit={applyTradeFilters}
            className="flex flex-col gap-3 rounded-xl bg-surface-container-low p-4"
          >
            <Field label="Search ticker" htmlFor="trade-search">
              <TextInput
                id="trade-search"
                type="search"
                maxLength={12}
                placeholder="AAPL"
                value={tradeSearch}
                onChange={(event) => setTradeSearch(event.target.value)}
              />
            </Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Side" htmlFor="trade-side">
                <select
                  id="trade-side"
                  value={tradeSide}
                  onChange={(event) =>
                    setTradeSide(event.target.value as typeof tradeSide)
                  }
                  className="w-full rounded-lg border border-surface-container-high bg-white px-3 py-2 font-body-sm text-body-sm text-on-surface focus-visible:outline-2 focus-visible:outline-primary"
                >
                  <option value="all">All sides</option>
                  <option value="long">Long</option>
                  <option value="short">Short</option>
                </select>
              </Field>
              <Field label="Result" htmlFor="trade-outcome">
                <select
                  id="trade-outcome"
                  value={tradeOutcome}
                  onChange={(event) =>
                    setTradeOutcome(event.target.value as typeof tradeOutcome)
                  }
                  className="w-full rounded-lg border border-surface-container-high bg-white px-3 py-2 font-body-sm text-body-sm text-on-surface focus-visible:outline-2 focus-visible:outline-primary"
                >
                  <option value="all">All results</option>
                  <option value="win">Wins</option>
                  <option value="loss">Losses</option>
                  <option value="breakeven">Break-even</option>
                </select>
              </Field>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button type="submit" variant="secondary" disabled={tradesLoading}>
                {tradesLoading ? "Searching…" : "Apply filters"}
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={tradesLoading}
                onClick={() => {
                  const filters = {
                    search: "",
                    side: "all" as const,
                    outcome: "all" as const,
                  };
                  setTradeSearch("");
                  setTradeSide("all");
                  setTradeOutcome("all");
                  setActiveTradeFilters(filters);
                  void loadTrades(filters);
                }}
              >
                Clear
              </Button>
            </div>
          </form>
          <p
            aria-live="polite"
            className="font-body-sm text-body-sm text-on-surface-variant"
          >
            Showing {tradeRows.length} of {tradeTotal} matching{" "}
            {tradeTotal === 1 ? "trade" : "trades"}.
          </p>
          {tradeError && (
            <p role="alert" className="font-body-sm text-body-sm text-error">
              {tradeError}
            </p>
          )}
          {tradeRows.length === 0 ? (
            <EmptyState
              icon="history"
              text={
                tradeTotal === 0 &&
                (activeTradeFilters.search ||
                  activeTradeFilters.side !== "all" ||
                  activeTradeFilters.outcome !== "all")
                  ? "No closed trades match these filters."
                  : "No closed trades yet. Close an open position to record P/L."
              }
            />
          ) : (
            <ul className="flex flex-col divide-y divide-surface-container-high">
              {tradeRows.map((trade) => (
                <TradeRow key={trade.id} trade={trade} />
              ))}
            </ul>
          )}
          {tradesHaveMore && (
            <Button
              type="button"
              variant="secondary"
              disabled={tradesLoading}
              onClick={() => void loadTrades(activeTradeFilters, true)}
            >
              {tradesLoading ? "Loading…" : "Load more trades"}
            </Button>
          )}
        </Card>

        <Card className="flex flex-col gap-5">
          <CardHeader
            icon="list_alt"
            title="Transaction log"
            subtitle={`${transactionTotal} ${transactionTotal === 1 ? "entry" : "entries"}`}
            badge={<ProvenanceBadge provenance="input" label="User Input" />}
          />
          <form
            onSubmit={applyTransactionFilters}
            className="flex flex-col gap-3 rounded-xl bg-surface-container-low p-4"
          >
            <Field label="Search note or type" htmlFor="transaction-search">
              <TextInput
                id="transaction-search"
                type="search"
                maxLength={80}
                placeholder="Deposit or note text"
                value={transactionSearch}
                onChange={(event) => setTransactionSearch(event.target.value)}
              />
            </Field>
            <Field label="Transaction type" htmlFor="transaction-kind">
              <select
                id="transaction-kind"
                value={transactionKind}
                onChange={(event) =>
                  setTransactionKind(
                    event.target.value as typeof transactionKind,
                  )
                }
                className="w-full rounded-lg border border-surface-container-high bg-white px-3 py-2 font-body-sm text-body-sm text-on-surface focus-visible:outline-2 focus-visible:outline-primary"
              >
                <option value="all">Deposits and withdrawals</option>
                <option value="deposit">Deposits only</option>
                <option value="withdraw">Withdrawals only</option>
              </select>
            </Field>
            <div className="flex flex-wrap gap-2">
              <Button
                type="submit"
                variant="secondary"
                disabled={transactionsLoading}
              >
                {transactionsLoading ? "Searching…" : "Apply filters"}
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={transactionsLoading}
                onClick={() => {
                  const filters = { search: "", kind: "all" as const };
                  setTransactionSearch("");
                  setTransactionKind("all");
                  setActiveTransactionFilters(filters);
                  void loadTransactions(filters);
                }}
              >
                Clear
              </Button>
            </div>
          </form>
          <p
            aria-live="polite"
            className="font-body-sm text-body-sm text-on-surface-variant"
          >
            Showing {transactionRows.length} of {transactionTotal} matching{" "}
            {transactionTotal === 1 ? "entry" : "entries"}.
          </p>
          {transactionError && (
            <p role="alert" className="font-body-sm text-body-sm text-error">
              {transactionError}
            </p>
          )}
          {transactionRows.length === 0 ? (
            <EmptyState
              icon="receipt"
              text={
                transactionTotal === 0 &&
                (activeTransactionFilters.search !== "" ||
                  activeTransactionFilters.kind !== "all")
                  ? "No transactions match these filters."
                  : "No deposits or withdrawals yet."
              }
            />
          ) : (
            <ul className="flex flex-col divide-y divide-surface-container-high">
              {transactionRows.map((tx) => (
                <TransactionRow key={tx.id} tx={tx} />
              ))}
            </ul>
          )}
          {transactionsHaveMore && (
            <Button
              type="button"
              variant="secondary"
              disabled={transactionsLoading}
              onClick={() =>
                void loadTransactions(activeTransactionFilters, true)
              }
            >
              {transactionsLoading ? "Loading…" : "Load more transactions"}
            </Button>
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