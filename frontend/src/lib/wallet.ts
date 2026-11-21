import { cookies } from "next/headers";

export interface WalletSummary {
  balance: number;
  starting_balance: number;
  change: number;
  change_pct: number;
  currency: string;
  updated_at: number;
}

export interface WalletTransaction {
  id: number;
  kind: "deposit" | "withdraw";
  amount: number;
  balance_after: number;
  note: string;
  created_at: number;
}

export interface BalancePoint {
  balance: number;
  change_pct: number;
  created_at: number;
}

export interface WalletHistory {
  starting_balance: number;
  items: BalancePoint[];
}

export interface Position {
  id: number;
  ticker: string;
  side: "long" | "short";
  entry_price: number;
  current_price: number | null;
  quantity: number;
  leverage: number;
  amount_deducted: number;
  notional: number;
  liquidation_price: number;
  liquidated: boolean;
  equity: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
  price_is_stale: boolean;
  opened_at: number;
}

export interface LivePositions {
  items: Position[];
  totals: {
    open_margin: number;
    unrealized_pnl: number | null;
    unrealized_pnl_pct: number | null;
    unpriced_position_count: number;
  };
  as_of: number;
}

export interface PreviewScenario {
  price_move_pct: number;
  pnl: number;
  pnl_pct: number;
}

export interface LeveragePreviewRow {
  leverage: number;
  margin: number;
  notional: number;
  quantity: number;
  liquidation_price: number;
  liquidation_move_pct: number;
  scenarios: PreviewScenario[];
}

export interface PositionPreview {
  ticker: string;
  side: "long" | "short";
  amount: number;
  entry_price: number;
  price_is_stale: boolean;
  wallet_balance: number;
  balance_after_open: number;
  affordable: boolean;
  liquidate_at_margin: boolean;
  options: LeveragePreviewRow[];
}

export interface Trade {
  id: number;
  position_id: number;
  ticker: string;
  side: "long" | "short";
  entry_price: number;
  exit_price: number;
  quantity: number;
  leverage: number;
  amount_deducted: number;
  pnl: number;
  pnl_pct: number;
  opened_at: number;
  closed_at: number;
}

export interface TradingSummary {
  closed_trade_count: number;
  win_count: number;
  loss_count: number;
  breakeven_count: number;
  win_rate_pct: number | null;
  realized_pnl: number;
  average_pnl: number | null;
  best_trade_pnl: number | null;
  worst_trade_pnl: number | null;
  open_position_count: number;
  open_margin: number;
  unrealized_pnl: number | null;
  unpriced_position_count: number;
}

export interface HistoryPage<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
}

export interface WalletData {
  wallet: WalletSummary | null;
  transactions: WalletTransaction[];
  transactionTotal: number;
  transactionsHasMore: boolean;
  history: BalancePoint[];
  startingBalance: number;
  positions: Position[];
  trades: Trade[];
  tradeTotal: number;
  tradesHasMore: boolean;
  tradingSummary: TradingSummary | null;
  error: string | null;
}

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

async function getJson<T>(
  path: string,
  session: string | undefined,
): Promise<T | null> {
  if (!session) return null;
  try {
    const res = await fetch(`${BACKEND_URL}${path}`, {
      headers: { cookie: `session=${session}` },
      cache: "no-store",
    });
    return res.ok ? ((await res.json()) as T) : null;
  } catch {
    return null;
  }
}

/** Everything the Wallet page needs, fetched server-side with the session cookie. */
export async function getWalletData(): Promise<WalletData> {
  const session = (await cookies()).get("session")?.value;
  if (!session) {
    return {
      wallet: null,
      transactions: [],
      transactionTotal: 0,
      transactionsHasMore: false,
      history: [],
      startingBalance: 1000,
      positions: [],
      trades: [],
      tradeTotal: 0,
      tradesHasMore: false,
      tradingSummary: null,
      error: "Not signed in.",
    };
  }

  const [
    wallet,
    transactions,
    history,
    positions,
    trades,
    tradingSummary,
  ] = await Promise.all([
    getJson<WalletSummary>("/api/wallet", session),
    getJson<HistoryPage<WalletTransaction>>(
      "/api/wallet/transactions",
      session,
    ),
    getJson<WalletHistory>("/api/wallet/history", session),
    getJson<{ items: Position[] }>("/api/positions", session),
    getJson<HistoryPage<Trade>>("/api/trades", session),
    getJson<TradingSummary>("/api/trading/summary", session),
  ]);

  return {
    wallet,
    transactions: transactions?.items ?? [],
    transactionTotal: transactions?.total ?? 0,
    transactionsHasMore: transactions?.has_more ?? false,
    history: history?.items ?? [],
    startingBalance: history?.starting_balance ?? 1000,
    positions: positions?.items ?? [],
    trades: trades?.items ?? [],
    tradeTotal: trades?.total ?? 0,
    tradesHasMore: trades?.has_more ?? false,
    tradingSummary,
    error: wallet ? null : "Could not load your wallet. Is the backend running?",
  };
}