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
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
  opened_at: number;
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

export interface WalletData {
  wallet: WalletSummary | null;
  transactions: WalletTransaction[];
  history: BalancePoint[];
  startingBalance: number;
  positions: Position[];
  trades: Trade[];
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
      history: [],
      startingBalance: 1000,
      positions: [],
      trades: [],
      error: "Not signed in.",
    };
  }

  const [wallet, transactions, history, positions, trades] = await Promise.all([
    getJson<WalletSummary>("/api/wallet", session),
    getJson<{ items: WalletTransaction[] }>("/api/wallet/transactions", session),
    getJson<WalletHistory>("/api/wallet/history", session),
    getJson<{ items: Position[] }>("/api/positions", session),
    getJson<{ items: Trade[] }>("/api/trades", session),
  ]);

  return {
    wallet,
    transactions: transactions?.items ?? [],
    history: history?.items ?? [],
    startingBalance: history?.starting_balance ?? 1000,
    positions: positions?.items ?? [],
    trades: trades?.items ?? [],
    error: wallet ? null : "Could not load your wallet. Is the backend running?",
  };
}
