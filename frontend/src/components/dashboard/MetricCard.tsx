import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { Icon } from "@/components/ui/Icon";
import type { Provenance } from "@/lib/types";

export function MetricCard({
  label,
  value,
  unit,
  provenance,
  provenanceLabel,
  delta,
  deltaTone = "neutral",
  caption,
  footer,
}: {
  label: string;
  value: string;
  unit?: string;
  provenance: Provenance;
  provenanceLabel?: string;
  delta?: string;
  deltaTone?: "positive" | "negative" | "neutral";
  caption?: string;
  footer?: React.ReactNode;
}) {
  const deltaColor =
    deltaTone === "positive"
      ? "text-provenance-input-text"
      : deltaTone === "negative"
        ? "text-error"
        : "text-on-surface-variant";

  return (
    <section className="flex flex-col gap-space-md rounded-lg border border-surface-container-high bg-surface-container-lowest p-space-lg">
      <div className="flex items-start justify-between gap-space-sm">
        <span className="font-title-md text-title-md text-on-surface-variant">
          {label}
        </span>
        <ProvenanceBadge provenance={provenance} label={provenanceLabel} />
      </div>
      <div className="flex flex-col gap-space-sm">
        <div className="flex items-baseline gap-1">
          <span className="font-metric-xl text-metric-xl tabular-nums text-on-surface">
            {value}
          </span>
          {unit && (
            <span className="font-body-md text-body-md text-on-surface-variant">
              {unit}
            </span>
          )}
        </div>
        {delta && (
          <span
            className={`inline-flex items-center gap-1 font-body-sm text-body-sm font-medium tabular-nums ${deltaColor}`}
          >
            <Icon
              name={deltaTone === "negative" ? "trending_down" : "trending_up"}
              className="text-[16px]"
            />
            {delta}
          </span>
        )}
      </div>
      {footer}
      {caption && (
        <span className="border-t border-surface-container-high pt-space-sm font-label-code text-label-code text-on-surface-variant">
          {caption}
        </span>
      )}
    </section>
  );
}
