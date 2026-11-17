"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/Icon";

export function ChatComposer() {
  const [value, setValue] = useState("");

  return (
    <div className="flex flex-col gap-3 rounded-[20px] border border-surface-container-high bg-surface-container-lowest p-4">
      <div className="flex items-end gap-2">
        <button
          type="button"
          aria-label="Add attachment"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-on-surface-variant hover:bg-surface-container-low"
        >
          <Icon name="add" />
        </button>
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          rows={1}
          placeholder="Ask about your plan, goals, or trade-offs…"
          className="max-h-32 flex-1 resize-none bg-transparent py-2.5 font-body-md text-body-md text-on-surface placeholder:text-on-surface-variant/60 focus:outline-none"
        />
        <button
          type="button"
          aria-label="Send message"
          disabled={!value.trim()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary-container text-on-primary transition-colors hover:bg-primary-hover disabled:opacity-40"
        >
          <Icon name="send" filled />
        </button>
      </div>
      <div className="flex items-start gap-2 border-t border-surface-container-high pt-3 font-body-sm text-body-sm text-error">
        <Icon name="error" className="mt-0.5 text-[15px]" />
        <span>
          Do not input account numbers, passwords, or SSNs. Masked client
          session — example data only.
        </span>
      </div>
      <span className="font-body-sm text-body-sm text-on-surface-variant">
        Shift + Return for line breaks · Markdown supported
      </span>
    </div>
  );
}
