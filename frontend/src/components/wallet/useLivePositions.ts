"use client";

import { useEffect, useState } from "react";
import type { LivePositions, Position } from "@/lib/wallet";

export function useLivePositions(initial: Position[], intervalMs = 15_000) {
  const [live, setLive] = useState<LivePositions | null>(null);
  const [failed, setFailed] = useState(false);
  const key = initial.map((p) => p.id).sort((a, b) => a - b).join(",");

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function tick() {
      if (document.visibilityState === "visible") {
        try {
          const res = await fetch("/api/positions/live", { cache: "no-store" });
          if (!cancelled) {
            if (res.ok) {
              setLive((await res.json()) as LivePositions);
              setFailed(false);
            } else setFailed(true);
          }
        } catch {
          if (!cancelled) setFailed(true);
        }
      }
      if (!cancelled) timer = setTimeout(tick, intervalMs);
    }

    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [key, intervalMs]);

  const liveKey = live
    ? live.items.map((p) => p.id).sort((a, b) => a - b).join(",")
    : null;
  const usable = live !== null && liveKey === key;

  return {
    positions: usable ? live.items : initial,
    totals: usable ? live.totals : null,
    asOf: usable ? live.as_of : null,
    failed,
  };
}