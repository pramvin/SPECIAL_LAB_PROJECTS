import { Card, CardHeader, SectionLabel } from "@/components/ui/Card";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { BlockUnavailable } from "./BlockUnavailable";
import { ModelNote } from "./ModelNote";
import type { ChartLevel, ChartRead as ChartReadData } from "@/lib/analysis";

const usd = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });

const MOMENTUM: Record<string, string> = {
  improving: "Improving",
  flat: "Flat",
  weakening: "Weakening",
};

const VOLUME: Record<string, string> = {
  above_average: "Above average",
  normal: "Normal",
  below_average: "Below average",
};

function LevelList({ title, levels }: { title: string; levels: ChartLevel[] }) {
  return (
    <div className="flex flex-col gap-2 rounded-[16px] bg-surface-container-low p-4">
      <SectionLabel>{title}</SectionLabel>
      {levels.length === 0 ? (
        <span className="font-body-sm text-body-sm text-on-surface-variant">
          No clear level in the recent data.
        </span>
      ) : (
        <ul className="flex flex-col gap-2">
          {levels.map((level) => (
            <li key={`${level.price}-${level.why}`} className="flex flex-col">
              <span className="font-title-md text-title-md tabular-nums text-on-surface">
                {usd(level.price)}
              </span>
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                {level.why}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Support, resistance, momentum and volume as read from the stored prices. */
export function ChartRead({ block }: { block: ChartReadData }) {
  return (
    <Card as="section">
      <CardHeader
        title="Chart read"
        icon="candlestick_chart"
        subtitle="Support and resistance are price levels computed from stored daily closes; the model only chooses among them."
        badge={<ProvenanceBadge provenance="ai" label="Model summary" />}
      />

      {block.status === "unavailable" ? (
        <div className="mt-5">
          <BlockUnavailable status="unavailable" reason={block.reason} />
        </div>
      ) : (
        <>
          {block.summary && (
            <p className="mt-5 font-body-md text-body-md text-on-surface">
              {block.summary}
            </p>
          )}

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <LevelList title="Support" levels={block.support} />
            <LevelList title="Resistance" levels={block.resistance} />
          </div>

          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <div className="flex flex-col gap-1 rounded-[16px] bg-surface-container-low p-4">
              <SectionLabel>Momentum</SectionLabel>
              <span className="font-title-md text-title-md text-on-surface">
                {MOMENTUM[block.momentum.label] ?? block.momentum.label}
              </span>
              {block.momentum.why && (
                <span className="font-body-sm text-body-sm text-on-surface-variant">
                  {block.momentum.why}
                </span>
              )}
            </div>
            <div className="flex flex-col gap-1 rounded-[16px] bg-surface-container-low p-4">
              <SectionLabel>Volume</SectionLabel>
              <span className="font-title-md text-title-md text-on-surface">
                {VOLUME[block.volume.label] ?? block.volume.label}
              </span>
              {block.volume.why && (
                <span className="font-body-sm text-body-sm text-on-surface-variant">
                  {block.volume.why}
                </span>
              )}
            </div>
          </div>

          <div className="mt-4">
            <ModelNote />
          </div>
        </>
      )}
    </Card>
  );
}
