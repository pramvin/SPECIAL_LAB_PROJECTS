import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { BlockUnavailable } from "./BlockUnavailable";
import { ModelNote } from "./ModelNote";
import type { NewsDirection, NewsRead } from "@/lib/analysis";

const DIRECTION: Record<
  NewsDirection,
  { label: string; tone: "success" | "danger" | "neutral" }
> = {
  positive: { label: "Leans positive", tone: "success" },
  neutral: { label: "Neutral", tone: "neutral" },
  negative: { label: "Leans negative", tone: "danger" },
  mixed: { label: "Mixed", tone: "neutral" },
};

const CX = 120;
const CY = 120;
const R = 92;

/** Half-circle gauge: red on the left, green on the right, needle at the positive share. */
export function NewsGauge({ block }: { block: NewsRead }) {
  const share = block.positive_share;
  const direction = DIRECTION[block.direction] ?? DIRECTION.neutral;
  const angle = share === null ? null : Math.PI - share * Math.PI;
  const needleX = angle === null ? CX : CX + 62 * Math.cos(angle);
  const needleY = angle === null ? CY : CY - 62 * Math.sin(angle);

  return (
    <Card as="section">
      <CardHeader
        title="This week's news"
        icon="donut_large"
        subtitle="Share of this week's labeled headlines that are positive."
        badge={<ProvenanceBadge provenance="ai" label="Model labels" />}
        action={<Badge tone={direction.tone}>{direction.label}</Badge>}
      />

      {block.status === "unavailable" ? (
        <div className="mt-5">
          <BlockUnavailable status="unavailable" reason={block.reason} />
        </div>
      ) : (
        <>
          <div className="mt-5 flex flex-col items-center gap-1">
            <svg
              viewBox="0 0 240 132"
              className="h-auto w-full max-w-[300px]"
              role="img"
              aria-label={
                share === null
                  ? "No headlines to show on the gauge"
                  : `${Math.round(share * 100)} percent of this week's headlines are positive`
              }
            >
              <path
                d={`M${CX - R} ${CY} A${R} ${R} 0 0 1 ${CX} ${CY - R}`}
                fill="none"
                stroke="#d70015"
                strokeWidth="16"
              />
              <path
                d={`M${CX} ${CY - R} A${R} ${R} 0 0 1 ${CX + R} ${CY}`}
                fill="none"
                stroke="#166534"
                strokeWidth="16"
              />
              {share !== null ? (
                <>
                  <line
                    x1={CX}
                    y1={CY}
                    x2={needleX}
                    y2={needleY}
                    stroke="#1d1d1f"
                    strokeWidth="3"
                    strokeLinecap="round"
                  />
                  <circle cx={CX} cy={CY} r="5" fill="#1d1d1f" />
                </>
              ) : (
                <text
                  x={CX}
                  y={CY - 18}
                  textAnchor="middle"
                  fontSize="15"
                  fontWeight="600"
                  fill="#6e6e73"
                >
                  No headlines
                </text>
              )}
            </svg>
            <div className="flex w-full max-w-[300px] justify-between font-body-sm text-body-sm text-on-surface-variant">
              <span>Negative</span>
              <span>Positive</span>
            </div>
            {share !== null && (
              <span className="font-metric-md text-metric-md tabular-nums text-on-surface">
                {Math.round(share * 100)}% positive
              </span>
            )}
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 font-body-sm text-body-sm text-on-surface-variant">
            <span className="flex items-center gap-1.5">
              <span aria-hidden className="inline-block size-2.5 rounded-full bg-[#166534]" />
              Positive {block.counts.positive}
            </span>
            <span className="flex items-center gap-1.5">
              <span aria-hidden className="inline-block size-2.5 rounded-full bg-surface-container-highest" />
              Neutral {block.counts.neutral}
            </span>
            <span className="flex items-center gap-1.5">
              <span aria-hidden className="inline-block size-2.5 rounded-full bg-[#d70015]" />
              Negative {block.counts.negative}
            </span>
          </div>

          {block.summary && (
            <p className="mt-3 font-body-md text-body-md text-on-surface">
              {block.summary}
            </p>
          )}
        </>
      )}

      <div className="mt-4">
        <ModelNote />
      </div>
    </Card>
  );
}
