"use client";

import { useEffect, useId, useState } from "react";
import { TextInput } from "@/components/ui/Field";
import { formatCurrency } from "@/lib/format";
import type { Instrument } from "@/lib/watchlist";

/**
 * Type to search S&P 500 stocks and ETFs (uses the existing /api/search),
 * then pick from the dropdown. You can still type any other ticker by hand.
 * Keyboard: Up/Down to move, Enter to pick, Esc to close.
 */
export function TickerSearch({
  id,
  value,
  onChange,
}: {
  id: string;
  value: string;
  onChange: (ticker: string) => void;
}) {
  const listId = useId();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Instrument[]>([]);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [active, setActive] = useState(-1);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    const timer = setTimeout(
      async () => {
        setLoading(true);
        try {
          const params = new URLSearchParams({ q: value.trim(), limit: "8" });
          const res = await fetch(`/api/search?${params}`, {
            signal: controller.signal,
          });
          if (!res.ok) throw new Error(String(res.status));
          const data = (await res.json()) as { items: Instrument[] };
          setItems(data.items);
          setFailed(false);
          setActive(-1);
        } catch {
          if (!controller.signal.aborted) setFailed(true);
        } finally {
          if (!controller.signal.aborted) setLoading(false);
        }
      },
      value ? 250 : 0,
    );
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [value, open]);

  function pick(item: Instrument) {
    onChange(item.ticker);
    setOpen(false);
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActive((a) => Math.min(a + 1, items.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (event.key === "Enter" && open && active >= 0 && items[active]) {
      event.preventDefault(); // pick the highlighted stock instead of submitting
      pick(items[active]);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div className="relative">
      <TextInput
        id={id}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
        placeholder="Search a company or ticker, e.g. Apple or AAPL"
        autoComplete="off"
        value={value}
        onChange={(e) => {
          onChange(e.target.value.toUpperCase());
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={onKeyDown}
      />
      {open && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-20 mt-1 max-h-72 w-full overflow-auto rounded-xl border border-outline-variant bg-surface-container-lowest py-1 shadow-lg"
        >
          {loading && items.length === 0 && (
            <li className="px-4 py-3 font-body-sm text-body-sm text-on-surface-variant">
              Searching…
            </li>
          )}
          {failed && (
            <li className="px-4 py-3 font-body-sm text-body-sm text-error">
              Search failed. Is the backend running?
            </li>
          )}
          {!loading && !failed && items.length === 0 && (
            <li className="px-4 py-3 font-body-sm text-body-sm text-on-surface-variant">
              No matches. You can still type any ticker.
            </li>
          )}
          {items.map((item, index) => (
            <li
              key={item.ticker}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === active}
              // mouse-down (not click) so the input doesn't blur and close first
              onMouseDown={(e) => {
                e.preventDefault();
                pick(item);
              }}
              onMouseEnter={() => setActive(index)}
              className={`flex cursor-pointer items-center justify-between gap-3 px-4 py-2 ${
                index === active ? "bg-primary-fixed" : ""
              }`}
            >
              <span className="flex min-w-0 flex-col">
                <span className="font-body-md text-body-md font-medium text-on-surface">
                  {item.ticker}
                  {item.kind === "etf" && (
                    <span className="ml-2 rounded-full bg-surface-container-low px-2 py-0.5 text-[11px] font-medium text-on-surface-variant">
                      ETF
                    </span>
                  )}
                </span>
                <span className="truncate font-body-sm text-body-sm text-on-surface-variant">
                  {item.name}
                </span>
              </span>
              <span className="shrink-0 font-body-sm text-body-sm tabular-nums text-on-surface">
                {item.price !== null
                  ? formatCurrency(item.price, { decimals: 2 })
                  : "—"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}