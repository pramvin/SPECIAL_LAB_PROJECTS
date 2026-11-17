import { Card, CardHeader } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { Badge } from "@/components/ui/Badge";
import { MODEL_INPUTS } from "@/lib/data/assistant";

export function ModelInputsPanel() {
  return (
    <Card className="flex flex-col gap-5">
      <CardHeader
        icon="tune"
        title="Model inputs"
        subtitle="Live parameters"
        badge={<Badge tone="success">Live</Badge>}
      />
      <p className="font-body-sm text-body-sm text-on-surface-variant">
        Transparency parameters mandated per team decision. Modify rates to
        observe the delta on projections.
      </p>
      <div className="flex flex-col gap-3">
        {MODEL_INPUTS.map((input) => (
          <div
            key={input.id}
            className="flex items-center justify-between gap-3 rounded-xl bg-surface-container-low p-4"
          >
            <div className="flex flex-col gap-1">
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                {input.label}
              </span>
              <span className="font-metric-md text-metric-md tabular-nums text-on-surface">
                {input.value}
              </span>
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                {input.note}
              </span>
            </div>
            <button
              type="button"
              className="rounded-full border border-outline-variant px-3 py-1.5 font-body-sm text-body-sm text-on-surface hover:bg-surface-container-lowest"
            >
              Edit
            </button>
          </div>
        ))}
      </div>
      <div className="flex items-start gap-3 rounded-xl bg-primary-fixed p-4">
        <Icon
          name="history"
          className="mt-0.5 text-[18px] text-on-primary-fixed"
        />
        <span className="font-body-sm text-body-sm text-on-primary-fixed">
          Audit provenance: last calibrated 3 days ago via Federal Reserve
          Economic Data. All simulation iterations are logged as example data.
        </span>
      </div>
    </Card>
  );
}
