"use client";

import { useEffect, useState } from "react";
import { Card, CardHeader } from "@/components/ui/Card";
import { getAnalysis, startAnalysis, type Analysis } from "@/lib/analysis";
import type { Horizon } from "@/lib/recommendations";
import { ChartRead } from "./ChartRead";
import { NewsGauge } from "./NewsGauge";
import { NewsList } from "./NewsList";
import { SocialBox } from "./SocialBox";

const POLL_MS = 3_000;
const TIMEOUT_MS = 5 * 60_000;

const HORIZON_NAME: Record<Exclude<Horizon, "1w">, string> = {
  "1m": "1-month",
  "3m": "3-month",
};

function RetryButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mt-4 w-fit rounded-xl bg-on-surface px-5 py-2.5 font-body-sm text-body-sm font-semibold text-white"
    >
      Try again
    </button>
  );
}

function Failure({
  title,
  message,
  onRetry,
}: {
  title: string;
  message: string;
  onRetry: () => void;
}) {
  return (
    <Card as="section">
      <CardHeader title={title} icon="error" />
      <p className="mt-4 font-body-md text-body-md text-on-surface">{message}</p>
      <RetryButton onClick={onRetry} />
    </Card>
  );
}

function Skeleton() {
  return (
    <Card as="section">
      <div aria-busy="true" className="flex flex-col gap-3">
        <div className="h-5 w-1/3 animate-pulse rounded-full bg-surface-container-high" />
        <div className="h-3.5 w-full animate-pulse rounded-full bg-surface-container-low" />
        <div className="h-3.5 w-5/6 animate-pulse rounded-full bg-surface-container-low" />
        <div className="h-3.5 w-2/3 animate-pulse rounded-full bg-surface-container-low" />
      </div>
      <p
        aria-live="polite"
        className="mt-5 font-body-md text-body-md text-on-surface-variant"
      >
        Analyzing this week&rsquo;s news, chart and social posts. This takes a
        minute or two.
      </p>
    </Card>
  );
}

function ComingSoon({ horizon }: { horizon: Exclude<Horizon, "1w"> }) {
  return (
    <Card as="section">
      <CardHeader
        title="Coming soon"
        icon="schedule"
        subtitle={`The ${HORIZON_NAME[horizon]} analysis is not available yet.`}
      />
      <p className="mt-4 font-body-md text-body-md text-on-surface-variant">
        Only the 1-week analysis works for now. Open the 1 week tab to analyze
        this stock.
      </p>
    </Card>
  );
}

/**
 * Runs one click-analysis for the stock and renders its four blocks.
 * Starts a run on mount, then polls every 3 s for up to 5 minutes. The page
 * mounts it with a key per ticker and horizon, so state never leaks between stocks.
 */
export function StockDetail({
  ticker,
  horizon,
}: {
  ticker: string;
  horizon: Horizon;
}) {
  const active = horizon === "1w";
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [timedOut, setTimedOut] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!active) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const startedAt = Date.now();

    const fail = (e: unknown) =>
      setRequestError(
        e instanceof Error ? e.message : "Could not reach the backend.",
      );

    async function poll() {
      try {
        const data = await getAnalysis(ticker, horizon);
        if (stopped) return;
        setAnalysis(data);
        if (data.status !== "running") return;
      } catch (e) {
        if (!stopped) fail(e);
        return;
      }
      if (Date.now() - startedAt > TIMEOUT_MS) {
        if (!stopped) setTimedOut(true);
        return;
      }
      timer = setTimeout(poll, POLL_MS);
    }

    async function start() {
      try {
        const data = await startAnalysis(ticker, horizon);
        if (stopped) return;
        setAnalysis(data);
        if (data.status === "running") timer = setTimeout(poll, POLL_MS);
      } catch (e) {
        if (!stopped) fail(e);
      }
    }

    void start();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
    };
  }, [ticker, horizon, active, attempt]);

  const retry = () => {
    setAnalysis(null);
    setRequestError(null);
    setTimedOut(false);
    setAttempt((n) => n + 1);
  };

  if (!active) return <ComingSoon horizon={horizon} />;

  if (requestError) {
    return (
      <Failure
        title="Could not load the analysis"
        message={requestError}
        onRetry={retry}
      />
    );
  }

  if (timedOut) {
    return (
      <Failure
        title="This is taking longer than usual"
        message="The analysis has been running for more than 5 minutes. It may still finish in the background; try again in a minute."
        onRetry={retry}
      />
    );
  }

  if (analysis?.status === "error") {
    return (
      <Failure
        title="The analysis failed"
        message={analysis.error ?? "The backend did not say why."}
        onRetry={retry}
      />
    );
  }

  if (!analysis || analysis.status === "running") return <Skeleton />;

  const result = analysis.result;
  if (!result) {
    return (
      <Failure
        title="No analysis result"
        message="The run finished without a result. Try again."
        onRetry={retry}
      />
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {analysis.status === "partial" && (
        <p className="font-body-sm text-body-sm text-on-surface-variant">
          Some parts could not be loaded. What is available is shown below.
        </p>
      )}
      <NewsList block={result.news} />
      <NewsGauge block={result.news} />
      <SocialBox block={result.social} />
      <ChartRead block={result.chart} />
    </div>
  );
}
