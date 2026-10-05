import { Card, CardHeader } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { Badge } from "@/components/ui/Badge";
import { MODEL_INPUTS } from "@/lib/data/assistant";

export function ModelInputsPanel() {
  return (
    <Card className="flex flex-col gap-space-md">
      <CardHeader
        icon="tune"
        title="Model Inputs"
        subtitle="Live parameters"
        badge={<Badge tone="success">Live</Badge>}
      />
      <p className="font-body-sm text-body-sm text-on-surface-variant">
        Transparency parameters mandated per team decision. Modify rates to
        observe real-time delta on projections.
      </p>
      <div className="flex flex-col gap-space-sm">
        {MODEL_INPUTS.map((input) => (
          <div
            key={input.id}
            className="flex items-center justify-between rounded-md bg-surface-container-low p-space-sm"
          >
            <div className="flex flex-col">
              <span className="font-label-caps text-label-caps uppercase tracking-wide text-on-surface-variant">
                {input.label}
              </span>
              <span className="font-metric-md text-metric-md tabular-nums text-on-surface">
                {input.value}
              </span>
              <span className="font-label-code text-label-code text-on-surface-variant">
                {input.note}
              </span>
            </div>
            <button
              type="button"
              className="rounded-md border border-outline-variant px-space-sm py-1 font-body-sm text-body-sm text-secondary hover:bg-surface-container-lowest"
            >
              Edit
            </button>
          </div>
        ))}
      </div>
      <div className="flex items-start gap-space-sm rounded-md bg-secondary-fixed/50 p-space-sm">
        <Icon name="history" className="mt-0.5 text-[18px] text-secondary" />
        <span className="font-label-code text-label-code text-on-secondary-fixed">
          Audit Provenance: Last calibrated 3 days ago via Federal Reserve
          Economic Data. All simulation iterations are logged as example data.
        </span>
      </div>
    </Card>
  );
}
