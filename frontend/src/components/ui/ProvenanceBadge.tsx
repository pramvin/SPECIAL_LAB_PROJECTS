import type { Provenance } from "@/lib/types";
import { Icon } from "./Icon";

const CONFIG: Record<
  Provenance,
  { label: string; icon: string; className: string }
> = {
  input: {
    label: "User Input",
    icon: "edit",
    className:
      "bg-provenance-input-bg text-provenance-input-text border-provenance-input-border",
  },
  ai: {
    label: "AI · Assumptions",
    icon: "auto_awesome",
    className:
      "bg-provenance-ai-bg text-provenance-ai-text border-provenance-ai-border",
  },
  example: {
    label: "Example Data",
    icon: "info",
    className:
      "bg-provenance-example-bg text-provenance-example-text border-provenance-example-border",
  },
  warning: {
    label: "Needs Review",
    icon: "error",
    className:
      "bg-provenance-warning-bg text-provenance-warning-text border-provenance-warning-border",
  },
};

/**
 * Data-integrity pill. Required next to every figure so users can tell
 * user input, example data, and AI guidance apart (OVERVIEW.md §7).
 */
export function ProvenanceBadge({
  provenance,
  label,
  className = "",
}: {
  provenance: Provenance;
  label?: string;
  className?: string;
}) {
  const config = CONFIG[provenance];
  return (
    <span
      title={label ?? config.label}
      className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2.5 py-0.5 font-label-code text-label-code uppercase tracking-wide ${config.className} ${className}`}
    >
      <Icon name={config.icon} className="text-[12px]" />
      <span className="whitespace-nowrap">{label ?? config.label}</span>
    </span>
  );
}
