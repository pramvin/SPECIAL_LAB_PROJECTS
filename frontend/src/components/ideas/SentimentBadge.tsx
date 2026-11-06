import { Badge } from "@/components/ui/Badge";

const MAP = {
  bullish: { label: "Positive", tone: "success", icon: "trending_up" },
  bearish: { label: "Negative", tone: "danger", icon: "trending_down" },
  neutral: { label: "Neutral", tone: "neutral", icon: "remove" },
} as const;

const TITLE =
  "Classified by an ML model trained on positive/negative word lists. Not yet checked against human labels.";

/** ML-labeled headline sentiment. Not yet validated on our own headlines, so it is display-only. */
export function SentimentBadge({ sentiment }: { sentiment?: string | null }) {
  if (!sentiment || !(sentiment in MAP)) return null;
  const m = MAP[sentiment as keyof typeof MAP];
  return (
    <span title={TITLE}>
      <Badge tone={m.tone} icon={m.icon}>
        {m.label}
      </Badge>
    </span>
  );
}
