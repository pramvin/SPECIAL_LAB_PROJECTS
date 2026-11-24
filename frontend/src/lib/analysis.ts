import type { Horizon, Sentiment } from "./recommendations";

/** One click-analysis run for a ticker + horizon (see specs/click-analysis/SPEC.md). */
export type AnalysisStatus = "running" | "ok" | "partial" | "error";

export type NewsDirection = Sentiment | "mixed";
export type SocialDirection = NewsDirection | "no_data";
export type MomentumLabel = "improving" | "flat" | "weakening";
export type VolumeLabel = "above_average" | "normal" | "below_average";

export interface ChartLevel {
  price: number;
  why: string;
}

export interface ChartRead {
  summary: string;
  support: ChartLevel[];
  resistance: ChartLevel[];
  momentum: { label: MomentumLabel; why: string };
  volume: { label: VolumeLabel; why: string };
  status: "ok" | "unavailable";
  reason: string | null;
}

export interface NewsItem {
  title: string;
  source: string;
  url: string | null;
  published_at: string;
  sentiment: Sentiment | null;
}

export interface NewsRead {
  direction: NewsDirection;
  /** positive / all scored headlines, 0..1. Null when there are no headlines. */
  positive_share: number | null;
  counts: { positive: number; neutral: number; negative: number };
  summary: string;
  items: NewsItem[];
  status: "ok" | "unavailable";
  reason: string | null;
}

export interface SocialItem {
  text: string;
  source: string;
  sentiment: Sentiment | null;
  url: string | null;
}

export interface SocialRead {
  direction: SocialDirection;
  summary: string;
  sources: Record<string, { status: "ok" | "unavailable" | "skipped"; count: number }>;
  items: SocialItem[];
  status: "ok" | "unavailable" | "skipped";
  reason: string | null;
}

export interface AnalysisResult {
  chart: ChartRead;
  news: NewsRead;
  social: SocialRead;
}

export interface Analysis {
  ticker: string;
  horizon: Horizon;
  status: AnalysisStatus;
  cached: boolean;
  started_at: string;
  finished_at: string | null;
  error: string | null;
  result: AnalysisResult | null;
}

async function request(path: string, method: "GET" | "POST"): Promise<Analysis> {
  const res = await fetch(path, { method, cache: "no-store" });
  const body = (await res.json().catch(() => null)) as
    | { detail?: unknown }
    | null;
  if (!res.ok) {
    throw new Error(
      typeof body?.detail === "string"
        ? body.detail
        : `Request failed (${res.status})`,
    );
  }
  return body as unknown as Analysis;
}

const url = (ticker: string, horizon: Horizon) =>
  `/api/analysis/${encodeURIComponent(ticker)}?horizon=${horizon}`;

/** Starts a run (or reuses a fresh one) and returns it immediately; the LLM work is in the background. */
export function startAnalysis(ticker: string, horizon: Horizon) {
  return request(url(ticker, horizon), "POST");
}

export function getAnalysis(ticker: string, horizon: Horizon) {
  return request(url(ticker, horizon), "GET");
}
